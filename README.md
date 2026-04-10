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
Boot gagal 2x berturut-turut? Sistem auto-rollback ke snapshot Btrfs terakhir yang berjalan normal. Event dicatat ke `/var/log/nusantara/recovery.log`. User cukup nyalakan laptop.

### 🔧 Hardware Watchdog & GPU Automation
Setiap boot, `nusantara-hw-detect.service` mendeteksi GPU dan memuat driver sebelum display manager jalan. Tulis `hw-state.json` ke `/var/lib/nusantara/`. Kalau GPU diganti antar-sesi, notifikasi wizard muncul otomatis. Kalau driver gagal → fallback ke llvmpipe, desktop tetap muncul.

### 🤖 System Guardian Daemon
Daemon utama yang jalan sebagai systemd service (`nusantara-guardian.service`). Kerjanya:
- Boot sequence: cek counter → detect GPU → reset counter setelah sukses
- Loop tiap 5 menit: cek disk, RAM, layanan sistem, S.M.A.R.T
- Kirim notifikasi Bahasa Indonesia + action buttons
- **Unix socket IPC** di `/run/nusantara/guardian.sock` — GUI bisa kirim event langsung

### 🗺️ Konfigurasi Terpusat
File `/etc/nusantara/guardian.conf` mengatur semua threshold (disk, RAM, interval, max boot gagal, dll). Perubahan aktif tanpa restart daemon via event `RELOAD_CONFIG`.

### 💚 Sehat Check
Monitor kesehatan sistem realtime dalam Bahasa Indonesia — bukan error code. Disk, RAM, GPU, layanan sistem, **S.M.A.R.T disk health** — semua terpantau. Output ditulis ke `/var/lib/nusantara/health-state.json` dan dibaca GUI. Auto-refresh tiap 5 detik.

### 🌏 Lokalisasi Indonesia Penuh
Semua string UI dan notifikasi baca dari `localization/messages.json` via modul `i18n.py`. Ubah teks tanpa edit kode Python sama sekali.

---

## Status Development (Per 9 April 2026)

### ✅ Backend — Selesai
| Komponen | File | Keterangan |
|---|---|---|
| Guardian Daemon | `guardian/main.py` | Daemon utama + IPC socket server |
| Config Terpusat | `guardian/config.py` | Singleton, baca `/etc/nusantara/guardian.conf` |
| Boot Watcher | `guardian/boot_watcher.py` | Zero-Panic Boot, recovery.log, systemd-boot groundwork |
| Hardware Watcher | `guardian/hardware_watcher.py` | GPU detection, `hw-state.json`, GPU change detection |
| Health Monitor | `guardian/health_monitor.py` | Disk, RAM, GPU, layanan, S.M.A.R.T |
| S.M.A.R.T Monitor | `guardian/smart_monitor.py` | Reallocated sectors, pending, NVMe errors |
| Notification Dispatcher | `guardian/notification_dispatcher.py` | Notif Bahasa Indonesia + action buttons via gdbus |
| i18n | `guardian/i18n.py` | `t("key", var=val)` baca dari messages.json |
| IPC Socket | `guardian/main.py` | Unix socket server, handle event dari GUI |
| GPU Detection Script | `gpu-automation/hw-detect.sh` | Jalan via systemd sebelum display manager |
| Lokalisasi | `localization/messages.json` | Semua pesan Bahasa Indonesia |

### ✅ Systemd Services — Aktif di Hardware Nyata
| Service | Tipe | Keterangan |
|---|---|---|
| `nusantara-guardian.service` | simple | Guardian daemon, enabled, auto-restart |
| `nusantara-hw-detect.service` | oneshot | GPU detect, Before=display-manager |
| `nusantara-tray.desktop` | autostart | System tray icon, jalan saat login KDE |
| `nusantara-welcome.desktop` | autostart | Welcome screen, jalan saat first boot |

### ✅ GUI — Selesai
| Komponen | File | Keterangan |
|---|---|---|
| Sehat Check | `guardian/sehat_check_ui.py` | PyQt6, baca `health-state.json`, auto-refresh 5 detik, data real |
| Driver Manager | `guardian/driver_manager_ui.py` | One-click GPU driver fix |
| System Tray | `guardian/tray_icon.py` | Status color: hijau/kuning/merah, menu klik kanan |
| Welcome Screen | `guardian/welcome_screen.py` | Onboarding user baru, shortcut ke semua fitur |

### ✅ Infrastruktur — Selesai
| Komponen | Keterangan |
|---|---|
| `nusantara-update` | Satu command update dari GitHub + restart Guardian |
| `nusantara-install.sh` | Installer script v0.1 — partisi, Btrfs subvolumes, pacstrap, bootloader |
| SSH + GitHub | Configured di sistem target |

### ⏳ Belum
- Calamares GUI installer
- Zero-Panic Boot — rollback Btrfs aktual (sekarang masih stub)
- Gaming layer (Steam + Proton-GE + MangoHud)
- Immutable base (root read-only)
- KDE theming Nusantara OS
- Desktop Entry `.desktop` files untuk semua GUI

---

## Struktur Project

```
nusantara-os/
├── guardian/
│   ├── main.py                     # Daemon utama + IPC socket
│   ├── config.py                   # Konfigurasi terpusat (singleton)
│   ├── boot_watcher.py             # Zero-Panic Boot + recovery.log
│   ├── hardware_watcher.py         # GPU detection + hw-state.json
│   ├── health_monitor.py           # Health monitoring (disk/RAM/GPU/SMART)
│   ├── smart_monitor.py            # S.M.A.R.T disk health via smartctl
│   ├── notification_dispatcher.py  # Notifikasi Bahasa Indonesia + gdbus
│   ├── i18n.py                     # Internationalization via messages.json
│   ├── sehat_check_ui.py           # Sehat Check GUI (PyQt6)
│   ├── driver_manager_ui.py        # Driver Manager GUI (PyQt6)
│   ├── tray_icon.py                # System tray icon
│   └── welcome_screen.py           # Welcome screen
├── gpu-automation/
│   └── hw-detect.sh                # GPU detection & driver loading (systemd)
├── systemd/
│   ├── nusantara-guardian.service  # Guardian daemon service
│   ├── nusantara-hw-detect.service # Hardware detection service
│   ├── nusantara-tray.desktop      # KDE autostart — system tray
│   ├── nusantara-welcome.desktop   # KDE autostart — welcome screen
│   └── install.sh                  # Install script (sudo bash install.sh)
├── localization/
│   └── messages.json               # Semua string Bahasa Indonesia
├── etc/
│   └── nusantara/
│       └── guardian.conf           # Config template
└── installer-config/               # (coming soon)
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
| Notifikasi | gdbus (D-Bus) + notify-send fallback |
| Apps | Flatpak + Flathub |
| Installer | Calamares (coming soon) |

---

## Cara Install Guardian Service

```bash
cd /path/to/nusantara-os
sudo bash systemd/install.sh
```

Script ini otomatis:
- Copy semua file ke `/usr/lib/nusantara/`
- Install + enable kedua systemd service
- Set permissions direktori data

## Update dari GitHub

```bash
nusantara-update
```

Satu command — pull GitHub, copy file terbaru ke `/usr/lib/nusantara/`, restart Guardian.

## Cara Jalankan (Development — tanpa install)

```bash
# Requirements
sudo pacman -S python-pyqt6 smartmontools

# Guardian daemon
cd /path/to/nusantara-os
sudo python3 guardian/main.py

# Test IPC socket (terminal lain)
echo '{"type":"GUARDIAN_STATUS"}' | sudo socat - UNIX-CONNECT:/run/nusantara/guardian.sock
echo '{"type":"HEALTH_CHECK_NOW"}' | sudo socat - UNIX-CONNECT:/run/nusantara/guardian.sock

# Sehat Check GUI
python3 guardian/sehat_check_ui.py

# Driver Manager GUI
python3 guardian/driver_manager_ui.py

# Welcome Screen (force tampil)
python3 guardian/welcome_screen.py --force
```

## Systemd Commands

```bash
sudo systemctl start nusantara-guardian      # Jalankan sekarang
sudo systemctl status nusantara-guardian     # Cek status
sudo systemctl restart nusantara-guardian    # Restart
sudo systemctl stop nusantara-guardian       # Stop
journalctl -u nusantara-guardian -f          # Log live
journalctl -u nusantara-hw-detect            # Log hardware detection
```

## Lokasi File Penting

| File | Keterangan |
|---|---|
| `/etc/nusantara/guardian.conf` | Config utama (threshold, interval, dll) |
| `/var/lib/nusantara/health-state.json` | Hasil health check terbaru (dibaca GUI) |
| `/var/lib/nusantara/hw-state.json` | Status GPU terbaru |
| `/var/lib/nusantara/.welcome-shown` | Flag — welcome screen sudah ditampilkan |
| `/var/log/nusantara/guardian.log` | Log daemon |
| `/var/log/nusantara/recovery.log` | Log event pemulihan/rollback |
| `/run/nusantara/guardian.sock` | Unix socket IPC |

---

## Roadmap

| Versi | Codename | Status | Fokus |
|---|---|---|---|
| v0.1 Alpha | Halmahera | 🔄 In progress | Guardian daemon, GUI, systemd service, installer |
| v0.5 Beta | Lombok | ⏳ Planned | Calamares installer, Btrfs rollback aktual |
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

## Dev Log

| Tanggal | Milestone |
|---|---|
| 06 Apr 2026 | Project init — Guardian daemon skeleton hidup |
| 06 Apr 2026 | Zero-Panic Boot, Health Monitor, Notification Dispatcher selesai |
| 06 Apr 2026 | GPU detection + systemd services aktif |
| 07 Apr 2026 | Sehat Check PyQt6 GUI selesai |
| 07 Apr 2026 | Driver Manager GUI + System Tray Icon selesai |
| 07 Apr 2026 | **Backend PRD v1.0 Sprint:** config.py, GPU change detection, IPC socket Unix, S.M.A.R.T monitor, boot_watcher + recovery.log |
| 07 Apr 2026 | Notification action buttons via gdbus — semua notif punya tombol aksi |
| 07 Apr 2026 | i18n.py — lokalisasi penuh via messages.json, tidak ada hardcoded string |
| 07 Apr 2026 | systemd/install.sh — satu perintah install semua service |
| 07 Apr 2026 | Guardian aktif sebagai service: 10MB RAM, <1% CPU idle |
| 09 Apr 2026 | **NusantaraOS BOOT di hardware nyata** — i3 Gen 4, HDD 465GB, Intel i915, KDE Plasma 6 Wayland ✅ |
| 09 Apr 2026 | Guardian daemon `active (running)` di sistem nyata — health-state.json data real |
| 09 Apr 2026 | SSH + GitHub configured — `nusantara-update` jalan satu command |
| 09 Apr 2026 | Sehat Check GUI live — disk 456GB, RAM 3.7GB, Intel i915 Gen 4 terbaca real |
| 09 Apr 2026 | Bug fix: `cek_layanan()` false positive karakter `●` |
| 09 Apr 2026 | Welcome Screen GUI selesai + KDE autostart |
| 09 Apr 2026 | System tray icon + KDE autostart configured |

---

<div align="center">

**Dibuat dengan ❤️ di Indonesia**

*Nusantara OS — Dari kepulauan, untuk semua.*

</div>
