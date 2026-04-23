# Nusantara OS — Product Requirements Document

> **"Dari kepulauan, untuk semua."**

| | |
|---|---|
| **Version** | v1.0 — Initial Release |
| **Status** | Draft |
| **Date** | April 06, 2026 |
| **Author** | Haikal (prod.byhk) |
| **Project** | Nusantara OS — Indonesian Linux Distribution |
| **Host** | Arch Linux (LFS-based build) |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Background & Problem Statement](#2-background--problem-statement)
3. [Target Users](#3-target-users)
4. [Product Goals & Success Metrics](#4-product-goals--success-metrics)
5. [Feature Requirements](#5-feature-requirements)
6. [Non-Functional Requirements](#6-non-functional-requirements)
7. [System Architecture](#7-system-architecture)
8. [Technical Stack](#8-technical-stack)
9. [Out of Scope (v1.0)](#9-out-of-scope--v10)
10. [Release Roadmap](#10-release-roadmap)
11. [Risks & Mitigations](#11-risks--mitigations)

---

## 1. Executive Summary

Nusantara OS is an Indonesian-first Linux distribution built from Linux From Scratch (LFS) on an Arch Linux host. Its core mission is to deliver a fully automated, reliable, and gaming-capable operating system that any Indonesian — young or old, technical or not — can install and use without ever opening a terminal.

Unlike existing "easy" distributions that are passive (they react when users ask), Nusantara OS is **proactive**: the system detects problems, fixes them automatically, communicates with users in plain Bahasa Indonesia, and never leaves users stranded on a black screen.

> **Core Differentiator:** Nusantara OS is the first Indonesian Linux distribution with a fully automated recovery and hardware detection system, GPU fallback on failure, a health monitor in Bahasa Indonesia, and a dedicated gaming layer — all built from source via LFS for maximum control and transparency.

---

## 2. Background & Problem Statement

Indonesia has over 270 million people and a rapidly growing tech-literate population. Despite this, no Linux distribution exists that is purpose-built for Indonesian users with genuine localization, cultural identity, and hardware automation for the kinds of machines Indonesians commonly use.

Current solutions fail Indonesian users in the following ways:

| Problem | Current State | Impact |
|---|---|---|
| Language barrier | Most distros default to English with partial Indonesian translation | Excludes non-technical users and older generations |
| Hardware failures | GPU driver changes or swaps often result in black screens with no recovery | Users brick systems, switch back to Windows |
| Complex recovery | Rollback requires CLI knowledge (e.g. Timeshift + terminal) | Non-technical users cannot self-recover |
| No local identity | No distro reflects Indonesian cultural identity and language | Zero adoption by non-developer users |
| Gaming fragility | System updates can break Wine/Proton/DXVK compatibility | Gamers avoid Linux entirely |
| Passive UX | Systems wait for users to identify and fix problems | Users feel unsupported and confused |

---

## 3. Target Users

### 3.1 User Personas

**Pelajar & Mahasiswa** — Age: 15–25 — Primary uses: Gaming, tugas, browsing

Budget PC/laptop, sering ganti part GPU/RAM. Wants Linux yang bisa main game tanpa ribet.

**Pengguna Rumahan** — Age: 30–55 — Primary uses: Browsing, office, streaming

Literasi digital rendah-menengah. Butuh sistem yang "just works," error dalam Bahasa Indonesia.

**Wirausahawan Kecil** — Age: 25–45 — Primary uses: Akuntansi, office, komunikasi

Mau keluar dari Windows tapi takut sistem crash dan kehilangan data pekerjaan.

**Developer Lokal** — Age: 20–35 — Primary uses: Coding, dev tools, server

Butuh base yang bersih, kontrol penuh, dan terminal yang powerful di bawah UI-friendly.

### 3.2 User Journey

The target user journey requires **zero CLI interaction** from installation to daily use. A successful user should be able to:

```
Boot a live USB → Install via GUI → Use the system daily →
Survive hardware changes and update failures → Never need to open a terminal
```

---

## 4. Product Goals & Success Metrics

| Goal | Metric | Target (v1.0) |
|---|---|---|
| Zero terminal requirement | Tasks completable via GUI only | 100% of common user tasks |
| Automated hardware recovery | System boots after GPU driver failure | Fallback to llvmpipe in < 30s |
| Zero-Panic Boot | Auto-rollback after repeated boot failure | Trigger within 2 failed boots |
| Gaming compatibility | Steam + Proton games run out of box | > 80% of Steam catalog |
| Indonesian language coverage | % of UI translated | > 95% UI coverage |
| Installation success rate | Calamares installs completing without error | > 98% on target hardware |
| Time to desktop | Seconds from login screen to usable desktop | < 8s on mid-range hardware |

---

## 5. Feature Requirements

### 5.1 Zero-Panic Boot — Automated Recovery System

**Priority: MUST HAVE**

When a system update or configuration change causes repeated boot failures, Nusantara OS automatically detects the failure pattern and rolls back to the last known-good Btrfs snapshot without any user intervention. The user is notified in Bahasa Indonesia after recovery.

- Detect boot failure if system fails to reach login screen 2 consecutive times
- Maintain a boot counter via systemd-boot that resets on clean shutdown
- On trigger: auto-mount last good Btrfs `@snapshot` and boot from it
- On successful recovery boot: display notification *"Sistem sempat bermasalah, sudah dipulihkan otomatis"*
- Home directory (`@home` subvolume) must NOT be rolled back — only root (`@`)
- Log all recovery events to `/var/log/nusantara/recovery.log`
- Expose recovery history in GUI — no terminal needed

### 5.2 Hardware Watchdog & GPU Automation

**Priority: MUST HAVE**

On every boot, the system detects the current GPU vendor and loads the appropriate driver stack. If the driver fails to initialize, the system automatically falls back to software rendering (llvmpipe) so the user always reaches the desktop. A one-click repair flow is provided from within the desktop.

- Run `hw-detect` service before display manager starts (systemd ordering: `After=basic.target`)
- Detect GPU via `lspci` — handle AMD (amdgpu/radv), Intel (iris/xe), NVIDIA (nouveau + proprietary)
- If primary driver fails: auto-load llvmpipe fallback within 30 seconds
- On llvmpipe fallback: show desktop notification with *"Perbaiki Driver"* action button
- NVIDIA proprietary installer must be one-click GUI — no manual `.run` execution
- DKMS must be installed and configured for automatic driver rebuild on kernel update
- Hardware change detection: if GPU vendor changes between boots, auto-trigger driver setup wizard

### 5.3 System Guardian Daemon

**Priority: MUST HAVE**

The core automation engine of Nusantara OS. A persistent background service that monitors system health, coordinates automated responses, and dispatches all user-facing notifications. All features in sections 5.1, 5.2, and 5.4 run through this daemon.

- Single Python/Rust daemon running as a systemd service (`nusantara-guardian.service`)
- Modules: BootWatcher, HardwareWatcher, HealthMonitor, NotificationDispatcher
- All notifications routed through NotificationDispatcher — consistent Bahasa Indonesia tone
- Action buttons on all notifications — no notification should be dead-end
- Daemon must consume < 50MB RAM and < 1% CPU in idle state
- Configurable via `/etc/nusantara/guardian.conf` (GUI editor available)
- Comprehensive logging to journald + `/var/log/nusantara/`
- Auto-restart on crash via systemd `RestartSec=5`

### 5.4 Sehat Check — Bahasa Indonesia Health Monitor

**Priority: MUST HAVE**

A proactive system health monitor that translates technical errors into plain, actionable Bahasa Indonesia. Nusantara OS is the first Linux distribution with a health monitor designed for non-technical Indonesian users.

- Monitor disk health via S.M.A.R.T — alert in plain Indonesian when degradation detected
- Monitor GPU temperature — notify and throttle at configurable thresholds
- Monitor RAM usage — identify top memory consumers, suggest action
- Monitor failed systemd units — surface as *"ada layanan yang bermasalah"* with fix button
- Monitor disk space — alert before partition fills (warn at 85%, critical at 95%)
- All messages must use everyday Bahasa Indonesia — zero jargon, zero error codes shown to user
- Each alert must have at minimum one action button (fix, ignore, learn more)
- Sehat Check panel accessible from system tray — shows color-coded health summary

### 5.5 Gaming Layer — Isolated & Resilient

**Priority: MUST HAVE**

Gaming dependencies (Wine, Proton, DXVK, MangoHud, GameMode) live in a dedicated Btrfs subvolume (`@gaming`) that is versioned independently from the OS. System updates cannot break game compatibility. Gaming layer updates can be rolled back without affecting the OS.

- Gaming stack installed to `@gaming` Btrfs subvolume, mounted at `/opt/gaming`
- Steam installed via Flatpak — sandboxed, self-updating, no library conflicts
- Proton-GE included by default for maximum game compatibility
- MangoHud and GameMode pre-configured — activated per-game or globally
- GameMode: set CPU governor to performance during active gaming sessions
- Gaming layer has independent snapshot + rollback from OS layer
- GPU memory and temperature monitoring during gaming (surfaced via MangoHud)
- One-click game compatibility report: checks if a Steam game is Linux-compatible
- Controller support: auto-detect and configure Xbox, PlayStation, generic HID controllers

### 5.6 Indonesian Localization — Full Coverage

**Priority: MUST HAVE**

Nusantara OS ships with complete Indonesian language support as the default, covering UI, documentation, notifications, installer, and input methods. Regional timezone options are pre-configured for WIB/WITA/WIT.

- Default locale: `id_ID.UTF-8`
- Default timezone: `Asia/Jakarta` (WIB) — selectable WIB/WITA/WIT during install
- Keyboard: US QWERTY (standard for Indonesian keyboards)
- Font: Noto Sans + Noto Serif (full Latin + regional character coverage)
- All Guardian daemon notifications in Bahasa Indonesia (formal but not stiff)
- Calamares installer fully translated — zero English prompts in install flow
- IBus or Fcitx5 pre-installed for regional language input (Javanese script etc.)
- > 95% KDE Plasma UI translated to Indonesian via existing KDE translation project
- Error messages: map common kernel/system errors to plain Indonesian descriptions

### 5.7 Immutable Base + Layered Package System

**Priority: SHOULD HAVE**

The core OS layer is mounted read-only to prevent accidental corruption. User applications install as Flatpak (sandboxed, cannot damage the base). System packages are managed in a curated layer with atomic updates.

- Root filesystem mounted read-only (remount RO after boot)
- System updates are atomic: prepare new root → verify → swap → reboot
- Flatpak as the primary application delivery mechanism for user apps
- Flathub pre-configured as default Flatpak remote
- Gaming stack and system packages in separate managed layers
- Factory reset option: restores base system in < 60 seconds (home preserved)
- No AUR by default in v1.0 — curated repository only for stability
- Package manager GUI available — no terminal required for updates/installs

### 5.8 Calamares GUI Installer

**Priority: MUST HAVE**

Nusantara OS ships with Calamares as the graphical installer. The entire installation flow must be completable without any terminal or CLI interaction. Target installation time is under 20 minutes on mid-range hardware.

- Full Indonesian localization of all Calamares prompts and labels
- Partitioning: auto-partition (recommended) and manual mode available
- Btrfs with subvolumes (`@`, `@home`, `@snapshots`, `@gaming`) as default partition scheme
- GPU detection during install — pre-configure appropriate driver stack before first boot
- Network connectivity check — offer to install updates during setup
- WIB/WITA/WIT timezone selector with map interface
- User creation with strong password enforcement (visual indicator)
- Post-install summary: list what was installed and what to do next
- UEFI and legacy BIOS boot support

---

## 6. Non-Functional Requirements

| Category | Requirement | Target |
|---|---|---|
| Performance | Boot to desktop time | < 8 seconds (mid-range SSD) |
| Performance | RAM usage at idle desktop | < 600 MB (KDE Plasma) |
| Performance | Guardian daemon CPU at idle | < 1% |
| Reliability | System uptime target | 99.5% (excluding planned updates) |
| Reliability | Rollback success rate | > 99% on supported hardware |
| Compatibility | GPU vendors supported | AMD, Intel, NVIDIA (open + proprietary) |
| Compatibility | UEFI + Legacy BIOS | Both required |
| Security | Default firewall | UFW enabled, sensible defaults |
| Security | Automatic security updates | Critical CVEs auto-applied |
| Usability | Tasks without terminal | 100% of common user tasks |
| Usability | First-boot setup time | < 5 minutes to usable desktop |
| Localization | Indonesian UI coverage | > 95% |
| Maintainability | Kernel update → driver rebuild | Automatic via DKMS |

---

## 7. System Architecture

Nusantara OS uses a layered architecture with clear separation between the immutable base, managed system layer, gaming layer, and user application layer.

| Layer | Description |
|---|---|
| **User Layer (Flatpak)** | Sandboxed user applications via Flathub. Cannot modify lower layers. |
| **Gaming Layer (@gaming)** | Steam, Proton-GE, Wine, DXVK, MangoHud. Independent Btrfs subvolume with own snapshots. |
| **Managed System Layer** | Desktop environment (KDE Plasma), Guardian daemon, Sehat Check, Indonesian localization, display server (Wayland + XWayland), audio (PipeWire), networking (NetworkManager). |
| **Immutable Base (Read-Only)** | LFS core: Linux 6.8+ kernel, glibc, systemd, core utils, bootloader. Mounted RO at runtime. Updated atomically. |

### Btrfs Subvolume Layout

| Subvolume | Mount Point | Purpose | Rollback? |
|---|---|---|---|
| `@` | `/` | OS root — immutable at runtime | Yes — Zero-Panic Boot |
| `@home` | `/home` | User data and configs | No — always preserved |
| `@snapshots` | `/.snapshots` | Snapshot storage | N/A |
| `@gaming` | `/opt/gaming` | Gaming stack | Yes — independent |
| `@boot` | `/boot` | Kernel + bootloader | Manual only |

---

## 8. Technical Stack

| Component | Technology | Notes |
|---|---|---|
| Build base | LFS (Linux From Scratch) | Host: Arch Linux |
| Kernel | Linux 6.8+ | AMD RDNA, Intel Arc, NVIDIA open module support |
| Init system | systemd | Required for hardware automation and journald |
| C library | glibc | Required for Steam + gaming binaries |
| Display server | Wayland + XWayland | XWayland for legacy game compatibility |
| Compositor | KWin (KDE) | Gaming performance + familiar Windows-like layout |
| Desktop environment | KDE Plasma 6 | Highest Indonesian translation coverage |
| Audio | PipeWire | Replaces PulseAudio + JACK, low-latency gaming audio |
| Networking | NetworkManager | GUI-friendly, works out of box |
| GPU (AMD/Intel) | Mesa (radv, iris, radeonsi) | Open source, included in base |
| GPU (NVIDIA) | Nouveau (default) + proprietary installer | DKMS for auto-rebuild |
| Guardian daemon | Python (primary) or Rust | Runs as systemd service |
| Notifications | libnotify + custom GTK dialog | Action buttons required |
| Package manager | pacman (ported from Arch) | Familiar, AUR-ready for future |
| User apps | Flatpak + Flathub | Sandboxed, base-safe |
| Gaming | Steam (Flatpak) + Proton-GE + MangoHud + GameMode | |
| Filesystem | Btrfs (default) + ext4 (option) | Btrfs required for snapshots |
| Installer | Calamares | Industry standard, Qt6-based, fully translatable |
| Bootloader | systemd-boot | UEFI-first, supports boot counter for Zero-Panic |
| Fonts | Noto Sans + Noto Serif + JetBrains Mono | Full Indonesian glyph support |
| Input method | IBus / Fcitx5 | Regional script support |

---

## 9. Out of Scope — v1.0

- AUR (Arch User Repository) support — v2.0 candidate
- ARM/mobile device support — x86_64 only in v1.0
- Cloud/server edition — desktop-only focus
- Custom kernel patches beyond upstream LTS
- Aksara daerah (Javanese, Balinese script) input — IBus infrastructure prepared, content v2.0
- Automated online backup — Sehat Check will surface backup reminders, actual backup service is v2.0
- Nusantara App Store (custom Flatpak frontend) — v1.1
- OTA (over-the-air) system image updates — v2.0

---

## 10. Release Roadmap

| Phase | Release | Codename | Timeline | Key Deliverables |
|---|---|---|---|---|
| Phase 1 | v0.1 Alpha | Halmahera | Month 1–2 | LFS base build, kernel, toolchain, systemd, basic boot |
| Phase 2 | v0.2 Alpha | Flores | Month 2–3 | BLFS: Wayland, PipeWire, NetworkManager, KDE Plasma |
| Phase 3 | v0.5 Beta | Lombok | Month 3–4 | Guardian daemon, Sehat Check, Indonesian locale, GPU auto-detection |
| Phase 4 | v0.8 Beta | Bali | Month 4–5 | Gaming layer, Steam, Proton-GE, MangoHud, NVIDIA installer |
| Phase 5 | v0.9 RC | Sulawesi | Month 5–6 | Calamares installer, Zero-Panic Boot, immutable base, full QA |
| Phase 6 | v1.0 Stable | Jawa | Month 6+ | Public release, ISO, documentation, community launch |
| Phase 7 | v1.1 | Bali Gaming Edition | Month 8+ | Gaming-focused ISO, Nusantara App Store, optimization |
| Phase 8 | v2.0 LTS | Sumatra | Month 12+ | AUR support, OTA updates, ARM exploration, enterprise features |

---

## 11. Risks & Mitigations

| Risk | Severity | Probability | Mitigation |
|---|---|---|---|
| NVIDIA driver breaks on kernel update | High | High | DKMS mandatory from day 1. GPU fallback to llvmpipe ensures desktop always boots. |
| LFS build time underestimated | Medium | High | Maintain a stage archive at each milestone. Use ccache to speed rebuilds. |
| Calamares fails on uncommon hardware | High | Medium | Extensive hardware matrix testing. Fallback to guided manual install doc. |
| Guardian daemon memory leak over time | Medium | Medium | Implement daemon watchdog (systemd RestartSec). Memory profiling in beta. |
| Indonesian translation incomplete at launch | Medium | Medium | Fallback to English for untranslated strings. Community translation sprint before v1.0. |
| Btrfs corruption during power loss | High | Low | Enable Btrfs CoW and checksums. Document backup strategy clearly. |
| Solo maintainer bottleneck | High | High | Modular architecture so contributors can own individual components. Prioritize documentation. |
| Steam Flatpak breaking changes | Low | Low | Pin Flatpak runtime version in gaming layer. Test on Proton-GE updates. |

---

*Nusantara OS PRD v1.0 — Generated April 06, 2026 — Internal document. All decisions subject to revision as build progresses.*

*Dibuat dengan ❤️ di Indonesia — Dari kepulauan, untuk semua.*
