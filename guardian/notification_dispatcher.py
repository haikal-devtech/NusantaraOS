#!/usr/bin/env python3
"""
NusantaraOS — Notification Dispatcher
File: guardian/notification_dispatcher.py

Kirim notifikasi ke user dengan action buttons.
Pakai gdbus (D-Bus) untuk action button support — PRD 5.3 requirement.
Fallback ke notify-send tanpa button kalau gdbus tidak tersedia.
"""

import importlib
import json
import logging
import os
import subprocess
import threading
from pathlib import Path
from typing import Any, Callable

_i18n = importlib.import_module("i18n") if True else None
t: Callable[..., str] = _i18n.t  # type: ignore[union-attr]

log = logging.getLogger(__name__)

# ── Tipe notifikasi ────────────────────────────────────────────────────────────

INFO       = 'info'
PERINGATAN = 'peringatan'
KRITIS     = 'kritis'
SUKSES     = 'sukses'

# Urgency mapping untuk notify-send
_URGENCY = {
    SUKSES:     'normal',
    INFO:       'low',
    PERINGATAN: 'normal',
    KRITIS:     'critical',
}

# Icon mapping
_ICON = {
    SUKSES:     'dialog-information',
    INFO:       'dialog-information',
    PERINGATAN: 'dialog-warning',
    KRITIS:     'dialog-error',
}

# Guardian dir — untuk launch GUI dari action
_GUARDIAN_DIR = Path(__file__).parent


# ── Core: kirim notif dengan action button via D-Bus ─────────────────────────

def _gdbus_notify(judul: str, pesan: str, tipe: str,
                  actions: list[tuple[str, str]] | None = None,
                  on_action: dict[str, Callable[[], Any]] | None = None):
    """
    Kirim notifikasi via gdbus call langsung ke org.freedesktop.Notifications.
    actions: list of (action_key, label), contoh: [("perbaiki", "Perbaiki Driver")]
    on_action: dict {action_key: callable} — callback yang dipanggil kalau user klik

    Jalankan listener di thread terpisah agar tidak block daemon.
    """
    urgency_map = {SUKSES: 1, INFO: 0, PERINGATAN: 1, KRITIS: 2}
    urgency = urgency_map.get(tipe, 1)
    icon    = _ICON.get(tipe, 'dialog-information')

    # Format actions untuk D-Bus: array of strings [key, label, key2, label2, ...]
    actions_flat = []
    if actions:
        for key, label in actions:
            actions_flat += [key, label]
    # Selalu tambah "default" action supaya klik notif bisa di-handle
    actions_flat += ["default", ""]

    actions_str = "[" + ", ".join(f'"{a}"' for a in actions_flat) + "]"

    # Hints: urgency
    hints_str = f'{{"urgency": <byte {urgency}>}}'

    cmd = [
        "gdbus", "call",
        "--session",
        "--dest", "org.freedesktop.Notifications",
        "--object-path", "/org/freedesktop/Notifications",
        "--method", "org.freedesktop.Notifications.Notify",
        "NusantaraOS",   # app-name
        "0",             # replaces-id
        icon,            # app-icon
        judul,           # summary
        pesan,           # body
        actions_str,     # actions
        hints_str,       # hints
        "-1",            # expire-timeout (-1 = server default)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and on_action and actions:
            # Extract notification ID dari output gdbus: "(uint32 42,)"
            import re
            m = re.search(r'\(uint32 (\d+),\)', result.stdout)
            if m:
                notif_id = int(m.group(1))
                _listen_action(notif_id, on_action)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _listen_action(notif_id: int, on_action: dict[str, Callable[[], Any]]):
    """
    Listen ke ActionInvoked signal dari D-Bus di background thread.
    Dipanggil sekali per notifikasi.
    """
    def _listener():
        cmd = [
            "gdbus", "monitor",
            "--session",
            "--dest", "org.freedesktop.Notifications",
            "--object-path", "/org/freedesktop/Notifications",
        ]
        try:
            from typing import IO, cast
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, text=True)
            stdout = cast(IO[str], proc.stdout)  # stdout pasti ada karena PIPE di atas
            for line in stdout:
                if f"ActionInvoked ({notif_id}," in line or \
                   f"ActionInvoked (uint32 {notif_id}," in line:
                    # Ekstrak action key
                    import re
                    m = re.search(r"ActionInvoked.*?'([^']+)'", line)
                    if m:
                        key = m.group(1)
                        cb = on_action.get(key) or on_action.get("default")
                        if cb:
                            try:
                                cb()
                            except Exception as e:
                                log.error(f"Error di action callback '{key}': {e}")
                    proc.terminate()
                    break
                if "NotificationClosed" in line and str(notif_id) in line:
                    proc.terminate()
                    break
        except Exception as e:
            log.debug(f"Listener notifikasi: {e}")

    t = threading.Thread(target=_listener, daemon=True)
    t.start()


def _launch_gui(script: str):
    """Launch GUI script di background (non-blocking)."""
    script_path = _GUARDIAN_DIR / script
    subprocess.Popen(
        ["python3", str(script_path)],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _open_file_manager():
    """Buka file manager default."""
    for fm in ("dolphin", "nautilus", "thunar", "pcmanfm", "nemo"):
        try:
            subprocess.Popen([fm], start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except FileNotFoundError:
            continue


# ── Fungsi kirim utama ────────────────────────────────────────────────────────

def kirim_notifikasi(judul: str, pesan: str, tipe: str = INFO,
                     actions: list[tuple[str, str]] | None = None,
                     on_action: dict[str, Callable[[], Any]] | None = None):
    """
    Kirim notifikasi desktop ke user.
    Coba gdbus dulu (support action buttons), fallback ke notify-send.
    """
    log.info(f"Notifikasi [{tipe.upper()}]: {judul}")

    # Coba gdbus dengan action buttons
    berhasil = _gdbus_notify(judul, pesan, tipe, actions, on_action)
    if berhasil:
        log.info("Notifikasi dikirim via gdbus ✅")
        return

    # Fallback: notify-send (tanpa button)
    urgency  = _URGENCY.get(tipe, 'normal')
    icon     = _ICON.get(tipe, 'dialog-information')
    try:
        subprocess.run([
            'notify-send',
            '--app-name=NusantaraOS',
            f'--urgency={urgency}',
            f'--icon={icon}',
            judul, pesan
        ], timeout=5)
        log.info("Notifikasi dikirim via notify-send ✅")
    except FileNotFoundError:
        log.info(f"[NOTIFIKASI] {judul}: {pesan}")
    except Exception as e:
        log.error(f"Gagal kirim notifikasi: {e}")


# ── Pesan siap pakai (PRD-compliant, semua ada action) ────────────────────────

def notif_sistem_sehat():
    kirim_notifikasi(
        "✅ " + t("notifikasi.sistem_sehat"),
        t("notifikasi.sistem_sehat_isi"),
        SUKSES,
        actions=[("sehat_check", "Buka Sehat Check")],
        on_action={"sehat_check": lambda: _launch_gui("sehat_check_ui.py")},
    )


def notif_disk_hampir_penuh(persen: float):
    kirim_notifikasi(
        "⚠️ " + t("notifikasi.disk_peringatan"),
        t("notifikasi.disk_peringatan_isi", persen=f"{persen:.0f}"),
        PERINGATAN,
        actions=[("buka_fm", "Buka Manajer File")],
        on_action={"buka_fm": _open_file_manager},
    )


def notif_disk_kritis(persen: float):
    kirim_notifikasi(
        "🚨 " + t("notifikasi.disk_kritis"),
        t("notifikasi.disk_kritis_isi", persen=f"{persen:.0f}"),
        KRITIS,
        actions=[("buka_fm", "Buka Manajer File")],
        on_action={"buka_fm": _open_file_manager},
    )


def notif_ram_penuh():
    kirim_notifikasi(
        "⚠️ " + t("notifikasi.ram_penuh"),
        t("notifikasi.ram_penuh_isi"),
        PERINGATAN,
        actions=[("sehat_check", "Lihat Detail")],
        on_action={"sehat_check": lambda: _launch_gui("sehat_check_ui.py")},
    )


def notif_gpu_fallback():
    kirim_notifikasi(
        "⚠️ " + t("notifikasi.gpu_fallback"),
        t("notifikasi.gpu_fallback_isi"),
        PERINGATAN,
        actions=[("perbaiki", "Perbaiki Driver")],
        on_action={"perbaiki": lambda: _launch_gui("driver_manager_ui.py")},
    )


def notif_gpu_ganti():
    kirim_notifikasi(
        "🔄 " + t("hardware.gpu_ganti_terdeteksi"),
        t("hardware.gpu_ganti_terdeteksi"),
        PERINGATAN,
        actions=[("setup_driver", "Setup Driver")],
        on_action={"setup_driver": lambda: _launch_gui("driver_manager_ui.py")},
    )


def notif_layanan_bermasalah(nama_layanan: str):
    kirim_notifikasi(
        "⚠️ Layanan Bermasalah",
        t("sehat.layanan_bermasalah", n=1) + f" ({nama_layanan})",
        PERINGATAN,
        actions=[("sehat_check", "Lihat Detail")],
        on_action={"sehat_check": lambda: _launch_gui("sehat_check_ui.py")},
    )


def notif_pemulihan_berhasil():
    kirim_notifikasi(
        "🛡️ " + t("notifikasi.pemulihan_berhasil"),
        t("notifikasi.pemulihan_berhasil_isi"),
        SUKSES,
        actions=[("sehat_check", "Lihat Laporan")],
        on_action={"sehat_check": lambda: _launch_gui("sehat_check_ui.py")},
    )


def notif_pembaruan_tersedia(jumlah: int):
    kirim_notifikasi(
        "📦 " + t("notifikasi.pembaruan_tersedia"),
        t("notifikasi.pembaruan_tersedia_isi", n=jumlah),
        INFO,
        actions=[("update", "Perbarui Sekarang")],
        on_action={"update": lambda: log.info("TODO: buka package manager GUI")},
    )


def notif_disk_smart_warning(disk: str, masalah: str):
    kirim_notifikasi(
        f"⚠️ Kesehatan Disk {disk} Menurun",
        f"{masalah}. Segera backup data penting.",
        KRITIS,
        actions=[("sehat_check", "Lihat Detail")],
        on_action={"sehat_check": lambda: _launch_gui("sehat_check_ui.py")},
    )


# ── Test langsung ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
    log.info("Test notifikasi dengan action buttons...")

    import time
    notif_gpu_fallback()
    time.sleep(1)
    notif_disk_hampir_penuh(87)
    time.sleep(1)
    notif_sistem_sehat()

    log.info("Notifikasi dikirim. Klik tombol untuk test action callback.")
    time.sleep(10)  # tunggu action kalau ada
