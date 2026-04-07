"""
NusantaraOS — Guardian System Tray Icon
File: guardian/tray_icon.py

Icon Guardian di system tray KDE Plasma.
- Icon berubah warna sesuai status sistem (hijau/kuning/merah)
- Left-click → buka Sehat Check
- Right-click → menu (Sehat Check, Driver Manager, separator, Keluar)
- Auto-refresh status tiap 30 detik
- Baca state dari /var/lib/nusantara/health-state.json

Dijalankan dari main.py Guardian daemon saat startup.
"""

import json
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QWidget,
)

# ── Path ───────────────────────────────────────────────────────────────────────

HEALTH_STATE_PATH = Path("/var/lib/nusantara/health-state.json")

# ── Warna brand ────────────────────────────────────────────────────────────────

ICON_COLORS = {
    "ok":      ("#2E8A52", "#1D5C38"),   # Hijau Rimba — fill, outline
    "warning": ("#E8B020", "#C5940A"),   # Emas Keraton
    "error":   ("#C0302A", "#8B1A1A"),   # Merah Saga
    "unknown": ("#A08060", "#4A3020"),   # muted
}

REFRESH_INTERVAL_MS = 30_000   # 30 detik


# ── Icon generator ─────────────────────────────────────────────────────────────

def _make_icon(status: str, size: int = 22) -> QIcon:
    """
    Generate icon bulat dengan warna status.
    Titik kecil di tengah sebagai identitas Guardian.
    Tidak butuh file PNG eksternal.
    """
    fill_hex, outline_hex = ICON_COLORS.get(status, ICON_COLORS["unknown"])
    fill    = QColor(fill_hex)
    outline = QColor(outline_hex)
    dot     = QColor("#F2E4C0")  # Krem Lawas

    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)

    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Lingkaran utama
    painter.setPen(QPen(outline, 1.5))
    painter.setBrush(QBrush(fill))
    margin = 2
    painter.drawEllipse(margin, margin, size - margin * 2, size - margin * 2)

    # Titik tengah — identitas NusantaraOS (kawung center)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(dot))
    dot_r = max(2, size // 8)
    center = size // 2
    painter.drawEllipse(center - dot_r, center - dot_r, dot_r * 2, dot_r * 2)

    painter.end()
    return QIcon(px)


# ── Status reader ──────────────────────────────────────────────────────────────

def _read_overall_status() -> tuple[str, str]:
    """
    Baca health-state.json, return (status, tooltip_text).
    status: 'ok' | 'warning' | 'error' | 'unknown'
    """
    if not HEALTH_STATE_PATH.exists():
        return "unknown", "NusantaraOS Guardian\nStatus tidak diketahui"

    try:
        data = json.loads(HEALTH_STATE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return "unknown", "NusantaraOS Guardian\nGagal membaca status"

    statuses = [
        data.get("storage",  {}).get("status", "ok"),
        data.get("memory",   {}).get("status", "ok"),
        data.get("gpu",      {}).get("status", "ok"),
        data.get("guardian", {}).get("status", "ok"),
        data.get("services", {}).get("status", "ok"),
    ]

    if "error" in statuses:
        overall = "error"
    elif "warning" in statuses:
        overall = "warning"
    else:
        overall = "ok"

    # Bangun tooltip
    label_map = {
        "ok":      "✅ Semua normal",
        "warning": "⚠️ Ada peringatan",
        "error":   "❌ Ada masalah",
    }
    lines = ["NusantaraOS Guardian", label_map.get(overall, "—")]

    # Tambah detail warning/error
    checks = [
        ("Penyimpanan", data.get("storage",  {})),
        ("Memori",      data.get("memory",   {})),
        ("GPU",         data.get("gpu",      {})),
        ("Guardian",    data.get("guardian", {})),
    ]
    for name, d in checks:
        s = d.get("status", "ok")
        if s != "ok":
            v = d.get("value", "")
            lines.append(f"  {name}: {v}")

    return overall, "\n".join(lines)


# ── Tray icon ──────────────────────────────────────────────────────────────────

class GuardianTrayIcon(QSystemTrayIcon):
    def __init__(self, app: QApplication):
        super().__init__()
        self._app = app
        self._status = "unknown"
        self._sehat_win  = None
        self._driver_win = None

        # Setup awal
        self._update_status()
        self._build_menu()

        # Klik kiri → Sehat Check
        self.activated.connect(self._on_activated)

        # Auto-refresh
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_status)
        self._timer.start(REFRESH_INTERVAL_MS)

        self.show()

    # ── Menu ───────────────────────────────────────────────────────────────────

    def _build_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background: #2A1A12;
                color: #F2E4C0;
                border: 1px solid #4A3020;
                border-radius: 6px;
                padding: 4px 0;
                font-family: 'Noto Sans', sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 7px 20px;
            }
            QMenu::item:selected {
                background: #3A2518;
                color: #E8B020;
            }
            QMenu::separator {
                height: 1px;
                background: #4A3020;
                margin: 4px 0;
            }
        """)

        # Header — nama app (non-clickable)
        header = menu.addAction("NusantaraOS Guardian")
        header.setEnabled(False)
        menu.addSeparator()

        # Aksi utama
        sehat_action  = menu.addAction("❤  Sehat Check")
        driver_action = menu.addAction("🔧  Manajer Driver")
        menu.addSeparator()

        # Status saat ini
        self._status_action = menu.addAction(self._status_label())
        self._status_action.setEnabled(False)
        menu.addSeparator()

        # Keluar
        quit_action = menu.addAction("✕  Keluar Guardian")

        # Connect
        sehat_action.triggered.connect(self._open_sehat_check)
        driver_action.triggered.connect(self._open_driver_manager)
        quit_action.triggered.connect(self._quit)

        self.setContextMenu(menu)
        self._menu = menu

    def _status_label(self) -> str:
        labels = {
            "ok":      "● Sistem normal",
            "warning": "● Ada peringatan",
            "error":   "● Ada masalah",
            "unknown": "● Status tidak diketahui",
        }
        return labels.get(self._status, "●")

    # ── Update ─────────────────────────────────────────────────────────────────

    def _update_status(self):
        status, tooltip = _read_overall_status()
        self._status = status

        self.setIcon(_make_icon(status))
        self.setToolTip(tooltip)

        # Update label di menu kalau sudah ada
        if hasattr(self, "_status_action"):
            self._status_action.setText(self._status_label())

    # ── Handlers ───────────────────────────────────────────────────────────────

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._open_sehat_check()

    def _open_sehat_check(self):
        try:
            from sehat_check_ui import SehatCheckWindow
            if self._sehat_win is None or not self._sehat_win.isVisible():
                self._sehat_win = SehatCheckWindow()
                self._sehat_win.show()
            else:
                self._sehat_win.raise_()
                self._sehat_win.activateWindow()
        except ImportError as e:
            self.showMessage("Error", f"Tidak bisa membuka Sehat Check:\n{e}",
                             QSystemTrayIcon.MessageIcon.Critical, 3000)

    def _open_driver_manager(self):
        try:
            from driver_manager_ui import DriverManagerWindow
            if self._driver_win is None or not self._driver_win.isVisible():
                self._driver_win = DriverManagerWindow()
                self._driver_win.show()
            else:
                self._driver_win.raise_()
                self._driver_win.activateWindow()
        except ImportError as e:
            self.showMessage("Error", f"Tidak bisa membuka Driver Manager:\n{e}",
                             QSystemTrayIcon.MessageIcon.Critical, 3000)

    def _quit(self):
        self.hide()
        self._app.quit()


# ── Entry point ────────────────────────────────────────────────────────────────

def launch_tray(app: QApplication | None = None) -> GuardianTrayIcon:
    """
    Dipanggil dari main.py Guardian.
    Kalau dipanggil standalone, buat QApplication sendiri.
    """
    standalone = app is None
    if standalone:
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("[tray] System tray tidak tersedia di environment ini.")
        if standalone:
            sys.exit(1)
        return None

    tray = GuardianTrayIcon(app)

    if standalone:
        sys.exit(app.exec())

    return tray


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)   # jangan exit kalau semua window ditutup

    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("System tray tidak tersedia.")
        sys.exit(1)

    tray = GuardianTrayIcon(app)
    sys.exit(app.exec())
