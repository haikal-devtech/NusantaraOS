# NusantaraOS 🇮🇩

> "Dari kepulauan, untuk semua."

Indonesia's first Linux distribution — automated, gaming-ready, and fully localized in Bahasa Indonesia.

![Status](https://img.shields.io/badge/status-active%20development-green)
![Phase](https://img.shields.io/badge/phase-1%20%E2%80%94%20Base%20Setup-blue)
![Platform](https://img.shields.io/badge/platform-x86__64-lightgrey)

---

## Tentang NusantaraOS

NusantaraOS adalah distro Linux pertama Indonesia yang dirancang untuk semua orang — dari pelajar, ibu rumah tangga, wirausahawan, sampai developer. Sistem yang proaktif, otomatis, dan berbicara Bahasa Indonesia.

---

## Fitur Utama (Planned)

- 🛡️ **System Guardian** — daemon yang jaga sistem tetap sehat otomatis
- 🔧 **Zero-Panic Boot** — auto-rollback kalau sistem gagal boot
- 🎮 **Gaming Layer** — Steam, Proton-GE, MangoHud out of the box
- 🖥️ **GPU Automation** — deteksi dan load driver otomatis
- 🇮🇩 **Full Indonesian** — 95%+ UI dalam Bahasa Indonesia
- ❤️ **Sehat Check** — monitor kesehatan sistem dalam bahasa manusia

---

## Progress

| Phase | Status | Keterangan |
|-------|--------|------------|
| Phase 1 — Base Setup & Btrfs | 🔄 In Progress | Active development |
| Phase 2 — Wayland + KDE Plasma | ⏳ Planned | |
| Phase 3 — Guardian Daemon + Sehat Check | ⏳ Planned | |
| Phase 4 — Gaming Layer | ⏳ Planned | |
| Phase 5 — Calamares + Zero-Panic Boot | ⏳ Planned | |
| Phase 6 — v1.0 Public Release (Jawa) | ⏳ Planned | |

---

## Dev Log

### 06 April 2026 — Hari Pertama 🔥
- Setup repo dan file structure
- Guardian daemon skeleton hidup pertama kali
- Hardware Watcher berhasil deteksi GPU Intel
- Fix bug pertama: Intel terdeteksi sebagai AMD karena string 'ATI' ada di kata 'integrATId'
- Commit pertama masuk ke GitHub

---

## Tech Stack

- **Base**: Arch Linux → LFS (v2.0)
- **Desktop**: KDE Plasma 6
- **Filesystem**: Btrfs dengan subvolumes
- **Guardian**: Python 3
- **Installer**: Calamares
- **Audio**: PipeWire
- **Display**: Wayland + XWayland

---

## Author

**haikal-devtech** — solo developer, first time builder, full ambition. 🇮🇩

---

*Dibangun dengan ☕ dan semangat dari kepulauan.*

