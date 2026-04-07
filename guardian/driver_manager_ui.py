"""
NusantaraOS — Driver Manager GUI
File: guardian/driver_manager_ui.py

Tampilan PyQt6 untuk manajemen driver GPU.
Baca state dari /var/lib/nusantara/hw-state.json,
kirim perintah ke Guardian daemon lewat Unix socket IPC.

Dipanggil dari:
  - NotificationDispatcher (tombol "Perbaiki Driver")
  - System tray menu "Kelola Driver"
  - Welcome Screen shortcut
"""

import json
import os
import socket
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QFont, QPalette, QPixmap, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QProgressBar, QMessageBox,
    QStackedWidget, QSpacerItem, QSizePolicy, QGraphicsDropShadowEffect,
)

# ── Konstanta ──────────────────────────────────────────────────────────────────

HW_STATE_PATH    = Path("/var/lib/nusantara/hw-state.json")
GUARDIAN_SOCKET  = "/run/nusantara/guardian.sock"
LOG_PATH         = Path("/var/log/nusantara/driver_manager.log")

# Fallback state kalau file belum ada (dev mode)
FALLBACK_HW_STATE = {
    "gpu_vendor":  "intel",
    "gpu_model":   "Intel HD Graphics (Gen 2)",
    "pci_id":      "8086:0166",
    "driver":      "i915",
    "using_llvmpipe": False,
    "last_seen_pci_id": "8086:0166",
}

# Warna brand NusantaraOS
COLORS = {
    "bg":          "#1C0F0A",   # Arang Kayu
    "surface":     "#2A1A12",
    "surface2":    "#3A2518",
    "border":      "#4A3020",
    "text":        "#F2E4C0",   # Krem Lawas
    "text_muted":  "#A08060",
    "red":         "#8B1A1A",   # Merah Saga
    "red_bright":  "#C0302A",
    "gold":        "#C5940A",   # Emas Keraton
    "gold_bright": "#E8B020",
    "green":       "#1D5C38",   # Hijau Rimba
    "green_bright":"#2E8A52",
    "blue":        "#1A3F6F",   # Biru Samudera
    "blue_bright": "#2E6BAA",
    "amber":       "#D4860A",
    "warn_bg":     "#3A2800",
    "ok_bg":       "#0A2A18",
    "err_bg":      "#2A0A0A",
}

VENDOR_LABELS = {
    "amd":    ("AMD", "radeon / amdgpu"),
    "intel":  ("Intel", "i915 / xe"),
    "nvidia": ("NVIDIA", "nouveau / proprietary"),
    "vm":     ("Virtual GPU", "llvmpipe / virtio"),
    "unknown":("Tidak Dikenali", "—"),
}

DRIVER_DISPLAY = {
    "amdgpu":      ("amdgpu", COLORS["green_bright"]),
    "radeon":      ("radeon (legacy)", COLORS["amber"]),
    "radv":        ("radv (Mesa Vulkan)", COLORS["green_bright"]),
    "i915":        ("i915", COLORS["green_bright"]),
    "xe":          ("xe (Intel Arc)", COLORS["green_bright"]),
    "iris":        ("iris (Mesa)", COLORS["green_bright"]),
    "nouveau":     ("nouveau (open)", COLORS["amber"]),
    "nvidia":      ("NVIDIA proprietary", COLORS["green_bright"]),
    "llvmpipe":    ("llvmpipe ⚠️ Software", COLORS["red_bright"]),
    "unknown":     ("Tidak terdeteksi", COLORS["red_bright"]),
}

# ── Worker thread — jangan block UI ───────────────────────────────────────────

class DriverInstallWorker(QThread):
    """
    Jalankan proses instalasi driver di background thread.
    Emit progress string dan selesai/error signal.
    """
    progress   = pyqtSignal(str)
    finished   = pyqtSignal(bool, str)   # sukses, pesan

    def __init__(self, vendor: str, action: str):
        super().__init__()
        self.vendor = vendor
        self.action = action

    def run(self):
        try:
            if self.vendor == "nvidia" and self.action == "install_proprietary":
                self._install_nvidia_proprietary()
            elif self.action == "rebuild_dkms":
                self._rebuild_dkms()
            elif self.action == "reset_to_open":
                self._reset_to_open()
            elif self.action == "send_guardian_event":
                self._send_guardian_event("DRIVER_FIX_REQUESTED", {"vendor": self.vendor})
                self.finished.emit(True, "Permintaan dikirim ke Guardian daemon.")
            else:
                self.finished.emit(False, f"Aksi tidak dikenali: {self.action}")
        except Exception as e:
            self.finished.emit(False, str(e))

    def _install_nvidia_proprietary(self):
        steps = [
            ("Memeriksa paket yang tersedia...",    ["pacman", "-Si", "nvidia"]),
            ("Menginstal driver NVIDIA...",          ["sudo", "pacman", "-S", "--noconfirm", "nvidia", "nvidia-utils"]),
            ("Memperbarui initramfs...",             ["sudo", "mkinitcpio", "-P"]),
        ]
        for label, cmd in steps:
            self.progress.emit(label)
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.finished.emit(False, f"Gagal: {label}\n{result.stderr[:300]}")
                return
        self.finished.emit(True, "Driver NVIDIA proprietary berhasil diinstal.\nRestart diperlukan.")

    def _rebuild_dkms(self):
        self.progress.emit("Membangun ulang DKMS modules...")
        result = subprocess.run(["sudo", "dkms", "autoinstall"], capture_output=True, text=True)
        if result.returncode == 0:
            self.finished.emit(True, "DKMS modules berhasil dibangun ulang.")
        else:
            self.finished.emit(False, f"DKMS gagal:\n{result.stderr[:300]}")

    def _reset_to_open(self):
        self.progress.emit("Menghapus driver proprietary...")
        subprocess.run(["sudo", "pacman", "-Rns", "--noconfirm", "nvidia", "nvidia-utils"],
                       capture_output=True)
        self.progress.emit("Mengaktifkan nouveau...")
        subprocess.run(["sudo", "modprobe", "nouveau"], capture_output=True)
        self.finished.emit(True, "Driver NVIDIA direset ke nouveau.\nRestart mungkin diperlukan.")

    def _send_guardian_event(self, event_type: str, payload: dict):
        try:
            msg = json.dumps({"type": event_type, "payload": payload})
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(GUARDIAN_SOCKET)
                s.sendall(msg.encode())
        except Exception as e:
            self.progress.emit(f"Guardian tidak terjangkau ({e}) — lanjut manual.")


# ── Komponen UI kecil ──────────────────────────────────────────────────────────

def _sheet(base: str) -> str:
    """Helper buat QSS multiline."""
    return base.strip()


class Divider(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.HLine)
        self.setStyleSheet(f"background: {COLORS['border']}; min-height: 1px; max-height: 1px; border: none;")


class Badge(QLabel):
    def __init__(self, text: str, color: str, bg: str):
        super().__init__(text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background: {bg};
                border: 1px solid {color};
                border-radius: 4px;
                padding: 2px 10px;
                font-size: 12px;
                font-weight: 600;
            }}
        """)
        self.setFixedHeight(24)


class GPUInfoCard(QFrame):
    """
    Kartu atas — vendor, model, PCI ID, driver aktif.
    """
    def __init__(self, state: dict):
        super().__init__()
        self.setObjectName("GPUCard")
        self.setStyleSheet(f"""
            QFrame#GPUCard {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                padding: 4px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(18, 14, 18, 14)

        vendor    = state.get("gpu_vendor", "unknown")
        model     = state.get("gpu_model", "Tidak terdeteksi")
        pci_id    = state.get("pci_id", "—")
        driver    = state.get("driver", "unknown")
        llvmpipe  = state.get("using_llvmpipe", False)

        vendor_name, vendor_sub = VENDOR_LABELS.get(vendor, VENDOR_LABELS["unknown"])
        driver_label, driver_color = DRIVER_DISPLAY.get(
            "llvmpipe" if llvmpipe else driver, DRIVER_DISPLAY["unknown"]
        )

        # Baris atas: nama vendor + badge driver
        top = QHBoxLayout()
        vendor_lbl = QLabel(vendor_name)
        vendor_lbl.setStyleSheet(f"color: {COLORS['text']}; font-size: 18px; font-weight: 700;")
        top.addWidget(vendor_lbl)
        top.addStretch()
        top.addWidget(Badge(
            "⚠ Software Rendering" if llvmpipe else "● Driver Aktif",
            COLORS["red_bright"] if llvmpipe else COLORS["green_bright"],
            COLORS["err_bg"] if llvmpipe else COLORS["ok_bg"],
        ))
        layout.addLayout(top)

        # Model GPU
        model_lbl = QLabel(model)
        model_lbl.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px;")
        layout.addWidget(model_lbl)

        layout.addWidget(Divider())

        # Detail row: PCI ID + driver
        details = QHBoxLayout()
        for label, value, color in [
            ("PCI ID",  pci_id,       COLORS["text_muted"]),
            ("Driver",  driver_label, driver_color),
            ("Stack",   vendor_sub,   COLORS["text_muted"]),
        ]:
            col = QVBoxLayout()
            col.setSpacing(2)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; font-weight: 600; text-transform: uppercase;")
            val = QLabel(value)
            val.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 500;")
            col.addWidget(lbl)
            col.addWidget(val)
            details.addLayout(col)
            if label != "Stack":
                details.addWidget(_vline())
        layout.addLayout(details)


def _vline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.VLine)
    line.setStyleSheet(f"background: {COLORS['border']}; min-width: 1px; max-width: 1px; border: none;")
    return line


class ActionButton(QPushButton):
    """
    Tombol aksi utama — ada dua varian: primary (merah saga) dan secondary.
    """
    def __init__(self, text: str, primary: bool = True):
        super().__init__(text)
        if primary:
            bg, bg_h, fg = COLORS["red"], COLORS["red_bright"], COLORS["text"]
        else:
            bg, bg_h, fg = COLORS["surface2"], COLORS["border"], COLORS["text"]
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                color: {fg};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {bg_h};
                border-color: {COLORS['gold']};
            }}
            QPushButton:pressed {{
                background: {bg};
            }}
            QPushButton:disabled {{
                background: {COLORS['surface']};
                color: {COLORS['text_muted']};
                border-color: {COLORS['border']};
            }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(42)


# ── Panel per skenario driver ─────────────────────────────────────────────────

class PanelOK(QWidget):
    """Driver aman — tampilkan status + opsi advanced."""
    def __init__(self, state: dict, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        vendor = state.get("gpu_vendor", "unknown")

        ok_box = QFrame()
        ok_box.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['ok_bg']};
                border: 1px solid {COLORS['green']};
                border-radius: 8px;
                padding: 6px;
            }}
        """)
        ok_layout = QVBoxLayout(ok_box)
        ok_layout.setContentsMargins(14, 12, 14, 12)
        ico = QLabel("✅  Driver berjalan normal")
        ico.setStyleSheet(f"color: {COLORS['green_bright']}; font-size: 14px; font-weight: 600;")
        desc = QLabel("Tidak ada tindakan yang diperlukan. Sistem menggunakan driver GPU terbaik yang tersedia.")
        desc.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px;")
        desc.setWordWrap(True)
        ok_layout.addWidget(ico)
        ok_layout.addWidget(desc)
        layout.addWidget(ok_box)

        if vendor == "nvidia":
            layout.addWidget(Divider())
            adv_lbl = QLabel("Opsi lanjutan — NVIDIA")
            adv_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; font-weight: 600;")
            layout.addWidget(adv_lbl)
            row = QHBoxLayout()
            row.addWidget(ActionButton("🔁  Bangun Ulang DKMS", primary=False))
            row.addWidget(ActionButton("↩  Reset ke Nouveau", primary=False))
            layout.addLayout(row)

        layout.addStretch()


class PanelLlvmpipe(QWidget):
    """
    Fallback llvmpipe aktif — warning + tombol perbaiki.
    Emit signal install_requested(vendor, action).
    """
    install_requested = pyqtSignal(str, str)

    def __init__(self, state: dict, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        vendor = state.get("gpu_vendor", "unknown")

        warn_box = QFrame()
        warn_box.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['warn_bg']};
                border: 1px solid {COLORS['gold']};
                border-radius: 8px;
                padding: 6px;
            }}
        """)
        w_layout = QVBoxLayout(warn_box)
        w_layout.setContentsMargins(14, 12, 14, 12)
        title = QLabel("⚠️  Software Rendering Aktif")
        title.setStyleSheet(f"color: {COLORS['gold_bright']}; font-size: 14px; font-weight: 700;")
        body = QLabel(
            "GPU kamu terdeteksi, tapi driver hardware gagal dimuat. "
            "Sistem sekarang pakai software rendering (llvmpipe) — "
            "performa grafis sangat terbatas dan gaming tidak akan jalan."
        )
        body.setWordWrap(True)
        body.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px; line-height: 1.5;")
        w_layout.addWidget(title)
        w_layout.addWidget(body)
        layout.addWidget(warn_box)

        # Tombol aksi utama
        fix_btn = ActionButton(f"🔧  Perbaiki Driver — {VENDOR_LABELS.get(vendor, ('GPU',''))[0]}")
        fix_btn.clicked.connect(lambda: self.install_requested.emit(vendor, "send_guardian_event"))
        layout.addWidget(fix_btn)

        if vendor == "nvidia":
            nvidia_btn = ActionButton("⬇  Instal Driver NVIDIA Proprietary", primary=False)
            nvidia_btn.clicked.connect(lambda: self.install_requested.emit("nvidia", "install_proprietary"))
            layout.addWidget(nvidia_btn)

        layout.addWidget(Divider())
        note = QLabel("💡  Setelah driver diperbaiki, restart diperlukan agar perubahan berlaku.")
        note.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()


class PanelNvidiaSetup(QWidget):
    """
    GPU NVIDIA dengan driver terbuka (nouveau) — tawarkan proprietary.
    """
    install_requested = pyqtSignal(str, str)

    def __init__(self, state: dict, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info_box = QFrame()
        info_box.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface2']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 6px;
            }}
        """)
        i_layout = QVBoxLayout(info_box)
        i_layout.setContentsMargins(14, 12, 14, 12)
        title = QLabel("🟡  NVIDIA terdeteksi — driver terbuka aktif")
        title.setStyleSheet(f"color: {COLORS['gold_bright']}; font-size: 14px; font-weight: 700;")
        body = QLabel(
            "Nouveau (driver open-source) sedang aktif. Driver ini aman untuk pemakaian sehari-hari, "
            "tapi performa gaming dan Vulkan jauh di bawah driver proprietary NVIDIA.\n\n"
            "Instal driver proprietary untuk performa maksimal."
        )
        body.setWordWrap(True)
        body.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px;")
        i_layout.addWidget(title)
        i_layout.addWidget(body)
        layout.addWidget(info_box)

        install_btn = ActionButton("⬇  Instal Driver NVIDIA Proprietary (Disarankan)")
        install_btn.clicked.connect(lambda: self.install_requested.emit("nvidia", "install_proprietary"))
        layout.addWidget(install_btn)

        dkms_btn = ActionButton("🔁  Bangun Ulang DKMS (jika driver sudah ada)", primary=False)
        dkms_btn.clicked.connect(lambda: self.install_requested.emit("nvidia", "rebuild_dkms"))
        layout.addWidget(dkms_btn)
        layout.addStretch()


class PanelProgress(QWidget):
    """Progress view saat instalasi berjalan."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        self.status_lbl = QLabel("Mempersiapkan...")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px;")
        self.status_lbl.setWordWrap(True)

        self.bar = QProgressBar()
        self.bar.setRange(0, 0)  # indeterminate
        self.bar.setFixedHeight(6)
        self.bar.setTextVisible(False)
        self.bar.setStyleSheet(f"""
            QProgressBar {{
                background: {COLORS['surface2']};
                border-radius: 3px;
                border: none;
            }}
            QProgressBar::chunk {{
                background: {COLORS['gold']};
                border-radius: 3px;
            }}
        """)

        note = QLabel("Jangan tutup jendela ini selama proses berlangsung.")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")

        layout.addStretch()
        layout.addWidget(self.status_lbl)
        layout.addWidget(self.bar)
        layout.addWidget(note)
        layout.addStretch()

    def update_status(self, msg: str):
        self.status_lbl.setText(msg)


# ── Main Window ───────────────────────────────────────────────────────────────

class DriverManagerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker: QThread | None = None
        self.state = self._load_hw_state()

        self.setWindowTitle("NusantaraOS — Manajer Driver")
        self.setMinimumSize(560, 440)
        self.setMaximumSize(700, 600)
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background: {COLORS['bg']};
                color: {COLORS['text']};
                font-family: 'Noto Sans', 'Segoe UI', sans-serif;
            }}
            QScrollBar {{ width: 0px; }}
        """)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title = QLabel("Manajer Driver")
        title.setStyleSheet(f"color: {COLORS['text']}; font-size: 20px; font-weight: 700;")
        subtitle = QLabel("NusantaraOS Guardian")
        subtitle.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        sub_col = QVBoxLayout()
        sub_col.addWidget(title)
        sub_col.addWidget(subtitle)
        header.addLayout(sub_col)
        header.addStretch()
        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("Refresh deteksi hardware")
        refresh_btn.setFixedSize(36, 36)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['surface2']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                color: {COLORS['text_muted']};
                font-size: 16px;
            }}
            QPushButton:hover {{
                background: {COLORS['border']};
                color: {COLORS['text']};
            }}
        """)
        refresh_btn.clicked.connect(self._refresh)
        header.addWidget(refresh_btn)
        root.addLayout(header)

        root.addWidget(Divider())

        # GPU info card
        self.gpu_card = GPUInfoCard(self.state)
        root.addWidget(self.gpu_card)

        root.addWidget(Divider())

        # Stacked action panels
        self.stack = QStackedWidget()
        self.panel_ok       = PanelOK(self.state)
        self.panel_llvmpipe = PanelLlvmpipe(self.state)
        self.panel_nvidia   = PanelNvidiaSetup(self.state)
        self.panel_progress = PanelProgress()

        self.stack.addWidget(self.panel_ok)        # index 0
        self.stack.addWidget(self.panel_llvmpipe)  # index 1
        self.stack.addWidget(self.panel_nvidia)    # index 2
        self.stack.addWidget(self.panel_progress)  # index 3

        self.panel_llvmpipe.install_requested.connect(self._start_install)
        self.panel_nvidia.install_requested.connect(self._start_install)

        root.addWidget(self.stack)

        # Footer
        root.addWidget(Divider())
        footer = QHBoxLayout()
        self.footer_lbl = QLabel("Diberdayakan oleh Guardian daemon")
        self.footer_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        close_btn = ActionButton("Tutup", primary=False)
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.close)
        footer.addWidget(self.footer_lbl)
        footer.addStretch()
        footer.addWidget(close_btn)
        root.addLayout(footer)

        self._update_panel()

    # ── Logic ────────────────────────────────────────────────────────────────

    def _load_hw_state(self) -> dict:
        if HW_STATE_PATH.exists():
            try:
                return json.loads(HW_STATE_PATH.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        # dev fallback
        return FALLBACK_HW_STATE.copy()

    def _update_panel(self):
        vendor   = self.state.get("gpu_vendor", "unknown")
        driver   = self.state.get("driver", "unknown")
        llvmpipe = self.state.get("using_llvmpipe", False)

        if llvmpipe:
            self.stack.setCurrentIndex(1)
        elif vendor == "nvidia" and driver in ("nouveau", "unknown"):
            self.stack.setCurrentIndex(2)
        else:
            self.stack.setCurrentIndex(0)

    def _refresh(self):
        self.state = self._load_hw_state()
        # Rebuild GPU card
        old_card = self.gpu_card
        self.gpu_card = GPUInfoCard(self.state)
        layout = self.centralWidget().layout()
        layout.replaceWidget(old_card, self.gpu_card)
        old_card.deleteLater()
        self._update_panel()
        self.footer_lbl.setText("Hardware di-refresh ✅")
        QTimer.singleShot(3000, lambda: self.footer_lbl.setText("Diberdayakan oleh Guardian daemon"))

    def _start_install(self, vendor: str, action: str):
        self.stack.setCurrentIndex(3)
        self.worker = DriverInstallWorker(vendor, action)
        self.worker.progress.connect(self.panel_progress.update_status)
        self.worker.finished.connect(self._on_install_done)
        self.worker.start()

    def _on_install_done(self, success: bool, message: str):
        if success:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Selesai")
            dlg.setText(f"✅  {message}")
            dlg.setIcon(QMessageBox.Icon.Information)
            if "Restart" in message or "restart" in message:
                dlg.setStandardButtons(
                    QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Reset
                )
                dlg.button(QMessageBox.StandardButton.Reset).setText("Restart Sekarang")
                if dlg.exec() == QMessageBox.StandardButton.Reset:
                    subprocess.run(["systemctl", "reboot"])
            else:
                dlg.exec()
        else:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Gagal")
            dlg.setText(f"❌  Instalasi gagal:\n\n{message}")
            dlg.setIcon(QMessageBox.Icon.Critical)
            dlg.exec()

        self._refresh()


# ── Entry point ───────────────────────────────────────────────────────────────

def launch_driver_manager():
    """
    Dipanggil dari notification_dispatcher.py atau system tray.
    Bisa juga langsung: python driver_manager_ui.py
    """
    app = QApplication.instance() or QApplication(sys.argv)
    win = DriverManagerWindow()
    win.show()
    if not QApplication.instance():
        sys.exit(app.exec())
    return win


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DriverManagerWindow()
    win.show()
    sys.exit(app.exec())
