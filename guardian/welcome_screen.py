"""
NusantaraOS — Welcome Screen
File: guardian/welcome_screen.py

Layar sambutan first boot. Muncul sekali saat login pertama kali
setelah instalasi. Setelah ditutup, tulis flag ke:
  /var/lib/nusantara/welcome-shown

Dipanggil dari:
  - nusantara-tray.desktop (autostart, cek flag dulu)
  - python welcome_screen.py (manual / testing)
"""

import json
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, QRectF, QTimer
from PyQt6.QtGui import (
    QColor, QPainter, QPainterPath, QBrush, QPen,
    QLinearGradient, QFont, QFontMetrics,
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QCheckBox, QSizePolicy, QSpacerItem,
)

# ── Path ──────────────────────────────────────────────────────────────────────

HEALTH_STATE_PATH  = Path("/var/lib/nusantara/health-state.json")
HW_STATE_PATH      = Path("/var/lib/nusantara/hw-state.json")
WELCOME_FLAG_PATH  = Path("/var/lib/nusantara/welcome-shown")

# ── Warna brand ───────────────────────────────────────────────────────────────

C = {
    "bg":           "#1C0F0A",   # Arang Kayu
    "surface":      "#2A1A12",
    "surface2":     "#3A2518",
    "border":       "#4A3020",
    "text":         "#F2E4C0",   # Krem Lawas
    "text_muted":   "#A08060",
    "red":          "#8B1A1A",   # Merah Saga
    "red_bright":   "#C0302A",
    "gold":         "#C5940A",   # Emas Keraton
    "gold_bright":  "#E8B020",
    "green":        "#1D5C38",   # Hijau Rimba
    "green_bright": "#2E8A52",
    "blue":         "#1A3F6F",   # Biru Samudera
    "blue_bright":  "#2E6BAA",
}

# ── Status helper ─────────────────────────────────────────────────────────────

STATUS_COLOR = {
    "ok":      C["green_bright"],
    "warning": C["gold_bright"],
    "error":   C["red_bright"],
}

STATUS_LABEL = {
    "ok":      "Aman",
    "warning": "Peringatan",
    "error":   "Bahaya",
}

# ── Kawung Logo Widget ────────────────────────────────────────────────────────

class KawungLogo(QWidget):
    """
    Motif kawung — 4 elips kardinal + lingkaran tengah emas.
    Dirender pakai QPainter langsung, tidak butuh file gambar.
    """
    def __init__(self, size: int = 72):
        super().__init__()
        self._size = size
        self.setFixedSize(size, size)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = cy = self._size / 2
        r = self._size / 2

        # 4 elips: atas, bawah, kiri, kanan — warna Merah Saga
        petal_rx = r * 0.38
        petal_ry = r * 0.22
        offset   = r * 0.44

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(C["red"])))

        for dx, dy, angle in [
            (0,       -offset, 0),   # atas
            (0,        offset, 0),   # bawah
            (-offset,  0,      90),  # kiri
            ( offset,  0,      90),  # kanan
        ]:
            path = QPainterPath()
            p.save()
            p.translate(cx + dx, cy + dy)
            p.rotate(angle)
            path.addEllipse(
                QRectF(-petal_rx, -petal_ry, petal_rx * 2, petal_ry * 2)
            )
            p.drawPath(path)
            p.restore()

        # Lingkaran tengah — Emas Keraton
        center_r = r * 0.22
        grad = QLinearGradient(cx - center_r, cy - center_r, cx + center_r, cy + center_r)
        grad.setColorAt(0.0, QColor(C["gold_bright"]))
        grad.setColorAt(1.0, QColor(C["gold"]))
        p.setBrush(QBrush(grad))
        p.drawEllipse(QRectF(cx - center_r, cy - center_r, center_r * 2, center_r * 2))

        p.end()


# ── Komponen UI ───────────────────────────────────────────────────────────────

class Divider(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.HLine)
        self.setStyleSheet(
            f"background:{C['border']};min-height:1px;max-height:1px;border:none;"
        )


class SnapshotRow(QWidget):
    """Satu baris di system snapshot — label + nilai + status dot."""
    def __init__(self, label: str, value: str, status: str = "ok"):
        super().__init__()
        color = STATUS_COLOR.get(status, C["green_bright"])
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)

        dot = QLabel("●")
        dot.setStyleSheet(f"color:{color};font-size:11px;min-width:16px;")
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color:{C['text_muted']};font-size:13px;min-width:110px;")
        val = QLabel(value)
        val.setStyleSheet(f"color:{C['text']};font-size:13px;font-weight:500;")
        val.setWordWrap(True)

        layout.addWidget(dot)
        layout.addWidget(lbl)
        layout.addWidget(val)
        layout.addStretch()


class ShortcutButton(QPushButton):
    """
    Tombol shortcut vertikal — ikon besar + label.
    Dipakai untuk Sehat Check, Manajer Driver, Terminal.
    """
    def __init__(self, icon: str, label: str, sub: str = ""):
        super().__init__()
        self.setFixedSize(150, 90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {C['surface']};
                border: 1px solid {C['border']};
                border-radius: 10px;
                color: {C['text']};
            }}
            QPushButton:hover {{
                background: {C['surface2']};
                border-color: {C['gold']};
            }}
            QPushButton:pressed {{
                background: {C['bg']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ico = QLabel(icon)
        ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico.setStyleSheet("font-size:24px;background:transparent;border:none;")

        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            f"color:{C['text']};font-size:12px;font-weight:600;"
            "background:transparent;border:none;"
        )

        layout.addWidget(ico)
        layout.addWidget(lbl)

        if sub:
            s = QLabel(sub)
            s.setAlignment(Qt.AlignmentFlag.AlignCenter)
            s.setStyleSheet(
                f"color:{C['text_muted']};font-size:10px;"
                "background:transparent;border:none;"
            )
            layout.addWidget(s)


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
                padding:10px 28px;
                font-size:14px;
                font-weight:600;
            }}
            QPushButton:hover {{
                background:{bg_h};
                border-color:{C['gold']};
            }}
            QPushButton:pressed {{
                background:{bg};
            }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(42)


# ── Main Window ───────────────────────────────────────────────────────────────

class WelcomeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._health = self._load_health()
        self._hw     = self._load_hw()

        self.setWindowTitle("NusantaraOS — Selamat Datang")
        self.setFixedSize(680, 580)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background:{C['bg']};
                color:{C['text']};
                font-family:'Noto Sans','Segoe UI',sans-serif;
            }}
            QCheckBox {{
                color:{C['text_muted']};
                font-size:12px;
                spacing:6px;
            }}
            QCheckBox::indicator {{
                width:14px;
                height:14px;
                border:1px solid {C['border']};
                border-radius:3px;
                background:{C['surface2']};
            }}
            QCheckBox::indicator:checked {{
                background:{C['red']};
                border-color:{C['red_bright']};
            }}
        """)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Banner atas ───────────────────────────────────────────────────────
        banner = self._build_banner()
        root.addWidget(banner)

        # ── Konten utama ──────────────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet(f"background:{C['bg']};")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(28, 20, 28, 0)
        body_layout.setSpacing(16)

        # System snapshot
        snapshot = self._build_snapshot()
        body_layout.addWidget(snapshot)

        # Shortcut buttons
        shortcuts = self._build_shortcuts()
        body_layout.addLayout(shortcuts)

        body_layout.addStretch()
        root.addWidget(body)

        # ── Footer ────────────────────────────────────────────────────────────
        root.addWidget(Divider())
        footer = self._build_footer()
        root.addWidget(footer)

    # ── Section builders ──────────────────────────────────────────────────────

    def _build_banner(self) -> QWidget:
        """Banner atas dengan gradien gelap — logo + judul + tagline."""
        banner = QWidget()
        banner.setFixedHeight(160)
        banner.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {C['surface']},
                    stop:1 {C['bg']}
                );
                border-bottom: 1px solid {C['border']};
            }}
        """)

        layout = QHBoxLayout(banner)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(24)

        # Logo
        logo = KawungLogo(size=80)
        layout.addWidget(logo)

        # Teks
        text_col = QVBoxLayout()
        text_col.setSpacing(6)

        greet = QLabel("Selamat Datang di")
        greet.setStyleSheet(
            f"color:{C['text_muted']};font-size:14px;font-weight:400;"
            "background:transparent;border:none;"
        )

        title = QLabel("NusantaraOS")
        title.setStyleSheet(
            f"color:{C['text']};font-size:28px;font-weight:800;"
            "letter-spacing:-0.5px;background:transparent;border:none;"
        )

        tagline = QLabel("Dari kepulauan, untuk semua.")
        tagline.setStyleSheet(
            f"color:{C['gold']};font-size:13px;font-style:italic;"
            "background:transparent;border:none;"
        )

        text_col.addWidget(greet)
        text_col.addWidget(title)
        text_col.addWidget(tagline)
        layout.addLayout(text_col)
        layout.addStretch()

        # Version badge
        ver_badge = QLabel("v0.1-alpha")
        ver_badge.setStyleSheet(f"""
            color:{C['text_muted']};
            background:{C['surface2']};
            border:1px solid {C['border']};
            border-radius:4px;
            padding:3px 10px;
            font-size:11px;
            font-weight:600;
        """)
        ver_badge.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(ver_badge)

        return banner

    def _build_snapshot(self) -> QFrame:
        """Kartu ringkasan kondisi sistem saat ini."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background:{C['surface']};
                border:1px solid {C['border']};
                border-radius:10px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        sec_lbl = QLabel("KONDISI SISTEM SAAT INI")
        sec_lbl.setStyleSheet(
            f"color:{C['text_muted']};font-size:11px;font-weight:600;"
            "letter-spacing:1px;background:transparent;border:none;"
        )
        layout.addWidget(sec_lbl)
        layout.addSpacing(6)

        # Baris snapshot dari health & hw state
        rows = self._snapshot_rows()
        for label, value, status in rows:
            layout.addWidget(SnapshotRow(label, value, status))

        return card

    def _snapshot_rows(self) -> list[tuple[str, str, str]]:
        h  = self._health
        hw = self._hw

        # GPU
        gpu_model  = hw.get("gpu_model", "Tidak terdeteksi")
        gpu_driver = hw.get("driver", "—")
        llvmpipe   = hw.get("using_llvmpipe", False)
        if llvmpipe:
            gpu_val    = f"{gpu_model} — ⚠ software rendering"
            gpu_status = "warning"
        else:
            gpu_val    = f"{gpu_model} ({gpu_driver})"
            gpu_status = "ok"

        # Memori
        mem_d  = h.get("memory", {})
        mem_val   = mem_d.get("value", "—")
        mem_status = mem_d.get("status", "ok")

        # Storage
        sto_d = h.get("storage", {})
        sto_val    = sto_d.get("value", "—")
        sto_status = sto_d.get("status", "ok")

        # Guardian
        grd_d  = h.get("guardian", {})
        grd_val    = grd_d.get("value", "Tidak diketahui")
        grd_status = grd_d.get("status", "ok")

        return [
            ("GPU",         gpu_val,  gpu_status),
            ("Memori",      mem_val,  mem_status),
            ("Penyimpanan", sto_val,  sto_status),
            ("Guardian",    grd_val,  grd_status),
        ]

    def _build_shortcuts(self) -> QHBoxLayout:
        """Tiga shortcut button horizontal."""
        layout = QHBoxLayout()
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        sec = QVBoxLayout()
        sec.setSpacing(8)

        lbl = QLabel("MULAI DARI SINI")
        lbl.setStyleSheet(
            f"color:{C['text_muted']};font-size:11px;font-weight:600;letter-spacing:1px;"
        )

        row = QHBoxLayout()
        row.setSpacing(12)
        row.setAlignment(Qt.AlignmentFlag.AlignLeft)

        btn_sehat = ShortcutButton("❤", "Sehat Check", "Monitor sistem")
        btn_sehat.clicked.connect(self._open_sehat_check)

        btn_driver = ShortcutButton("🔧", "Manajer Driver", "Kelola GPU")
        btn_driver.clicked.connect(self._open_driver_manager)

        btn_terminal = ShortcutButton("⬛", "Terminal", "Konsole / bash")
        btn_terminal.clicked.connect(self._open_terminal)

        row.addWidget(btn_sehat)
        row.addWidget(btn_driver)
        row.addWidget(btn_terminal)

        sec.addWidget(lbl)
        sec.addLayout(row)
        layout.addLayout(sec)
        layout.addStretch()

        return layout

    def _build_footer(self) -> QWidget:
        footer = QWidget()
        footer.setStyleSheet(f"background:{C['bg']};")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(28, 14, 28, 18)

        self._skip_cb = QCheckBox("Jangan tampilkan lagi saat login")
        layout.addWidget(self._skip_cb)
        layout.addStretch()

        close_btn = ActionButton("Mulai Jelajahi  →")
        close_btn.clicked.connect(self._dismiss)
        layout.addWidget(close_btn)

        return footer

    # ── Actions ───────────────────────────────────────────────────────────────

    def _open_sehat_check(self):
        try:
            import sys, os
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from sehat_check_ui import launch_sehat_check
            self._sehat_win = launch_sehat_check()
        except Exception as e:
            self._fallback_launch("sehat_check_ui.py", str(e))

    def _open_driver_manager(self):
        try:
            import sys, os
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from driver_manager_ui import launch_driver_manager
            self._driver_win = launch_driver_manager()
        except Exception as e:
            self._fallback_launch("driver_manager_ui.py", str(e))

    def _open_terminal(self):
        """Coba Konsole dulu, fallback ke xterm."""
        for term in ("konsole", "xterm", "gnome-terminal", "alacritty"):
            try:
                subprocess.Popen([term])
                return
            except FileNotFoundError:
                continue

    def _fallback_launch(self, script: str, err: str):
        """Kalau import gagal, launch sebagai subprocess."""
        import os
        guardian_dir = os.path.dirname(os.path.abspath(__file__))
        subprocess.Popen([sys.executable, os.path.join(guardian_dir, script)])

    def _dismiss(self):
        """Tutup welcome screen. Tulis flag kalau checkbox dicentang."""
        if self._skip_cb.isChecked():
            try:
                WELCOME_FLAG_PATH.parent.mkdir(parents=True, exist_ok=True)
                WELCOME_FLAG_PATH.touch()
            except OSError:
                pass
        self.close()

    # ── Data loaders ──────────────────────────────────────────────────────────

    def _load_health(self) -> dict:
        if HEALTH_STATE_PATH.exists():
            try:
                return json.loads(HEALTH_STATE_PATH.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "memory":   {"value": "—", "status": "ok"},
            "storage":  {"value": "—", "status": "ok"},
            "guardian": {"value": "Aktif", "status": "ok"},
        }

    def _load_hw(self) -> dict:
        if HW_STATE_PATH.exists():
            try:
                return json.loads(HW_STATE_PATH.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "gpu_model": "Tidak terdeteksi",
            "driver":    "—",
            "using_llvmpipe": False,
        }


# ── Entry point ───────────────────────────────────────────────────────────────

def should_show_welcome() -> bool:
    """
    Return True kalau welcome screen belum pernah di-dismiss dengan
    "Jangan tampilkan lagi". Dipanggil dari tray_icon.py / autostart.
    """
    return not WELCOME_FLAG_PATH.exists()


def launch_welcome():
    """
    Dipanggil dari tray_icon.py atau autostart.
    Kalau flag sudah ada, langsung return tanpa buka window.
    """
    if not should_show_welcome():
        return None
    app = QApplication.instance() or QApplication(sys.argv)
    win = WelcomeWindow()
    win.show()
    return win


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Mode dev — bypass flag check supaya bisa di-test berulang
    win = WelcomeWindow()
    win.show()
    sys.exit(app.exec())
