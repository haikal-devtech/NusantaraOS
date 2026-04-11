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
Boot gagal 2x berturut-turut? Sistem auto-rollback ke snapshot Btrfs terakhir yang berjalan normal. Implementasi aktual: cari block device → mount raw Btrfs → rename `@` rusak → buat `@` baru dari snapshot → reboot. `@home` tidak pernah disentuh.

### 🔧 Hardware Watchdog & GPU Automation
Setiap boot, `nusantara-hw-detect.service` mendeteksi GPU dan memuat driver sebelum display manager jalan. Kalau driver gagal → fallback ke llvmpipe, desktop tetap muncul.

### 🤖 System Guardian Daemon
Daemon utama (`nusantara-guardian.service`): boot sequence, health check tiap 5 menit, notifikasi Bahasa Indonesia, Unix socket IPC.

### 💚 Sehat Check
Monitor kesehatan sistem realtime — disk, RAM, GPU, layanan, S.M.A.R.T. Auto-refresh 5 detik. Data real dari hardware.

### 📸 Btrfs Snapshots
Snapshot via Snapper + manual btrfs. Dipakai Zero-Panic Boot untuk rollback. `@home` selalu aman.

### 🌏 Lokalisasi Indonesia Penuh
Semua string via `localization/messages.json` + `i18n.py`. Ubah teks tanpa edit kode Python.

---

## Status Development (Per 11 April 2026)

### ✅ Backend — Selesai
| Komponen | File | Keterangan |
|---|---|---|
| Guardian Daemon | `guardian/main.py` | Daemon utama + IPC socket server |
| Config Terpusat | `guardian/config.py` | Singleton, baca `/etc/nusantara/guardian.conf` |
| Boot Watcher | `guardian/boot_watcher.py` | Zero-Panic Boot aktual — Btrfs swap-root implemented |
| Hardware Watcher | `guardian/hardware_watcher.py` | GPU detection, hw-state.json |
| Health Monitor | `guardian/health_monitor.py` | Disk, RAM, GPU, layanan, S.M.A.R.T |
| S.M.A.R.T Monitor | `guardian/smart_monitor.py` | Reallocated sectors, pending, NVMe errors |
| Notification Dispatcher | `guardian/notification_dispatcher.py` | Notif Bahasa Indonesia + gdbus |
| i18n | `guardian/i18n.py` | Lokalisasi via messages.json |
| GPU Detection Script | `gpu-automation/hw-detect.sh` | Jalan via systemd sebelum display manager |

### ✅ Systemd Services — Aktif di Hardware Nyata
| Service | Keterangan |
|---|---|
| `nusantara-guardian.service` | Guardian daemon, enabled, auto-restart |
| `nusantara-hw-detect.service` | GPU detect, Before=display-manager |
| `nusantara-tray.desktop` | KDE autostart — system tray |
| `nusantara-welcome.desktop` | KDE autostart — welcome screen |

### ✅ GUI — Selesai
| Komponen | File | Keterangan |
|---|---|---|
| Sehat Check | `guardian/sehat_check_ui.py` | PyQt6, data real, auto-refresh 5 detik |
| Driver Manager | `guardian/driver_manager_ui.py` | One-click GPU driver fix |
| System Tray | `guardian/tray_icon.py` | Status color: hijau/kuning/merah |
| Welcome Screen | `guardian/welcome_screen.py` | Onboarding + shortcut semua fitur |

### ✅ Desktop & Theming
| Komponen | Keterangan |
|---|---|
| KDE Plasma 6 Wayland | Aktif di hardware nyata |
| Floating dock | Bottom panel, Papirus Dark icons |
| 5 color schemes | Arang Nusantara, Rimba Kalimantan, Samudra Hindia, Merapi, Senja Raja Ampat |
| .desktop files | Semua GUI Nusantara muncul di app launcher |

### ✅ Infrastruktur
| Komponen | Keterangan |
|---|---|
| `nusantara-update` | Satu command update dari GitHub |
| `nusantara-install.sh` | Installer script v0.1 |
| Btrfs snapshots | Snapper + manual, Zero-Panic Boot ready |
| SSH + GitHub | Configured di sistem target |

### ⏳ Belum
- Calamares GUI installer
- Immutable base (root read-only)
- Gaming layer (Steam + Proton-GE)

---

## Struktur Project

```
nusantara-os/
├── guardian/
│   ├── main.py
│   ├── config.py
│   ├── boot_watcher.py
│   ├── hardware_watcher.py
│   ├── health_monitor.py
│   ├── smart_monitor.py
│   ├── notification_dispatcher.py
│   ├── i18n.py
│   ├── sehat_check_ui.py
│   ├── driver_manager_ui.py
│   ├── tray_icon.py
│   └── welcome_screen.py
├── gpu-automation/
│   └── hw-detect.sh
├── systemd/
│   ├── nusantara-guardian.service
│   ├── nusantara-hw-detect.service
│   ├── nusantara-tray.desktop
│   ├── nusantara-welcome.desktop
│   └── install.sh
├── desktop/
│   ├── nusantara-sehat-check.desktop
│   ├── nusantara-driver-manager.desktop
│   ├── nusantara-welcome.desktop
│   ├── nusantara-guardian-settings.desktop
│   ├── nusantara-guardian-log.desktop
│   └── install-desktop.sh
├── theming/
│   ├── ArangNusantara.colors
│   ├── RimbaKalimantan.colors
│   ├── SamudraHindia.colors
│   ├── Merapi.colors
│   └── SenjaRajaAmpat.colors
├── localization/
│   └── messages.json
└── installer-config/   # coming soon
```

---

## Commands

```bash
# Update dari GitHub
nusantara-update

# Guardian
sudo systemctl status nusantara-guardian
journalctl -u nusantara-guardian -f

# Snapshot
sudo snapper list
sudo snapper -c root create --description "deskripsi"
sudo btrfs subvolume snapshot / /.snapshots/nama

# GUI
python3 /usr/lib/nusantara/guardian/sehat_check_ui.py
python3 /usr/lib/nusantara/guardian/driver_manager_ui.py
python3 /usr/lib/nusantara/guardian/welcome_screen.py --force
```

## Lokasi File Penting

| File | Keterangan |
|---|---|
| `/etc/nusantara/guardian.conf` | Config utama |
| `/var/lib/nusantara/health-state.json` | Hasil health check terbaru |
| `/var/lib/nusantara/hw-state.json` | Status GPU terbaru |
| `/var/log/nusantara/guardian.log` | Log daemon |
| `/var/log/nusantara/recovery.log` | Log rollback/recovery |
| `/run/nusantara/guardian.sock` | Unix socket IPC |
| `/.snapshots/` | Btrfs snapshots untuk Zero-Panic Boot |

---

## Roadmap

| Versi | Codename | Status | Fokus |
|---|---|---|---|
| v0.1 Alpha | Halmahera | 🔄 In progress | Guardian, GUI, theming, Zero-Panic Boot |
| v0.5 Beta | Lombok | ⏳ Planned | Calamares installer, immutable base |
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
| 07 Apr 2026 | Sehat Check + Driver Manager GUI selesai |
| 07 Apr 2026 | Backend PRD v1.0 Sprint: config.py, IPC socket, S.M.A.R.T, i18n |
| 09 Apr 2026 | **NusantaraOS BOOT di hardware nyata** — i3 Gen 4, HDD 465GB, Intel i915 ✅ |
| 09 Apr 2026 | Guardian daemon active (running) di sistem nyata |
| 09 Apr 2026 | SSH + GitHub + nusantara-update workflow jalan |
| 09 Apr 2026 | Welcome Screen GUI + system tray icon |
| 11 Apr 2026 | Fix fstab duplikat — boot error hilang |
| 11 Apr 2026 | hw-detect.sh aktif — Intel i915 terdeteksi |
| 11 Apr 2026 | **Zero-Panic Boot — Btrfs rollback aktual implemented** |
| 11 Apr 2026 | Snapper configured + Btrfs snapshots dibuat |
| 11 Apr 2026 | 5 KDE color schemes Indonesia-inspired |
| 11 Apr 2026 | .desktop files semua GUI — muncul di app launcher |
| 11 Apr 2026 | Floating dock + Papirus Dark + wallpaper Jakarta Pusat |

---

<div align="center">

**Dibuat dengan ❤️ di Indonesia**

*Nusantara OS — Dari kepulauan, untuk semua.*

</div>
