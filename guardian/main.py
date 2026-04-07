#!/usr/bin/env python3
"""
NusantaraOS — System Guardian Daemon
File: guardian/main.py

Ini "jantung" NusantaraOS — semua automation dikontrol dari sini.
Fitur:
  - BootWatcher: Zero-Panic Boot counter + rollback
  - HardwareWatcher: GPU detection + change detection + hw-state.json
  - HealthMonitor: disk, RAM, GPU, S.M.A.R.T, layanan
  - IPC Socket: GUI bisa kirim event ke daemon via Unix socket
  - NotificationDispatcher: semua notif Bahasa Indonesia + action buttons
"""

import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

# ── Fix import path ────────────────────────────────────────────────────────────
# Agar bisa dijalankan dari direktori manapun, bukan hanya dari dalam guardian/
GUARDIAN_DIR = os.path.dirname(os.path.abspath(__file__))
if GUARDIAN_DIR not in sys.path:
    sys.path.insert(0, GUARDIAN_DIR)

# ── Import modul Guardian ──────────────────────────────────────────────────────
# noqa: E402 — import setelah sys.path insert, ini disengaja
import importlib as _il  # noqa: E402

_config              = _il.import_module("config")
_boot_watcher        = _il.import_module("boot_watcher")
_hardware_watcher    = _il.import_module("hardware_watcher")
_health_monitor      = _il.import_module("health_monitor")
_notification        = _il.import_module("notification_dispatcher")

get_config          = _config.get_config
cek_boot            = _boot_watcher.cek_boot
reset_counter       = _boot_watcher.reset_counter
deteksi_gpu         = _hardware_watcher.deteksi_gpu
cek_perubahan_gpu   = _hardware_watcher.cek_perubahan_gpu
HW_STATE_PATH       = _hardware_watcher.HW_STATE_PATH
laporan_sehat       = _health_monitor.laporan_sehat
notif_sistem_sehat      = _notification.notif_sistem_sehat
notif_disk_hampir_penuh = _notification.notif_disk_hampir_penuh
notif_disk_kritis       = _notification.notif_disk_kritis
notif_ram_penuh         = _notification.notif_ram_penuh
notif_gpu_fallback      = _notification.notif_gpu_fallback
notif_gpu_ganti         = _notification.notif_gpu_ganti
notif_layanan_bermasalah = _notification.notif_layanan_bermasalah
notif_disk_smart_warning = _notification.notif_disk_smart_warning

# ── Config ─────────────────────────────────────────────────────────────────────
cfg = get_config()


# ── Logging — di-setup saat daemon dijalankan, bukan saat import ───────────────
log = logging.getLogger("guardian")


def _setup_logging():
    """Setup logging — dipanggil dari jalankan_guardian(), bukan saat import."""
    try:
        cfg.log_dir.mkdir(parents=True, exist_ok=True)
        cfg.state_dir.mkdir(parents=True, exist_ok=True)
        handlers = [
            logging.FileHandler(cfg.log_dir / 'guardian.log'),
            logging.StreamHandler(),
        ]
    except PermissionError:
        # Fallback kalau tidak punya akses ke /var/log/nusantara/
        handlers = [logging.StreamHandler()]
        log.warning("Tidak bisa tulis ke log file — pakai stdout saja")

    logging.basicConfig(
        level=getattr(logging, cfg.log_level, logging.INFO),
        format='[%(asctime)s] [%(name)s] %(message)s',
        handlers=handlers,
        force=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# IPC SOCKET SERVER
# GUI (driver_manager_ui, sehat_check_ui) kirim event ke daemon dari sini
# ══════════════════════════════════════════════════════════════════════════════

class GuardianIPCServer:
    """
    Unix socket server — listen di /run/nusantara/guardian.sock
    Handle event dari GUI dalam format JSON.
    Jalan di background thread, tidak block main loop.
    """

    SUPPORTED_EVENTS = {
        "HEALTH_CHECK_NOW",     # GUI minta health check sekarang
        "DRIVER_FIX_REQUESTED", # Driver Manager minta perbaiki driver
        "GUARDIAN_STATUS",      # GUI tanya status daemon saat ini
        "RELOAD_CONFIG",        # Reload guardian.conf tanpa restart
    }

    def __init__(self):
        self._socket_path = Path(cfg.socket_path)
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        """Jalankan IPC server di background thread."""
        self._running = True
        t = threading.Thread(target=self._run, name="ipc-server", daemon=True)
        self._thread = t
        t.start()  # pakai local var — Pyre2 bisa narrow Thread | None → Thread
        log.info(f"IPC server siap di {self._socket_path}")

    def stop(self):
        self._running = False
        # Hapus socket file kalau ada
        if self._socket_path.exists():
            self._socket_path.unlink()

    def _run(self):
        # Buat direktori untuk socket
        self._socket_path.parent.mkdir(parents=True, exist_ok=True)

        # Hapus socket lama kalau daemon restart
        if self._socket_path.exists():
            self._socket_path.unlink()

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(self._socket_path))
            server.listen(5)
            server.settimeout(1.0)  # timeout agar bisa cek self._running

            while self._running:
                try:
                    conn, _ = server.accept()
                    t = threading.Thread(
                        target=self._handle_client,
                        args=(conn,),
                        daemon=True
                    )
                    t.start()
                except socket.timeout:
                    continue
                except OSError:
                    break

    def _handle_client(self, conn: socket.socket):
        with conn:
            try:
                raw = conn.recv(4096).decode('utf-8')
                if not raw:
                    return

                event = json.loads(raw)
                event_type = event.get("type", "")
                payload    = event.get("payload", {})

                log.info(f"IPC event diterima: {event_type}")
                response = self._dispatch(event_type, payload)

                conn.sendall(json.dumps(response).encode('utf-8'))
                try:
                    conn.shutdown(socket.SHUT_RDWR)  # graceful close — cegah Broken pipe
                except OSError:
                    pass

            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                log.warning(f"IPC: pesan tidak valid: {e}")
                conn.sendall(json.dumps({"status": "error", "message": str(e)}).encode())
            except Exception as e:
                log.error(f"IPC handler error: {e}")

    def _dispatch(self, event_type: str, payload: dict) -> dict:
        if event_type == "GUARDIAN_STATUS":
            return {
                "status": "ok",
                "data": {
                    "daemon": "aktif",
                    "interval_cek": cfg.interval_cek,
                    "socket": str(self._socket_path),
                    "log_level": cfg.log_level,
                }
            }

        elif event_type == "HEALTH_CHECK_NOW":
            # Balas dulu ke client, lalu jalankan health check di background
            # agar socat tidak timeout dan Broken pipe tidak terjadi
            def _run_check():
                try:
                    laporan_sehat()
                except Exception as e:
                    log.error(f"Health check background error: {e}")
            threading.Thread(target=_run_check, daemon=True).start()
            return {"status": "ok", "message": "Health check dijadwalkan"}

        elif event_type == "DRIVER_FIX_REQUESTED":
            vendor = payload.get("vendor", "unknown")
            log.info(f"GUI minta perbaiki driver untuk vendor: {vendor}")
            # Driver fix dihandle oleh driver_manager_ui via subprocess
            # Daemon hanya log dan konfirmasi
            return {"status": "ok", "message": f"Driver fix untuk {vendor} diterima"}

        elif event_type == "RELOAD_CONFIG":
            try:
                _il.import_module("config").reload_config()
                return {"status": "ok", "message": "Config direload"}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            log.warning(f"IPC: event tidak dikenal: {event_type}")
            return {"status": "error", "message": f"Event tidak dikenal: {event_type}"}


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH CHECK + NOTIFIKASI
# ══════════════════════════════════════════════════════════════════════════════

def cek_dan_notif():
    """
    Jalankan semua health check dan kirim notifikasi berdasarkan kondisi aktual.
    Return True kalau sistem sehat.
    """
    semua_aman = laporan_sehat()

    # ── Disk ────────────────────────────────────────────────────────────────
    try:
        total, terpakai, _ = shutil.disk_usage('/')
        persen_disk = (terpakai / total) * 100

        if persen_disk >= cfg.disk_crit_pct:
            notif_disk_kritis(persen_disk)
        elif persen_disk >= cfg.disk_warn_pct:
            notif_disk_hampir_penuh(persen_disk)
    except Exception as e:
        log.error(f"Gagal cek disk untuk notifikasi: {e}")

    # ── RAM ─────────────────────────────────────────────────────────────────
    try:
        hasil = subprocess.run(['free', '-m'], capture_output=True, text=True)
        baris       = hasil.stdout.split('\n')[1].split()
        total_ram   = int(baris[1])
        terpakai_ram = int(baris[2])
        persen_ram  = (terpakai_ram / total_ram) * 100

        if persen_ram >= cfg.ram_crit_pct:
            notif_ram_penuh()
    except Exception as e:
        log.error(f"Gagal cek RAM untuk notifikasi: {e}")

    # ── Layanan gagal ────────────────────────────────────────────────────────
    try:
        hasil = subprocess.run(
            ['systemctl', '--failed', '--no-legend'],
            capture_output=True, text=True
        )
        for baris in hasil.stdout.strip().split('\n'):
            if baris.strip():
                nama = baris.split()[0]
                notif_layanan_bermasalah(nama)
                break  # notif satu per satu, tidak spam
    except Exception as e:
        log.error(f"Gagal cek layanan: {e}")

    # ── Sistem sehat ─────────────────────────────────────────────────────────
    if semua_aman:
        # Hanya kirim notif "sehat" sekali per jam, tidak tiap 5 menit
        _notif_sehat_throttled()

    return semua_aman


_last_notif_sehat = 0.0

def _notif_sehat_throttled():
    """Kirim notif sistem sehat maksimal sekali per jam."""
    global _last_notif_sehat
    now = time.time()
    if now - _last_notif_sehat >= 3600:
        notif_sistem_sehat()
        _last_notif_sehat = now


# ══════════════════════════════════════════════════════════════════════════════
# MAIN DAEMON LOOP
# ══════════════════════════════════════════════════════════════════════════════

def jalankan_guardian():
    _setup_logging()  # setup logging file handler saat daemon start, bukan saat import
    log.info("=" * 55)
    log.info("NUSANTARA OS — GUARDIAN DAEMON v0.1-alpha")
    log.info("Sistem kamu sedang dipantau")
    log.info(f"Config: interval={cfg.interval_cek}s, socket={cfg.socket_path}")
    log.info("=" * 55)

    # ── Langkah 1: Cek boot ─────────────────────────────────────────────────
    log.info("Langkah 1: Cek status boot...")
    cek_boot()

    # ── Langkah 2: Deteksi hardware ─────────────────────────────────────────
    log.info("Langkah 2: Deteksi hardware...")
    gpu = deteksi_gpu()

    if gpu is None or gpu == 'unknown':
        log.warning("GPU tidak dikenal — menggunakan llvmpipe")
        notif_gpu_fallback()
    else:
        # Cek apakah GPU diganti — baca PCI ID dari hw-state yang baru ditulis
        try:
            import json as _json
            if HW_STATE_PATH.exists():
                hw = _json.loads(HW_STATE_PATH.read_text())
                pci_id_baru = hw.get("pci_id", "—")
                # hw-state sudah update last_seen_pci_id ke nilai baru,
                # tapi kita perlu cek state SEBELUM deteksi_gpu() jalan.
                # Untuk ini, cek_perubahan_gpu() bandingkan field yang disimpan.
                # (Catatan: tulis_hw_state selalu update last_seen_pci_id ke nilai
                #  baru, jadi perbandingan dilakukan di sini SEBELUM pemanggilan
                #  tulis_hw_state pada run berikutnya)
                gpu_berubah = hw.get("gpu_changed", False)
                if gpu_berubah:
                    log.warning(f"GPU berubah terdeteksi! Trigger setup wizard.")
                    notif_gpu_ganti()
        except Exception as e:
            log.error(f"Gagal cek perubahan GPU: {e}")

    # ── Langkah 3: Boot sukses → reset counter ──────────────────────────────
    log.info("Langkah 3: Boot sukses, reset counter...")
    reset_counter()

    # ── Langkah 4: Start IPC server ─────────────────────────────────────────
    log.info("Langkah 4: Start IPC socket server...")
    ipc = GuardianIPCServer()
    ipc.start()

    # ── Langkah 5: Loop utama ───────────────────────────────────────────────
    log.info(f"Langkah 5: Loop pemantauan setiap {cfg.interval_cek // 60} menit")
    log.info("=" * 55)

    try:
        while True:
            log.info("─" * 40)
            log.info("Menjalankan Sehat Check...")
            cek_dan_notif()
            log.info(f"Istirahat {cfg.interval_cek // 60} menit...")
            time.sleep(cfg.interval_cek)
    except KeyboardInterrupt:
        log.info("Guardian dihentikan oleh user.")
    finally:
        ipc.stop()
        log.info("Guardian daemon berhenti.")


if __name__ == "__main__":
    jalankan_guardian()
