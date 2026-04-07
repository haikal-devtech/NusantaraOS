# 🇮🇩 Nusantara OS

> **"Dari kepulauan, untuk semua."**

Nusantara OS adalah distribusi Linux pertama Indonesia — dibangun untuk semua orang Indonesia, muda maupun tua, tanpa perlu buka terminal seumur hidup.

![Status](https://img.shields.io/badge/status-active%20development-brightgreen)
![Base](https://img.shields.io/badge/base-Arch%20Linux-1793D1)
![Desktop](https://img.shields.io/badge/desktop-KDE%20Plasma%206-blue)
![Language](https://img.shields.io/badge/language-Bahasa%20Indonesia-red)
![License](https://img.shields.io/badge/license-GPL--3.0-orange)

---

## Apa Itu Nusantara OS?

Distro Linux yang **proaktif** — bukan pasif. Sistem mendeteksi masalah, memperbaikinya sendiri, dan berkomunikasi dalam Bahasa Indonesia yang mudah dimengerti. User tidak perlu tahu apa itu terminal, driver, atau partisi.

### Kenapa Beda?

| Distro Biasa | Nusantara OS |
|---|---|
| Bereaksi kalau user minta | Deteksi masalah sebelum user sadar |
| Error dalam bahasa Inggris teknis | Notifikasi dalam Bahasa Indonesia biasa |
| Black screen kalau driver GPU gagal | Auto-fallback, desktop tetap muncul |
| Rollback butuh CLI | Auto-rollback tanpa user lakuin apapun |
| Gaming bisa rusak setelah update | Gaming layer terpisah, update OS aman |

---

## Fitur Utama

### 🛡️ Zero-Panic Boot
Boot gagal 2x berturut-turut? Sistem auto-rollback ke snapshot terakhir yang berjalan normal — tanpa user intervensi, tanpa CLI. User cukup nyalakan laptop.

### 🔧 Hardware Watchdog & GPU Automation
Setiap boot, sistem mendeteksi GPU dan memuat driver yang tepat. Kalau driver gagal, sistem otomatis fallback ke software rendering (llvmpipe) — desktop tetap muncul, tidak pernah black screen.

### 🤖 System Guardian Daemon
Daemon utama yang berjalan di background, mengkoordinasikan semua automation: boot recovery, hardware detection, health monitoring, dan notifikasi.

### 💚 Sehat Check
Monitor kesehatan sistem dalam Bahasa Indonesia biasa — bukan error code. RAM, penyimpanan, GPU, layanan sistem — semuanya terpantau real-time dengan notifikasi yang bisa dimengerti siapa saja.

### 🎮 Gaming Layer
Stack gaming (Steam, Proton, Wine, MangoHud) di subvolume Btrfs terpisah. Update OS tidak bisa merusak kompatibilitas game.

### 🗺️ Lokalisasi Indonesia Penuh
- Default locale: `id_ID.UTF-8`
- Timezone: WIB/WITA/WIT (pilihan saat install)
- Semua notifikasi dalam Bahasa Indonesia
- Font Noto (cover semua karakter Indonesia)

---

## Status Development

### ✅ Selesai
| Komponen | File | Keterangan |
|---|---|---|
| Guardian Daemon | `guardian/main.py` | Loop utama + orchestration |
| Boot Watcher | `guardian/boot_watcher.py` | Zero-Panic Boot logic |
| Hardware Watcher | `guardian/hardware_watcher.py` | GPU & hardware detection |
| Health Monitor | `guardian/health_monitor.py` | Cek disk, RAM, layanan — real data |
| Notification Dispatcher | `guardian/notification_dispatcher.py` | Semua notif Bahasa Indonesia |
| Sehat Check GUI | `guardian/sehat_check_ui.py` | PyQt6, brand Nusantara, auto-refresh 5 detik |
| Driver Manager GUI | `guardian/driver_manager_ui.py` | One-click GPU driver fix |
| System Tray Icon | `guardian/tray_icon.py` | Status color: hijau/kuning/merah |
| GPU Detection Script | `gpu-automation/hw-detect.sh` | Auto-load driver sebelum display manager |
| Lokalisasi | `localization/messages.json` | Semua pesan Bahasa Indonesia |
| Systemd Services | — | `nusantara-guardian` + `nusantara-hw-detect` aktif |

### ⏳ Belum
- Welcome Screen GUI
- Calamares installer config
- Btrfs subvolume setup
- Gaming layer
- System tray icon integration ke main daemon

---

## Struktur Project

```
nusantara-os/
├── guardian/
│   ├── main.py                     # Daemon utama
│   ├── boot_watcher.py             # Zero-Panic Boot
│   ├── hardware_watcher.py         # Hardware & GPU detection
│   ├── health_monitor.py           # Health monitoring (real data)
│   ├── notification_dispatcher.py  # Notifikasi Bahasa Indonesia
│   ├── sehat_check_ui.py           # Sehat Check GUI (PyQt6)
│   ├── driver_manager_ui.py        # Driver Manager GUI (PyQt6)
│   └── tray_icon.py                # System tray icon
├── gpu-automation/
│   └── hw-detect.sh                # GPU detection & driver loading
├── localization/
│   └── messages.json               # Bahasa Indonesia strings
├── installer-config/
│   └── calamares/                  # (coming soon)
└── docs/
```

---

## Tech Stack

| Layer | Pilihan |
|---|---|
| Base | Arch Linux (→ LFS di v2.0) |
| Kernel | Linux 6.8+ |
| Init | systemd |
| Desktop | KDE Plasma 6 |
| Display | Wayland + XWayland |
| Audio | PipeWire |
| Filesystem | Btrfs |
| GUI Framework | PyQt6 |
| Automation | Python 3 (Guardian daemon) |
| Apps | Flatpak + Flathub |
| Installer | Calamares (coming soon) |

---

## Cara Jalankan (Development)

### Requirements
```bash
sudo pacman -S python-pyqt6
```

### Setup data directory
```bash
sudo mkdir -p /var/lib/nusantara
sudo chown -R $USER:$USER /var/lib/nusantara
```

### Jalankan Guardian daemon
```bash
cd guardian
sudo python main.py
```

### Jalankan Sehat Check GUI
```bash
python guardian/sehat_check_ui.py
```

### Jalankan Driver Manager GUI
```bash
python guardian/driver_manager_ui.py
```

### Jalankan System Tray
```bash
python guardian/tray_icon.py &
```

### Setup autostart tray (KDE)
```bash
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/nusantara-tray.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=NusantaraOS Guardian Tray
Exec=python /home/$USER/nusantara-os/guardian/tray_icon.py
Icon=computer
Hidden=false
X-GNOME-Autostart-enabled=true
EOF
```

---

## Systemd Services

```bash
# Install dan enable services
sudo systemctl enable --now nusantara-guardian.service
sudo systemctl enable --now nusantara-hw-detect.service

# Cek status
sudo systemctl status nusantara-guardian.service
```

---

## Roadmap

| Versi | Codename | Status | Fokus |
|---|---|---|---|
| v0.1 Alpha | Halmahera | 🔄 In progress | LFS base, Guardian daemon, Sehat Check |
| v0.5 Beta | Lombok | ⏳ Planned | Calamares installer, Btrfs subvolumes |
| v0.8 Beta | Bali | ⏳ Planned | Gaming layer, Steam, Proton-GE |
| v1.0 Stable | Jawa | ⏳ Planned | Public release, ISO, dokumentasi |
| v1.1 | Bali Gaming | ⏳ Planned | Gaming edition ISO |
| v2.0 LTS | Sumatra | ⏳ Planned | LFS base, AUR, OTA updates |

---

## Branding

- **Logo:** Motif Batik Kawung — 4 petal kardinal, titik emas di tengah
- **Warna primer:** Merah Saga `#8B1A1A` + Emas Keraton `#C5940A`
- **Font:** Noto Serif (display) · Noto Sans (UI) · JetBrains Mono (terminal)
- **Cultural DNA:** Jawa · Sumatra · Kalimantan · Sulawesi · Papua

---

## Kontribusi

Project ini masih early stage dan di-develop secara solo. Kalau lo tertarik kontribusi:

1. Fork repo ini
2. Buat branch baru (`git checkout -b feat/nama-fitur`)
3. Commit perubahan (`git commit -m "feat: deskripsi singkat"`)
4. Push dan buat Pull Request

Issues dan diskusi terbuka untuk semua.

---

## Dev Log

| Tanggal | Milestone |
|---|---|
| 06 Apr 2026 | Project init — Guardian daemon skeleton hidup |
| 06 Apr 2026 | Zero-Panic Boot, Health Monitor, Notification Dispatcher selesai |
| 06 Apr 2026 | GPU detection + systemd services aktif |
| 07 Apr 2026 | Sehat Check PyQt6 GUI selesai |
| 07 Apr 2026 | Driver Manager GUI + System Tray Icon selesai |
| 07 Apr 2026 | Sehat Check reskin ke brand Nusantara OS |
| 07 Apr 2026 | Health Monitor: real data + auto-refresh 5 detik |

---

<div align="center">

**Dibuat dengan ❤️ di Indonesia**

*Nusantara OS — Dari kepulauan, untuk semua.*

</div>
