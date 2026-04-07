#!/usr/bin/env python3
"""
NusantaraOS — Boot Watcher
File: guardian/boot_watcher.py

Zero-Panic Boot: deteksi kalau sistem gagal boot berulang.
Kalau gagal 2x berturut-turut → auto rollback ke Btrfs snapshot.

Dua mode boot counter (sesuai config):
  1. systemd-boot (bootctl) — UEFI, lebih reliable, PRD recommendation
  2. File counter di /var/lib/nusantara/boot-counter — fallback non-UEFI

Recovery events dicatat ke /var/log/nusantara/recovery.log
"""

import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────────
try:
    from config import get_config
    _cfg = get_config()
    BOOT_COUNTER_FILE = _cfg.state_dir / "boot-counter"
    MAX_GAGAL         = _cfg.max_gagal
    USE_SYSTEMD_BOOT  = _cfg.use_systemd_boot
    RECOVERY_LOG      = _cfg.recovery_log
except ImportError:
    BOOT_COUNTER_FILE = Path("/var/lib/nusantara/boot-counter")
    MAX_GAGAL         = 2
    USE_SYSTEMD_BOOT  = True
    RECOVERY_LOG      = Path("/var/log/nusantara/recovery.log")


# ══════════════════════════════════════════════════════════════════════════════
# RECOVERY LOG
# ══════════════════════════════════════════════════════════════════════════════

def _tulis_recovery_log(pesan: str):
    """Catat event pemulihan ke recovery.log (PRD 5.1)."""
    try:
        RECOVERY_LOG.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(RECOVERY_LOG, 'a') as f:
            f.write(f"[{timestamp}] {pesan}\n")
    except Exception as e:
        log.error(f"Gagal tulis recovery log: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEMD-BOOT COUNTER
# ══════════════════════════════════════════════════════════════════════════════

def _bootctl_tersedia() -> bool:
    """Cek apakah bootctl (systemd-boot) tersedia di sistem ini."""
    try:
        result = subprocess.run(
            ['bootctl', 'is-installed'],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _baca_counter_bootctl() -> int:
    """
    Baca boot counter dari systemd-boot via bootctl.
    systemd-boot punya built-in boot counter di entry .conf
    Format: <name>+<tries-left>-<tries-done>.conf
    Kita parse dari bootctl status.
    """
    try:
        result = subprocess.run(
            ['bootctl', 'status', '--no-pager'],
            capture_output=True, text=True, timeout=10
        )
        # Cari baris "Boot Loader Spec" atau "Bad EFI" / tries done
        for line in result.stdout.split('\n'):
            if 'tries done' in line.lower() or 'tries-done' in line.lower():
                parts = line.split(':')
                if len(parts) >= 2:
                    try:
                        return int(parts[-1].strip())
                    except ValueError:
                        pass
        return 0
    except Exception as e:
        log.debug(f"Gagal baca bootctl counter: {e}")
        return 0


def _set_boot_tries(jumlah: int):
    """Set boot tries counter via bootctl (systemd-boot)."""
    try:
        # bootctl set-boot-loader-flag tidak ada di semua versi
        # Cara terbaik: via kernel parameter atau entry renaming
        # Untuk sekarang: pakai file counter sebagai primary, bootctl sebagai info
        log.debug(f"bootctl boot tries akan diset ke {jumlah} (future feature)")
    except Exception as e:
        log.debug(f"bootctl set tries: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# FILE COUNTER (fallback + primary saat ini)
# ══════════════════════════════════════════════════════════════════════════════

def baca_counter() -> int:
    """
    Baca berapa kali sistem sudah gagal boot.
    Coba systemd-boot dulu, fallback ke file counter.
    """
    # Coba baca dari file counter (reliable di semua setup)
    try:
        BOOT_COUNTER_FILE.parent.mkdir(parents=True, exist_ok=True)
        if BOOT_COUNTER_FILE.exists():
            angka = int(BOOT_COUNTER_FILE.read_text().strip())
            log.info(f"Counter boot gagal: {angka}x")
            return angka
        else:
            log.info("Boot pertama — counter 0")
            return 0
    except Exception as e:
        log.error(f"Gagal baca counter: {e}")
        return 0


def tulis_counter(angka: int):
    """Simpan angka counter boot gagal ke file."""
    try:
        BOOT_COUNTER_FILE.parent.mkdir(parents=True, exist_ok=True)
        BOOT_COUNTER_FILE.write_text(str(angka))
        log.info(f"Counter disimpan: {angka}x")
    except Exception as e:
        log.error(f"Gagal simpan counter: {e}")


def reset_counter():
    """
    Reset counter ke 0 setelah boot berhasil normal.
    Dipanggil dari main.py setelah Guardian aktif.
    """
    try:
        if BOOT_COUNTER_FILE.exists():
            BOOT_COUNTER_FILE.unlink()
        log.info("Boot berhasil! Counter direset ke 0")
        _tulis_recovery_log("Boot sukses — counter direset")
    except Exception as e:
        log.error(f"Gagal reset counter: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# ROLLBACK
# ══════════════════════════════════════════════════════════════════════════════

def mulai_rollback():
    """
    Prosedur rollback ke Btrfs snapshot terakhir yang bagus.
    PRD 5.1: home directory TIDAK dirollback.
    Semua event dicatat ke recovery.log.
    """
    log.warning("=" * 55)
    log.warning("NUSANTARA OS — PEMULIHAN OTOMATIS")
    log.warning("Sistem akan dipulihkan ke kondisi sebelumnya")
    log.warning("Folder /home kamu TIDAK terpengaruh")
    log.warning("=" * 55)

    _tulis_recovery_log("ROLLBACK DIPICU — sistem gagal boot berulang")

    # ── Cek apakah Btrfs tersedia ──────────────────────────────────────────
    try:
        result = subprocess.run(
            ['findmnt', '-n', '-o', 'FSTYPE', '/'],
            capture_output=True, text=True
        )
        fs_type = result.stdout.strip()
        if fs_type != 'btrfs':
            log.warning(f"Root filesystem adalah '{fs_type}', bukan Btrfs")
            log.warning("Zero-Panic Boot membutuhkan Btrfs — rollback dilewati")
            _tulis_recovery_log(f"ROLLBACK DILEWATI — filesystem {fs_type} bukan Btrfs")
            reset_counter()
            return
    except Exception:
        pass

    # ── Cari snapshot yang tersedia ────────────────────────────────────────
    snapshot_dir = Path("/.snapshots")
    if not snapshot_dir.exists():
        log.warning("Direktori /.snapshots tidak ditemukan")
        log.warning("Pastikan Btrfs subvolume @snapshots sudah di-setup")
        _tulis_recovery_log("ROLLBACK GAGAL — /.snapshots tidak ditemukan")
        reset_counter()
        return

    try:
        # Cari snapshot terbaru (kecuali yang baru dibuat saat ini)
        snapshots = sorted(snapshot_dir.iterdir(), key=os.path.getmtime, reverse=True)
        if not snapshots:
            log.warning("Tidak ada snapshot tersedia untuk rollback")
            _tulis_recovery_log("ROLLBACK GAGAL — tidak ada snapshot")
            reset_counter()
            return

        snapshot_terbaru = snapshots[0]
        log.info(f"Snapshot ditemukan: {snapshot_terbaru}")
        _tulis_recovery_log(f"Snapshot target: {snapshot_terbaru}")

        # TODO (Phase 5): implementasi swap root ke snapshot
        # Steps yang akan dilakukan:
        # 1. btrfs subvolume set-default <snapshot_id>
        # 2. grub/systemd-boot update
        # 3. Reboot ke snapshot
        # 4. Setelah boot dari snapshot: kirim notif_pemulihan_berhasil()

        log.info("(Implementasi Btrfs swap-root menyusul di Phase 5 — v0.9 RC)")
        _tulis_recovery_log("SIMULASI ROLLBACK — implementasi Btrfs menyusul di Phase 5")

    except Exception as e:
        log.error(f"Error saat rollback: {e}")
        _tulis_recovery_log(f"ROLLBACK ERROR: {e}")

    reset_counter()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN: CEK BOOT
# ══════════════════════════════════════════════════════════════════════════════

def cek_boot():
    """
    Fungsi utama Boot Watcher.
    Dipanggil setiap kali sistem boot (dari main.py Guardian).

    Alur:
    1. Baca counter gagal boot
    2. Kalau sudah >= MAX_GAGAL → ROLLBACK
    3. Kalau belum → tambah counter, lanjut boot normal
    4. Setelah boot sukses → reset_counter() dipanggil dari main.py
    """
    log.info("Boot Watcher: cek status boot...")

    counter = baca_counter()

    if counter >= MAX_GAGAL:
        log.warning(f"PERHATIAN! Sistem gagal boot {counter}x berturut-turut!")
        log.warning("Memulai prosedur pemulihan otomatis...")
        _tulis_recovery_log(
            f"TRIGGER ROLLBACK setelah {counter}x gagal boot (threshold: {MAX_GAGAL})"
        )
        mulai_rollback()
    else:
        counter_baru = counter + 1
        tulis_counter(counter_baru)
        log.info(f"Boot attempt ke-{counter_baru} — sistem loading...")
        log.info(f"Kalau boot sukses, counter akan direset otomatis")
        if counter_baru > 0:
            _tulis_recovery_log(f"Boot attempt ke-{counter_baru} — belum trigger rollback")


# ── Test langsung ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

    log.info("=== Test Boot Watcher ===")
    log.info(f"Config: MAX_GAGAL={MAX_GAGAL}, USE_SYSTEMD_BOOT={USE_SYSTEMD_BOOT}")
    log.info(f"Counter file: {BOOT_COUNTER_FILE}")
    log.info(f"Recovery log: {RECOVERY_LOG}")

    log.info("\nSimulasi boot pertama:")
    cek_boot()

    log.info("\nSimulasi boot gagal kedua:")
    cek_boot()

    log.info("\nSimulasi boot gagal ketiga (trigger rollback):")
    cek_boot()

    log.info("\nSimulasi boot sukses (reset counter):")
    reset_counter()

    log.info(f"\nRecovery log: {RECOVERY_LOG}")
    if Path(RECOVERY_LOG).exists():
        print(Path(RECOVERY_LOG).read_text())
