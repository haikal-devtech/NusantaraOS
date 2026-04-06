"""
NusantaraOS — Sehat Check GUI
File: guardian/sehat_check_ui.py

Monitor kesehatan sistem dalam Bahasa Indonesia.
Baca data dari health_monitor.py lewat Guardian daemon.

Dipanggil dari:
  - System tray icon NusantaraOS
  - Guardian notification action button
  - Langsung: python sehat_check_ui.py
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QSizePolicy,
)

# ── Konstanta ──────────────────────────────────────────────────────────────────

HEALTH_STATE_PATH = Path("/var/lib/nusantara/health-state.json")
LOG_PATH          = Path("/var/log/nusantara/sehat_check.log")

# Fallback data dev mode
FALLBACK_HEALTH = {
    "storage": {"value": "2 GB tersisa",  "status": "warning", "detail": "Partisi / hampir penuh"},
    "memory":  {"value": "40% terpakai",  "status": "ok",      "detail": "3.4 GB dari 5.7 GB"},
    "gpu":     {"value": "Intel aktif",   "status": "ok",      "detail": "i915 — driver normal"},
    "guardian":{"value": "Aktif",         "status": "ok",      "detail": "Semua modul berjalan"},
    "services":{"failed": [],             "status": "ok"},
    "last_check": None,
}

# Warna brand NusantaraOS
C = {
    "bg":           "#1C0F0A",   # Arang Kayu
    "surface":      "#2A1A12",
    "surface2":     "#3A2518",
    "border":       "#4A3020",
    "text":         "#F2E4C0",   # Krem Lawas
    "text_muted":   "#A08060",
    "red":          "#8B1A1A",   # Merah Saga
    "red_bright":   "#C0302A",
    "red_dim":      "#3A0A0A",
    "gold":         "#C5940A",   # Emas Keraton
    "gold_bright":  "#E8B020",
    "gold_dim":     "#3A2800",
    "green":        "#1D5C38",   # Hijau Rimba
    "green_bright": "#2E8A52",
    "green_dim":    "#0A2A18",
    "blue":         "#1A3F6F",   # Biru Samudera
    "blue_bright":  "#2E6BAA",
}

STATUS_CONFIG = {
    "ok":      ("Aman",      C["green_bright"], C["green_dim"], C["green"]),
    "warning": ("Peringatan",C["gold_bright"],  C["gold_dim"],  C["gold"]),
    "error":   ("Bahaya",    C["red_bright"],   C["red_dim"],   C["red"]),
}


# ── Komponen kecil ─────────────────────────────────────────────────────────────

class Divider(QFrame):
    def __init__(self, vertical=False):
        super().__init__()
        if vertical:
            self.setFrameShape(QFrame.Shape.VLine)
            self.setStyleSheet(f"background:{C['border']};min-width:1px;max-width:1px;border:none;")
        else:
            self.setFrameShape(QFrame.Shape.HLine)
            self.setStyleSheet(f"background:{C['border']};min-height:1px;max-height:1px;border:none;")


class StatusBadge(QLabel):
    def __init__(self, status: str):
        label, color, _, border = STATUS_CONFIG.get(status, STATUS_CONFIG["ok"])
        super().__init__(f"● {label}")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background: transparent;
                font-size: 12px;
                font-weight: 600;
            }}
        """)


class MetricCard(QFrame):
    """
    Satu kartu metrik — judul, nilai besar, badge status.
    Ukuran fleksibel, susun horizontal.
    """
    def __init__(self, title: str, value: str, status: str, detail: str = ""):
        super().__init__()
        label, color, bg, border = STATUS_CONFIG.get(status, STATUS_CONFIG["ok"])

        is_warning = status != "ok"
        card_border = border if is_warning else C["border"]

        self.setStyleSheet(f"""
            QFrame {{
                background: {C['surface']};
                border: 1px solid {card_border};
                border-radius: 10px;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(110)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        # Judul kartu
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color:{C['text_muted']};font-size:13px;font-weight:500;border:none;background:transparent;")
        layout.addWidget(title_lbl)

        # Nilai utama
        value_lbl = QLabel(value)
        value_lbl.setStyleSheet(f"color:{color};font-size:18px;font-weight:700;border:none;background:transparent;")
        layout.addWidget(value_lbl)

        # Badge status
        badge = StatusBadge(status)
        badge.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(badge)

        if detail:
            detail_lbl = QLabel(detail)
            detail_lbl.setStyleSheet(f"color:{C['text_muted']};font-size:11px;border:none;background:transparent;")
            detail_lbl.setWordWrap(True)
            layout.addWidget(detail_lbl)

        layout.addStretch()


class ServiceRow(QWidget):
    """Satu baris layanan — nama + status."""
    def __init__(self, name: str, ok: bool = True):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        dot = QLabel("✓" if ok else "✗")
        dot.setStyleSheet(f"color:{'#2E8A52' if ok else '#C0302A'};font-size:14px;font-weight:700;min-width:20px;")
        lbl = QLabel(name)
        lbl.setStyleSheet(f"color:{C['text']};font-size:13px;")
        layout.addWidget(dot)
        layout.addWidget(lbl)
        layout.addStretch()


class ActionButton(QPushButton):
    def __init__(self, text: str, primary: bool = True):
        super().__init__(text)
        if primary:
            bg, bg_h = C["red"], C["red_bright"]
        else:
            bg, bg_h = C["surface2"], C["border"]
        self.setStyleSheet(f"""
            QPushButton {{
                background:{bg};
                color:{C['text']};
                border:1px solid {C['border']};
                border-radius:6px;
                padding:8px 20px;
                font-size:13px;
                font-weight:600;
            }}
            QPushButton:hover {{
                background:{bg_h};
                border-color:{C['gold']};
            }}
            QPushButton:pressed {{ background:{bg}; }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(38)


# ── Main Window ────────────────────────────────────────────────────────────────

class SehatCheckWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data = self._load_state()

        self.setWindowTitle("NusantaraOS — Sehat Check")
        self.setMinimumSize(640, 460)
        self.setMaximumSize(900, 700)
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background:{C['bg']};
                color:{C['text']};
                font-family:'Noto Sans','Segoe UI',sans-serif;
            }}
            QScrollArea {{ border:none; background:transparent; }}
            QScrollBar:vertical {{ width:4px; background:{C['surface']}; }}
            QScrollBar::handle:vertical {{ background:{C['border']}; border-radius:2px; }}
        """)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(14)

        # ── Header ────────────────────────────────────────────────────────────
        header = QHBoxLayout()
        icon_title = QHBoxLayout()
        icon_title.setSpacing(8)
        heart = QLabel("❤")
        heart.setStyleSheet(f"color:{C['red_bright']};font-size:20px;")
        title = QLabel("Sehat Check")
        title.setStyleSheet(f"color:{C['text']};font-size:20px;font-weight:700;")
        icon_title.addWidget(heart)
        icon_title.addWidget(title)
        header.addLayout(icon_title)
        header.addStretch()

        # Badge overall status
        overall = self._overall_status()
        label, color, bg, border = STATUS_CONFIG.get(overall, STATUS_CONFIG["ok"])
        self.overall_badge = QLabel(f"● {'Semua Normal' if overall == 'ok' else 'Ada Peringatan' if overall == 'warning' else 'Ada Masalah'}")
        self.overall_badge.setStyleSheet(f"color:{color};font-size:13px;font-weight:600;")
        header.addWidget(self.overall_badge)

        root.addLayout(header)
        root.addWidget(Divider())

        # ── Section: Kondisi Sistem ────────────────────────────────────────────
        kondisi_lbl = QLabel("Kondisi Sistem")
        kondisi_lbl.setStyleSheet(f"color:{C['text_muted']};font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:1px;")
        root.addWidget(kondisi_lbl)

        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(10)
        self._build_cards()
        root.addLayout(self.cards_layout)

        root.addWidget(Divider())

        # ── Section: Layanan Sistem ────────────────────────────────────────────
        layanan_lbl = QLabel("Layanan Sistem")
        layanan_lbl.setStyleSheet(f"color:{C['text_muted']};font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:1px;")
        root.addWidget(layanan_lbl)

        self.services_container = QWidget()
        self.services_layout = QVBoxLayout(self.services_container)
        self.services_layout.setContentsMargins(0, 0, 0, 0)
        self.services_layout.setSpacing(2)
        self._build_services()
        root.addWidget(self.services_container)

        root.addStretch()
        root.addWidget(Divider())

        # ── Footer ─────────────────────────────────────────────────────────────
        footer = QHBoxLayout()
        self.time_lbl = QLabel(self._last_check_text())
        self.time_lbl.setStyleSheet(f"color:{C['text_muted']};font-size:11px;")
        cek_btn = ActionButton("🔄  Cek Ulang", primary=False)
        cek_btn.setFixedWidth(130)
        cek_btn.clicked.connect(self._refresh)
        footer.addWidget(self.time_lbl)
        footer.addStretch()
        footer.addWidget(cek_btn)
        root.addLayout(footer)

        # Auto-refresh tiap 60 detik
        self._timer = QTimer()
        self._timer.timeout.connect(self._refresh)
        self._timer.start(60_000)

    # ── Build helpers ──────────────────────────────────────────────────────────

    def _build_cards(self):
        d = self.data
        cards = [
            ("Penyimpanan", d["storage"]["value"], d["storage"]["status"], d["storage"].get("detail","")),
            ("Memori",      d["memory"]["value"],  d["memory"]["status"],  d["memory"].get("detail","")),
            ("GPU",         d["gpu"]["value"],      d["gpu"]["status"],     d["gpu"].get("detail","")),
            ("Guardian",    d["guardian"]["value"], d["guardian"]["status"],d["guardian"].get("detail","")),
        ]
        for title, value, status, detail in cards:
            self.cards_layout.addWidget(MetricCard(title, value, status, detail))

    def _build_services(self):
        # Hapus widget lama
        while self.services_layout.count():
            w = self.services_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        failed = self.data["services"].get("failed", [])
        if not failed:
            row = ServiceRow("Semua layanan sistem berjalan normal", ok=True)
            self.services_layout.addWidget(row)
        else:
            for svc in failed:
                self.services_layout.addWidget(ServiceRow(svc, ok=False))

    # ── Data ──────────────────────────────────────────────────────────────────

    def _load_state(self) -> dict:
        if HEALTH_STATE_PATH.exists():
            try:
                return json.loads(HEALTH_STATE_PATH.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return FALLBACK_HEALTH.copy()

    def _overall_status(self) -> str:
        statuses = [
            self.data["storage"]["status"],
            self.data["memory"]["status"],
            self.data["gpu"]["status"],
            self.data["guardian"]["status"],
            self.data["services"]["status"],
        ]
        if "error" in statuses:
            return "error"
        if "warning" in statuses:
            return "warning"
        return "ok"

    def _last_check_text(self) -> str:
        ts = self.data.get("last_check")
        if not ts:
            return "Terakhir dicek: barusan"
        try:
            dt = datetime.fromisoformat(ts)
            return f"Terakhir dicek: {dt.strftime('%H:%M:%S')}"
        except ValueError:
            return f"Terakhir dicek: {ts}"

    def _refresh(self):
        self.data = self._load_state()

        # Update cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._build_cards()

        # Update services
        self._build_services()

        # Update overall badge
        overall = self._overall_status()
        label, color, _, _ = STATUS_CONFIG.get(overall, STATUS_CONFIG["ok"])
        text = "Semua Normal" if overall == "ok" else "Ada Peringatan" if overall == "warning" else "Ada Masalah"
        self.overall_badge.setText(f"● {text}")
        self.overall_badge.setStyleSheet(f"color:{color};font-size:13px;font-weight:600;")

        # Update timestamp
        self.data["last_check"] = datetime.now().isoformat()
        self.time_lbl.setText(self._last_check_text())


# ── Entry point ───────────────────────────────────────────────────────────────

def launch_sehat_check():
    """Dipanggil dari system tray atau notification dispatcher."""
    app = QApplication.instance() or QApplication(sys.argv)
    win = SehatCheckWindow()
    win.show()
    if not QApplication.instance():
        sys.exit(app.exec())
    return win


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SehatCheckWindow()
    win.show()
    sys.exit(app.exec())
