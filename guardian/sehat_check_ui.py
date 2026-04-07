"""
NusantaraOS — Sehat Check GUI
File: guardian/sehat_check_ui.py

Monitor kesehatan sistem dalam Bahasa Indonesia.
Auto-refresh tiap 5 detik — tidak perlu klik Cek Ulang.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QSizePolicy,
)

HEALTH_STATE_PATH = Path("/var/lib/nusantara/health-state.json")
GUARDIAN_DIR      = os.path.dirname(os.path.abspath(__file__))

FALLBACK_HEALTH = {
    "storage":  {"value": "2 GB tersisa",  "status": "warning", "detail": "Partisi / hampir penuh"},
    "memory":   {"value": "42% terpakai",  "status": "ok",      "detail": "3.4 GB dari 5.7 GB"},
    "gpu":      {"value": "Intel aktif",   "status": "ok",      "detail": "i915 — driver normal"},
    "guardian": {"value": "Aktif",         "status": "ok",      "detail": "Semua modul berjalan"},
    "services": {"failed": [],             "status": "ok"},
    "last_check": None,
}

C = {
    "bg":           "#1C0F0A",
    "surface":      "#2A1A12",
    "surface2":     "#3A2518",
    "border":       "#4A3020",
    "text":         "#F2E4C0",
    "text_muted":   "#A08060",
    "red":          "#8B1A1A",
    "red_bright":   "#C0302A",
    "gold":         "#C5940A",
    "gold_bright":  "#E8B020",
    "green":        "#1D5C38",
    "green_bright": "#2E8A52",
}

STATUS_CONFIG = {
    "ok":      ("Aman",       C["green_bright"], C["green"], C["green"]),
    "warning": ("Peringatan", C["gold_bright"],  C["gold"],  C["gold"]),
    "error":   ("Bahaya",     C["red_bright"],   C["red"],   C["red"]),
}

REFRESH_MS = 5_000


class Divider(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.HLine)
        self.setStyleSheet(f"background:{C['border']};min-height:1px;max-height:1px;border:none;")


class StatusBadge(QLabel):
    def __init__(self, status: str):
        label, color, _, _ = STATUS_CONFIG.get(status, STATUS_CONFIG["ok"])
        super().__init__(f"● {label}")
        self.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setStyleSheet(f"color:{color};font-size:12px;font-weight:600;background:transparent;border:none;")


class MetricCard(QFrame):
    def __init__(self, title: str, value: str, status: str, detail: str = ""):
        super().__init__()
        _, color, _, border = STATUS_CONFIG.get(status, STATUS_CONFIG["ok"])
        card_border = border if status != "ok" else C["border"]
        self.setStyleSheet(f"QFrame {{background:{C['surface']};border:1px solid {card_border};border-radius:10px;}}")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(110)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        t = QLabel(title)
        t.setStyleSheet(f"color:{C['text_muted']};font-size:13px;font-weight:500;border:none;background:transparent;")
        layout.addWidget(t)

        v = QLabel(value)
        v.setStyleSheet(f"color:{color};font-size:17px;font-weight:700;border:none;background:transparent;")
        v.setWordWrap(True)
        layout.addWidget(v)

        layout.addWidget(StatusBadge(status))

        if detail:
            d = QLabel(detail)
            d.setStyleSheet(f"color:{C['text_muted']};font-size:11px;border:none;background:transparent;")
            d.setWordWrap(True)
            layout.addWidget(d)

        layout.addStretch()


class ServiceRow(QWidget):
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
        bg, bg_h = (C["red"], C["red_bright"]) if primary else (C["surface2"], C["border"])
        self.setStyleSheet(f"""
            QPushButton {{background:{bg};color:{C['text']};border:1px solid {C['border']};
                border-radius:6px;padding:8px 20px;font-size:13px;font-weight:600;}}
            QPushButton:hover {{background:{bg_h};border-color:{C['gold']};}}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(38)


class SehatCheckWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data = self._load_state()

        self.setWindowTitle("NusantaraOS — Sehat Check")
        self.setMinimumSize(640, 460)
        self.setMaximumSize(900, 700)
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{background:{C['bg']};color:{C['text']};
                font-family:'Noto Sans','Segoe UI',sans-serif;}}
            QScrollBar:vertical {{width:4px;background:{C['surface']};}}
            QScrollBar::handle:vertical {{background:{C['border']};border-radius:2px;}}
        """)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(14)

        # Header
        header = QHBoxLayout()
        il = QHBoxLayout()
        il.setSpacing(8)
        heart = QLabel("❤")
        heart.setStyleSheet(f"color:{C['red_bright']};font-size:20px;")
        title = QLabel("Sehat Check")
        title.setStyleSheet(f"color:{C['text']};font-size:20px;font-weight:700;")
        il.addWidget(heart)
        il.addWidget(title)
        header.addLayout(il)
        header.addStretch()
        overall = self._overall_status()
        _, color, _, _ = STATUS_CONFIG.get(overall, STATUS_CONFIG["ok"])
        self.overall_badge = QLabel(f"● {'Semua Normal' if overall == 'ok' else 'Ada Peringatan' if overall == 'warning' else 'Ada Masalah'}")
        self.overall_badge.setStyleSheet(f"color:{color};font-size:13px;font-weight:600;")
        header.addWidget(self.overall_badge)
        root.addLayout(header)
        root.addWidget(Divider())

        # Kondisi Sistem
        kl = QLabel("KONDISI SISTEM")
        kl.setStyleSheet(f"color:{C['text_muted']};font-size:11px;font-weight:600;letter-spacing:1px;")
        root.addWidget(kl)
        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(10)
        self._build_cards()
        root.addLayout(self.cards_layout)
        root.addWidget(Divider())

        # Layanan Sistem
        ll = QLabel("LAYANAN SISTEM")
        ll.setStyleSheet(f"color:{C['text_muted']};font-size:11px;font-weight:600;letter-spacing:1px;")
        root.addWidget(ll)
        self.services_container = QWidget()
        self.services_layout = QVBoxLayout(self.services_container)
        self.services_layout.setContentsMargins(0, 0, 0, 0)
        self.services_layout.setSpacing(2)
        self._build_services()
        root.addWidget(self.services_container)

        root.addStretch()
        root.addWidget(Divider())

        # Footer
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

        # Auto-refresh tiap 5 detik
        self._timer = QTimer()
        self._timer.timeout.connect(self._refresh)
        self._timer.start(REFRESH_MS)

    def _build_cards(self):
        d = self.data
        for title, key in [("Penyimpanan","storage"),("Memori","memory"),("GPU","gpu"),("Guardian","guardian")]:
            self.cards_layout.addWidget(MetricCard(
                title, d[key]["value"], d[key]["status"], d[key].get("detail","")
            ))

    def _build_services(self):
        while self.services_layout.count():
            w = self.services_layout.takeAt(0).widget()
            if w: w.deleteLater()
        failed = self.data["services"].get("failed", [])
        if not failed:
            self.services_layout.addWidget(ServiceRow("Semua layanan sistem berjalan normal", ok=True))
        else:
            for svc in failed:
                self.services_layout.addWidget(ServiceRow(svc, ok=False))

    def _load_state(self) -> dict:
        if HEALTH_STATE_PATH.exists():
            try:
                return json.loads(HEALTH_STATE_PATH.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return FALLBACK_HEALTH.copy()

    def _run_health_check(self):
        try:
            sys.path.insert(0, GUARDIAN_DIR)
            from health_monitor import laporan_sehat
            laporan_sehat()
        except Exception:
            pass

    def _overall_status(self) -> str:
        statuses = [self.data[k]["status"] for k in ("storage","memory","gpu","guardian","services")]
        if "error"   in statuses: return "error"
        if "warning" in statuses: return "warning"
        return "ok"

    def _last_check_text(self) -> str:
        ts = self.data.get("last_check")
        if not ts: return "Terakhir dicek: barusan"
        try:
            return f"Terakhir dicek: {datetime.fromisoformat(ts).strftime('%H:%M:%S')}"
        except ValueError:
            return f"Terakhir dicek: {ts}"

    def _refresh(self):
        self._run_health_check()
        self.data = self._load_state()

        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self._build_cards()
        self._build_services()

        overall = self._overall_status()
        _, color, _, _ = STATUS_CONFIG.get(overall, STATUS_CONFIG["ok"])
        text = "Semua Normal" if overall == "ok" else "Ada Peringatan" if overall == "warning" else "Ada Masalah"
        self.overall_badge.setText(f"● {text}")
        self.overall_badge.setStyleSheet(f"color:{color};font-size:13px;font-weight:600;")
        self.time_lbl.setText(self._last_check_text())


def launch_sehat_check():
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
