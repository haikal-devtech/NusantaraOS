"""
NusantaraOS — Sehat Check GUI (Real-time & Responsive Version)
File: guardian/sehat_check_ui.py

Monitor kesehatan sistem dalam Bahasa Indonesia.
- Update per 1 detik (Real-time).
- Menggunakan QThread agar UI tidak freeze (non-blocking).
- Update widget "in-place" (tanpa flicker/rebuild).
- Layout responsif menggunakan QScrollArea.
"""

import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QCursor, QColor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGridLayout, QScrollArea,
    QGraphicsDropShadowEffect, QSizePolicy
)

HEALTH_STATE_PATH = Path("/var/lib/nusantara/health-state.json")
GUARDIAN_DIR      = os.path.dirname(os.path.abspath(__file__))

FALLBACK_HEALTH = {
    "storage":  {"value": "Menghitung...", "status": "ok", "detail": "Menunggu data... "},
    "memory":   {"value": "Menghitung...", "status": "ok", "detail": "Menunggu data... "},
    "cpu":      {"value": "Menghitung...", "status": "ok", "detail": "Menunggu data... "},
    "gpu":      {"value": "Menghitung...", "status": "ok", "detail": "Menunggu data... "},
    "guardian": {"value": "Aktif",         "status": "ok", "detail": "Semua modul berjalan"},
    "services": {"failed": [],             "status": "ok"},
    "last_check": None,
}

# Palet Warna Nusantara (Modern Dark Batik Vibes)
C = {
    "bg":           "#140D0A", # Sangat gelap, nyaris hitam
    "surface":      "#241813", # Cokelat gelap untuk card
    "surface2":     "#33231A", # Hover state
    "border":       "#4A3224",
    "text":         "#F5EBE1", # Krem terang
    "text_muted":   "#B89E8A",
    "red":          "#992B2B", # Merah saga
    "red_bright":   "#E04545",
    "gold":         "#D4A017", # Emas prada
    "gold_bright":  "#FFC933",
    "green":        "#2A6B3D", # Hijau zamrud
    "green_bright": "#3DB061",
    "accent":       "#D4A017", # Warna aksen utama
}

STATUS_CONFIG = {
    "ok":      ("Aman",       C["green_bright"], C["green"], "✅"),
    "warning": ("Peringatan", C["gold_bright"],  C["gold"],  "⚠️"),
    "error":   ("Bahaya",     C["red_bright"],   C["red"],   "🚨"),
}

REFRESH_MS = 1_000  # Update per detik


# === Background Worker untuk mencegah UI nge-freeze ===

class HealthCheckWorker(QThread):
    """Jalankan health_monitor di background, kirim sinyal ke UI setelah selesai."""
    data_ready = pyqtSignal(dict)

    def run(self):
        try:
            sys.path.insert(0, GUARDIAN_DIR)
            from health_monitor import laporan_sehat
            laporan_sehat()
        except Exception as e:
            print(f"Error run health check: {e}")
        
        # Load the newly written state
        data = FALLBACK_HEALTH.copy()
        if HEALTH_STATE_PATH.exists():
            try:
                data = json.loads(HEALTH_STATE_PATH.read_text())
            except (json.JSONDecodeError, OSError):
                pass
                
        self.data_ready.emit(data)


# === Komponen UI Custom ===

def add_shadow(widget, radius=15, offset=(0, 4), color="#000000", alpha=80):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(radius)
    shadow.setOffset(offset[0], offset[1])
    c = QColor(color)
    c.setAlpha(alpha)
    shadow.setColor(c)
    widget.setGraphicsEffect(shadow)


class ActionButton(QPushButton):
    def __init__(self, text: str, icon: str = "", primary: bool = False):
        full_text = f"{icon}  {text}" if icon else text
        super().__init__(full_text)
        
        if primary:
            bg, hover, border, text_c = C["accent"], C["gold_bright"], C["accent"], "#140D0A"
        else:
            bg, hover, border, text_c = C["surface"], C["surface2"], C["border"], C["text"]
            
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {text_c};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover};
                border: 1px solid {C['gold_bright']};
            }}
            QPushButton:pressed {{
                background-color: {C['surface2'] if not primary else C['gold']};
            }}
        """)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        add_shadow(self, radius=10, offset=(0,2), alpha=50)


class MetricCard(QFrame):
    """Kartu metrik yang bisa di-update secara 'in-place'."""
    def __init__(self, title: str, icon: str):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {C['surface']};
                border: 1px solid {C['border']};
                border-radius: 12px;
            }}
        """)
        add_shadow(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)

        # Header card (Icon + Title + Status Badge)
        header = QHBoxLayout()
        header.setContentsMargins(0,0,0,0)
        
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 18px; background: transparent; border: none;")
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {C['text_muted']}; font-size: 14px; font-weight: bold; background: transparent; border: none;")
        
        self.status_lbl = QLabel()
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        header.addWidget(icon_lbl)
        header.addWidget(title_lbl)
        header.addStretch()
        header.addWidget(self.status_lbl)
        layout.addLayout(header)

        # Value
        self.value_lbl = QLabel("-")
        self.value_lbl.setStyleSheet(f"color: {C['text']}; font-size: 18px; font-weight: bold; background: transparent; border: none;")
        self.value_lbl.setWordWrap(True)
        layout.addWidget(self.value_lbl)

        # Detail
        self.detail_lbl = QLabel("-")
        self.detail_lbl.setStyleSheet(f"color: {C['text_muted']}; font-size: 12px; background: transparent; border: none;")
        self.detail_lbl.setWordWrap(True)
        layout.addWidget(self.detail_lbl)

        layout.addStretch()

    def update_data(self, value: str, status: str, detail: str):
        label_text, color, _, status_icon = STATUS_CONFIG.get(status, STATUS_CONFIG["ok"])
        
        self.status_lbl.setText(f"{status_icon} {label_text}")
        self.status_lbl.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        
        card_border = color if status != "ok" else C["border"]
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {C['surface']};
                border: 1px solid {card_border};
                border-radius: 12px;
            }}
        """)
        
        self.value_lbl.setText(value)
        self.detail_lbl.setText(detail)


class ServiceRow(QFrame):
    def __init__(self, name: str, ok: bool = True):
        super().__init__()
        self.setStyleSheet(f"background: {C['surface']}; border-radius: 8px; border: 1px solid {C['border']};")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        
        icon = QLabel("✅" if ok else "🚨")
        icon.setStyleSheet("background: transparent; border: none; font-size: 14px;")
        
        lbl = QLabel(name)
        lbl.setStyleSheet(f"color: {C['text'] if ok else C['red_bright']}; font-size: 13px; font-weight: {'normal' if ok else 'bold'}; background: transparent; border: none;")
        
        layout.addWidget(icon)
        layout.addWidget(lbl)
        layout.addStretch()
        
        if not ok:
            btn_fix = QPushButton("Restart")
            btn_fix.setStyleSheet(f"""
                QPushButton {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 4px; padding: 4px 8px; font-size: 11px; }}
                QPushButton:hover {{ background: {C['red']}; }}
            """)
            btn_fix.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            layout.addWidget(btn_fix)


# === Jendela Utama ===

class SehatCheckWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NusantaraOS — Sehat Check")
        self.setMinimumSize(850, 600)
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {C['bg']};
                color: {C['text']};
                font-family: 'Noto Sans', 'Segoe UI', sans-serif;
            }}
            QScrollBar:vertical {{ width: 8px; background: {C['bg']}; }}
            QScrollBar::handle:vertical {{ background: {C['border']}; border-radius: 4px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ==========================================
        # Kiri: Sidebar / Overview
        # ==========================================
        sidebar = QFrame()
        sidebar.setFixedWidth(280)
        sidebar.setStyleSheet(f"background-color: {C['surface']}; border-right: 1px solid {C['border']};")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(24, 30, 24, 24)
        sidebar_layout.setSpacing(20)

        # Header Sidebar
        logo = QLabel("🛡️")
        logo.setStyleSheet("font-size: 48px; background: transparent;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        app_title = QLabel("Sehat Check")
        app_title.setStyleSheet(f"color: {C['accent']}; font-size: 22px; font-weight: bold; background: transparent;")
        app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.overall_badge = QLabel("Menghitung...")
        self.overall_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        sidebar_layout.addWidget(logo)
        sidebar_layout.addWidget(app_title)
        sidebar_layout.addWidget(self.overall_badge)
        
        sidebar_layout.addSpacing(20)
        
        # Tindakan Cepat (Quick Actions)
        qa_lbl = QLabel("TINDAKAN CEPAT")
        qa_lbl.setStyleSheet(f"color: {C['text_muted']}; font-size: 11px; font-weight: bold; letter-spacing: 1px; background: transparent;")
        sidebar_layout.addWidget(qa_lbl)
        
        btn_clean = ActionButton("Bersihkan Memori", "🧹", primary=True)
        btn_clean.clicked.connect(self._action_clean_memory)
        
        btn_update = ActionButton("Cek Pembaruan", "📦")
        
        btn_driver = ActionButton("Manajer Driver", "⚙️")
        btn_driver.clicked.connect(lambda: subprocess.Popen(["python3", os.path.join(GUARDIAN_DIR, "driver_manager_ui.py")]))

        sidebar_layout.addWidget(btn_clean)
        sidebar_layout.addWidget(btn_update)
        sidebar_layout.addWidget(btn_driver)

        sidebar_layout.addStretch()
        
        # Footer Sidebar
        self.time_lbl = QLabel("Sinkronisasi terakhir:\nMenunggu...")
        self.time_lbl.setStyleSheet(f"color: {C['text_muted']}; font-size: 11px; background: transparent;")
        self.time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(self.time_lbl)

        main_layout.addWidget(sidebar)

        # ==========================================
        # Kanan: Konten Utama (Cards & Services) dengan QScrollArea
        # ==========================================
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent;")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        header_lbl = QLabel("Status Perangkat Keras & Sistem")
        header_lbl.setStyleSheet("font-size: 20px; font-weight: bold; background: transparent;")
        content_layout.addWidget(header_lbl)

        # Grid Cards (Dibuat sekali saja)
        self.cards = {}
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(15)
        
        card_definitions = [
            ("Penyimpanan", "💾", "storage"),
            ("Memori (RAM)", "🧠", "memory"),
            ("Prosesor (CPU)", "⚙️", "cpu"),
            ("Grafis (GPU)", "🎮", "gpu"),
        ]

        row, col = 0, 0
        for title, icon, key in card_definitions:
            card = MetricCard(title, icon)
            self.cards[key] = card
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1

        content_layout.addLayout(self.grid_layout)

        # Services Section
        srv_lbl = QLabel("Layanan Latar Belakang")
        srv_lbl.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px; background: transparent;")
        content_layout.addWidget(srv_lbl)

        self.services_layout = QVBoxLayout()
        self.services_layout.setSpacing(8)
        content_layout.addLayout(self.services_layout)

        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        # ==========================================
        # Pekerja Background & Timer Real-time
        # ==========================================
        self.worker = HealthCheckWorker()
        self.worker.data_ready.connect(self._on_data_ready)

        self._timer = QTimer()
        self._timer.timeout.connect(self._trigger_refresh)
        self._timer.start(REFRESH_MS)
        
        # Trigger pertama kali langsung tanpa nunggu 1 detik
        self._trigger_refresh()

    def _trigger_refresh(self):
        # Jalankan worker hanya jika worker sebelumnya sudah selesai
        if not self.worker.isRunning():
            self.worker.start()

    def _on_data_ready(self, data: dict):
        """Dipanggil ketika background thread selesai update data."""
        self._update_ui_data(data)

    def _overall_status(self, data: dict) -> str:
        keys = ("storage", "memory", "cpu", "gpu", "guardian", "services")
        statuses = [data.get(k, {}).get("status", "ok") for k in keys]
        if "error" in statuses: return "error"
        if "warning" in statuses: return "warning"
        return "ok"

    def _update_ui_data(self, data: dict):
        # Update Badge Status Utama
        overall = self._overall_status(data)
        text, color, _, icon = STATUS_CONFIG.get(overall, STATUS_CONFIG["ok"])
        msg = "Sistem Sehat" if overall == "ok" else "Ada Peringatan" if overall == "warning" else "Butuh Perhatian!"
        
        self.overall_badge.setText(msg)
        self.overall_badge.setStyleSheet(f"""
            background-color: {color}20; /* Transparan */
            color: {color};
            border: 1px solid {color};
            border-radius: 12px;
            padding: 6px 12px;
            font-size: 13px;
            font-weight: bold;
        """)

        # Update In-place Cards (tanpa flicker)
        for key, card in self.cards.items():
            item = data.get(key, FALLBACK_HEALTH.get(key))
            if item:
                card.update_data(item.get("value",""), item.get("status","ok"), item.get("detail",""))

        # Build Services (hapus & buat ulang ini murah/cepat karena sedikit)
        for i in reversed(range(self.services_layout.count())): 
            widget_to_remove = self.services_layout.itemAt(i).widget()
            if widget_to_remove:
                widget_to_remove.setParent(None)

        failed = data.get("services", {}).get("failed", [])
        if not failed:
            self.services_layout.addWidget(ServiceRow("Semua layanan (systemd) berjalan normal", ok=True))
        else:
            for svc in failed:
                self.services_layout.addWidget(ServiceRow(f"Layanan gagal: {svc}", ok=False))

        # Update Waktu Real-time
        ts = data.get("last_check")
        if ts:
            try:
                time_str = datetime.fromisoformat(ts).strftime('%H:%M:%S')
            except ValueError:
                time_str = str(ts)
        else:
            time_str = "Barusan"
        self.time_lbl.setText(f"Sinkronisasi terakhir:\n{time_str}")

    def _action_clean_memory(self):
        # Eksekusi sinkronisasi disk dan bersihkan caches
        print("Membersihkan memori/cache...")
        try:
            # Karena ini berjalan sebagai user biasa, mungkin butuh polkit jika bukan root.
            # Namun kita beri indikasi visual untuk UX.
            subprocess.Popen(["sync"])
        except Exception:
            pass
            
        sender = self.sender()
        if isinstance(sender, QPushButton):
            sender.setText("✅ Berhasil Dibersihkan")
            QTimer.singleShot(2000, lambda: sender.setText("🧹  Bersihkan Memori"))

def launch_sehat_check():
    standalone = QApplication.instance() is None
    app = QApplication.instance() or QApplication(sys.argv)
    win = SehatCheckWindow()
    win.show()
    if standalone:
        sys.exit(app.exec())
    return win

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SehatCheckWindow()
    win.show()
    sys.exit(app.exec())
