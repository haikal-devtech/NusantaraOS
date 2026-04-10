"""
NusantaraOS — Welcome Screen
File: guardian/welcome_screen.py

Layar sambutan first boot NusantaraOS.
Muncul otomatis saat user pertama kali login.

Dipanggil dari:
  - KDE autostart (nusantara-welcome.desktop)
  - Langsung: python3 welcome_screen.py
"""

import json
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QSpacerItem, QSizePolicy,
)

# ── Konstanta ──────────────────────────────────────────────────────────────────

FIRST_BOOT_FLAG = Path("/var/lib/nusantara/.welcome-shown")
GUARDIAN_DIR    = Path(__file__).parent

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


# ── Komponen ───────────────────────────────────────────────────────────────────

class Divider(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.HLine)
        self.setStyleSheet(
            f"background:{C['border']};min-height:1px;max-height:1px;border:none;"
        )


class ShortcutButton(QPushButton):
    """Tombol shortcut aplikasi — ikon + label."""
    def __init__(self, icon: str, label: str, desc: str, callback):
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"""
            QPushButton {{
                background:{C['surface']};
                border:1px solid {C['border']};
                border-radius:10px;
                text-align:left;
                padding:0px;
            }}
            QPushButton:hover {{
                background:{C['surface2']};
                border-color:{C['gold']};
            }}
            QPushButton:pressed {{
                background:{C['surface']};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        # Ikon
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            f"color:{C['gold_bright']};font-size:28px;background:transparent;border:none;"
        )
        icon_lbl.setFixedWidth(36)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        # Teks
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        name_lbl = QLabel(label)
        name_lbl.setStyleSheet(
            f"color:{C['text']};font-size:14px;font-weight:700;background:transparent;border:none;"
        )
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(
            f"color:{C['text_muted']};font-size:12px;background:transparent;border:none;"
        )
        text_col.addWidget(name_lbl)
        text_col.addWidget(desc_lbl)
        layout.addLayout(text_col)
        layout.addStretch()

        # Arrow
        arrow = QLabel("→")
        arrow.setStyleSheet(
            f"color:{C['text_muted']};font-size:16px;background:transparent;border:none;"
        )
        layout.addWidget(arrow)

        self.clicked.connect(callback)


class PrimaryButton(QPushButton):
    def __init__(self, text: str):
        super().__init__(text)
        self.setStyleSheet(f"""
            QPushButton {{
                background:{C['red']};
                color:{C['text']};
                border:1px solid {C['red_bright']};
                border-radius:8px;
                padding:12px 32px;
                font-size:15px;
                font-weight:700;
            }}
            QPushButton:hover {{
                background:{C['red_bright']};
                border-color:{C['gold']};
            }}
            QPushButton:pressed {{
                background:{C['red']};
            }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(48)


# ── Main Window ────────────────────────────────────────────────────────────────

class WelcomeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Selamat Datang di NusantaraOS")
        self.setMinimumSize(580, 620)
        self.setMaximumSize(700, 780)
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background:{C['bg']};
                color:{C['text']};
                font-family:'Noto Sans','Segoe UI',sans-serif;
            }}
        """)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(20)

        # ── Hero section ───────────────────────────────────────────────────────
        hero = QVBoxLayout()
        hero.setSpacing(8)

        # Kawung symbol (placeholder — bisa diganti SVG nanti)
        symbol = QLabel("◈")
        symbol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        symbol.setStyleSheet(
            f"color:{C['red_bright']};font-size:48px;background:transparent;"
        )
        hero.addWidget(symbol)

        title = QLabel("Selamat Datang di NusantaraOS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"color:{C['text']};font-size:22px;font-weight:700;background:transparent;"
        )
        hero.addWidget(title)

        tagline = QLabel("Dari kepulauan, untuk semua.")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setStyleSheet(
            f"color:{C['gold_bright']};font-size:14px;font-style:italic;background:transparent;"
        )
        hero.addWidget(tagline)

        version = QLabel("v0.1 Alpha — Halmahera")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet(
            f"color:{C['text_muted']};font-size:12px;background:transparent;"
        )
        hero.addWidget(version)

        root.addLayout(hero)
        root.addWidget(Divider())

        # ── Shortcut section ───────────────────────────────────────────────────
        shortcut_lbl = QLabel("Mulai dari sini")
        shortcut_lbl.setStyleSheet(
            f"color:{C['text_muted']};font-size:11px;font-weight:600;letter-spacing:1px;"
        )
        root.addWidget(shortcut_lbl)

        shortcuts = [
            ("❤", "Sehat Check",     "Pantau kesehatan sistem kamu",        self._buka_sehat_check),
            ("🔧", "Manajer Driver",  "Cek dan perbaiki driver GPU",         self._buka_driver_manager),
            ("📦", "Kelola Aplikasi", "Install aplikasi dari Flathub",       self._buka_flatpak),
            ("📖", "Panduan Memulai", "Pelajari cara pakai NusantaraOS",     self._buka_panduan),
        ]

        for icon, label, desc, cb in shortcuts:
            root.addWidget(ShortcutButton(icon, label, desc, cb))

        root.addWidget(Divider())

        # ── Footer ─────────────────────────────────────────────────────────────
        footer = QVBoxLayout()
        footer.setSpacing(10)

        self.show_again_btn = QPushButton("Jangan tampilkan lagi saat startup")
        self.show_again_btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent;
                color:{C['text_muted']};
                border:none;
                font-size:12px;
                text-decoration:underline;
            }}
            QPushButton:hover {{ color:{C['text']}; }}
        """)
        self.show_again_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_again_btn.clicked.connect(self._disable_autostart)

        mulai_btn = PrimaryButton("Mulai Menjelajah →")
        mulai_btn.clicked.connect(self.close)

        footer.addWidget(mulai_btn)
        footer.addWidget(self.show_again_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        root.addLayout(footer)

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _buka_sehat_check(self):
        try:
            sys.path.insert(0, str(GUARDIAN_DIR))
            from sehat_check_ui import SehatCheckWindow
            self._sehat = SehatCheckWindow()
            self._sehat.show()
        except Exception as e:
            print(f"Gagal buka Sehat Check: {e}")

    def _buka_driver_manager(self):
        try:
            sys.path.insert(0, str(GUARDIAN_DIR))
            from driver_manager_ui import DriverManagerWindow
            self._driver = DriverManagerWindow()
            self._driver.show()
        except Exception as e:
            print(f"Gagal buka Driver Manager: {e}")

    def _buka_flatpak(self):
        subprocess.Popen(["flatpak", "run", "org.gnome.Software"], 
                        stderr=subprocess.DEVNULL)

    def _buka_panduan(self):
        subprocess.Popen(["xdg-open", "https://github.com/haikal-devtech/NusantaraOS"],
                        stderr=subprocess.DEVNULL)

    def _disable_autostart(self):
        """Tulis flag — welcome screen tidak muncul lagi saat startup."""
        try:
            FIRST_BOOT_FLAG.parent.mkdir(parents=True, exist_ok=True)
            FIRST_BOOT_FLAG.touch()
            self.show_again_btn.setText("✓ Tidak akan muncul lagi saat startup")
            self.show_again_btn.setEnabled(False)
        except Exception as e:
            print(f"Gagal tulis flag: {e}")


# ── Entry point ────────────────────────────────────────────────────────────────

def should_show() -> bool:
    """Cek apakah welcome screen perlu ditampilkan."""
    return not FIRST_BOOT_FLAG.exists()


def launch_welcome(force: bool = False):
    app = QApplication.instance() or QApplication(sys.argv)
    if force or should_show():
        win = WelcomeWindow()
        win.show()
        if not QApplication.instance():
            sys.exit(app.exec())
        return win
    return None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # --force untuk test tanpa cek flag
    force = "--force" in sys.argv
    win = WelcomeWindow() if force or should_show() else None
    if win:
        win.show()
        sys.exit(app.exec())
    else:
        print("Welcome screen sudah pernah ditampilkan. Pakai --force untuk paksa tampil.")
        sys.exit(0)
