#!/usr/bin/env python3
"""
NusantaraOS — Boot Watcher
File: guardian/boot_watcher.py

Zero-Panic Boot: deteksi kalau sistem gagal boot berulang.
Kalau gagal 2x berturut-turut → auto rollback ke Btrfs snapshot.

Dua mode boot counter (sesuai config):
  1. systemd-boot (bootctl) — UEFI, lebih reliable, PRD recommendation
  2. File counter di /var/lib/nusantara/boot-counter — fallback non-UEFI

Recovery events dicatat ke /var/log/nusantara/recovery.log
"""

import logging
import os
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────────
try:
    from config import get_config
    _cfg = get_config()
    BOOT_COUNTER_FILE = _cfg.state_dir / "boot-counter"
    MAX_GAGAL         = _cfg.max_gagal
    USE_SYSTEMD_BOOT  = _cfg.use_systemd_boot
    RECOVERY_LOG      = _cfg.recovery_log
except ImportError:
    BOOT_COUNTER_FILE = Path("/var/lib/nusantara/boot-counter")
    MAX_GAGAL         = 2
    USE_SYSTEMD_BOOT  = True
    RECOVERY_LOG      = Path("/var/log/nusantara/recovery.log")

# Path Btrfs
BTRFS_ROOT_LABEL = "NusantaraOS"   # label partisi root (sesuai install script)
BTRFS_MNT_TMP   = Path("/tmp/nusantara-btrfs-root")
SNAPSHOT_DIR     = Path("/.snapshots")


# ══════════════════════════════════════════════════════════════════════════════
# RECOVERY LOG
# ══════════════════════════════════════════════════════════════════════════════

def _tulis_recovery_log(pesan: str):
    """Catat event pemulihan ke recovery.log (PRD 5.1)."""
    try:
        RECOVERY_LOG.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(RECOVERY_LOG, 'a') as f:
            f.write(f"[{timestamp}] {pesan}\n")
    except Exception as e:
        log.error(f"Gagal tulis recovery log: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEMD-BOOT COUNTER
# ══════════════════════════════════════════════════════════════════════════════

def _bootctl_tersedia() -> bool:
    try:
        result = subprocess.run(
            ['bootctl', 'is-installed'],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _baca_counter_bootctl() -> int:
    try:
        result = subprocess.run(
            ['bootctl', 'status', '--no-pager'],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.split('\n'):
            if 'tries done' in line.lower() or 'tries-done' in line.lower():
                parts = line.split(':')
                if len(parts) >= 2:
                    try:
                        return int(parts[-1].strip())
                    except ValueError:
                        pass
        return 0
    except Exception as e:
        log.debug(f"Gagal baca bootctl counter: {e}")
        return 0


# ══════════════════════════════════════════════════════════════════════════════
# FILE COUNTER
# ══════════════════════════════════════════════════════════════════════════════

def baca_counter() -> int:
    try:
        BOOT_COUNTER_FILE.parent.mkdir(parents=True, exist_ok=True)
        if BOOT_COUNTER_FILE.exists():
            angka = int(BOOT_COUNTER_FILE.read_text().strip())
            log.info(f"Counter boot gagal: {angka}x")
            return angka
        else:
            log.info("Boot pertama — counter 0")
            return 0
    except Exception as e:
        log.error(f"Gagal baca counter: {e}")
        return 0


def tulis_counter(angka: int):
    try:
        BOOT_COUNTER_FILE.parent.mkdir(parents=True, exist_ok=True)
        BOOT_COUNTER_FILE.write_text(str(angka))
        log.info(f"Counter disimpan: {angka}x")
    except Exception as e:
        log.error(f"Gagal simpan counter: {e}")


def reset_counter():
    try:
        if BOOT_COUNTER_FILE.exists():
            BOOT_COUNTER_FILE.unlink()
        log.info("Boot berhasil! Counter direset ke 0")
        _tulis_recovery_log("Boot sukses — counter direset")
    except Exception as e:
        log.error(f"Gagal reset counter: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: BTRFS
# ══════════════════════════════════════════════════════════════════════════════

def _cari_device_btrfs() -> str | None:
    """Cari block device dari partisi Btrfs root NusantaraOS."""
    try:
        # Cari via label dulu
        result = subprocess.run(
            ['blkid', '-L', BTRFS_ROOT_LABEL],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()

        # Fallback: cari dari mount info
        result = subprocess.run(
            ['findmnt', '-n', '-o', 'SOURCE', '/'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        log.error(f"Gagal cari device Btrfs: {e}")
    return None


def _mount_btrfs_root(device: str) -> bool:
    """Mount raw Btrfs partition (tanpa subvolume) ke tmp dir."""
    try:
        BTRFS_MNT_TMP.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ['mount', '-o', 'noatime', device, str(BTRFS_MNT_TMP)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            log.info(f"Btrfs root ter-mount di {BTRFS_MNT_TMP}")
            return True
        else:
            log.error(f"Gagal mount Btrfs: {result.stderr}")
            return False
    except Exception as e:
        log.error(f"Error mount Btrfs: {e}")
        return False


def _umount_btrfs_root():
    """Unmount tmp Btrfs mount."""
    try:
        subprocess.run(['umount', str(BTRFS_MNT_TMP)],
                      capture_output=True, text=True)
        BTRFS_MNT_TMP.rmdir()
    except Exception:
        pass


def _cari_snapshot_terbaru() -> Path | None:
    """
    Cari snapshot terbaru di /.snapshots.
    Snapper simpan snapshot di /.snapshots/<id>/snapshot/
    """
    if not SNAPSHOT_DIR.exists():
        log.warning("/.snapshots tidak ditemukan")
        return None

    kandidat = []
    for entry in SNAPSHOT_DIR.iterdir():
        # Format Snapper: /.snapshots/<id>/snapshot
        snap_path = entry / "snapshot"
        if snap_path.exists() and snap_path.is_dir():
            kandidat.append((entry.stat().st_mtime, snap_path))

    if not kandidat:
        log.warning("Tidak ada snapshot Snapper di /.snapshots")
        return None

    # Ambil yang paling baru
    kandidat.sort(reverse=True)
    latest = kandidat[0][1]
    log.info(f"Snapshot terbaru: {latest}")
    return latest


def _cari_snapshot_terbaru_dari_mount() -> Path | None:
    """
    Cari snapshot dari Btrfs yang sudah di-mount ke BTRFS_MNT_TMP.
    Untuk kasus di mana /.snapshots belum ter-mount.
    """
    snap_dir = BTRFS_MNT_TMP / "@snapshots"
    if not snap_dir.exists():
        snap_dir = BTRFS_MNT_TMP / ".snapshots"
    if not snap_dir.exists():
        return None

    kandidat = []
    for entry in snap_dir.iterdir():
        snap_path = entry / "snapshot"
        if snap_path.exists():
            kandidat.append((entry.stat().st_mtime, snap_path))

    if not kandidat:
        return None

    kandidat.sort(reverse=True)
    return kandidat[0][1]


# ══════════════════════════════════════════════════════════════════════════════
# ROLLBACK AKTUAL
# ══════════════════════════════════════════════════════════════════════════════

def mulai_rollback():
    """
    Prosedur rollback ke Btrfs snapshot terakhir yang bagus.
    PRD 5.1: home directory TIDAK dirollback — hanya @ (root).

    Alur:
    1. Cari device Btrfs root
    2. Mount raw Btrfs (tanpa subvolume)
    3. Rename @ → @_broken_<timestamp>
    4. Buat snapshot baru @ dari snapshot terbaru
    5. Unmount
    6. Reboot
    """
    log.warning("=" * 55)
    log.warning("NUSANTARA OS — PEMULIHAN OTOMATIS")
    log.warning("Sistem akan dipulihkan ke kondisi sebelumnya")
    log.warning("Folder /home kamu TIDAK terpengaruh")
    log.warning("=" * 55)

    _tulis_recovery_log("ROLLBACK DIPICU — sistem gagal boot berulang")

    # ── 1. Cek filesystem Btrfs ────────────────────────────────────────────
    try:
        result = subprocess.run(
            ['findmnt', '-n', '-o', 'FSTYPE', '/'],
            capture_output=True, text=True
        )
        fs_type = result.stdout.strip()
        if fs_type != 'btrfs':
            log.warning(f"Root filesystem '{fs_type}' bukan Btrfs — rollback dilewati")
            _tulis_recovery_log(f"ROLLBACK DILEWATI — filesystem {fs_type} bukan Btrfs")
            reset_counter()
            return
    except Exception as e:
        log.error(f"Gagal cek filesystem: {e}")

    # ── 2. Cari device Btrfs ───────────────────────────────────────────────
    device = _cari_device_btrfs()
    if not device:
        log.error("Gagal cari block device Btrfs root")
        _tulis_recovery_log("ROLLBACK GAGAL — tidak bisa cari block device")
        reset_counter()
        return

    log.info(f"Device Btrfs: {device}")
    _tulis_recovery_log(f"Device Btrfs: {device}")

    # ── 3. Mount raw Btrfs ─────────────────────────────────────────────────
    if not _mount_btrfs_root(device):
        log.error("Gagal mount Btrfs root partition")
        _tulis_recovery_log("ROLLBACK GAGAL — gagal mount Btrfs")
        reset_counter()
        return

    try:
        # ── 4. Cari snapshot terbaru ───────────────────────────────────────
        snapshot = _cari_snapshot_terbaru_dari_mount()
        if not snapshot:
            # Coba dari /.snapshots yang sudah ter-mount
            snapshot = _cari_snapshot_terbaru()

        if not snapshot:
            log.error("Tidak ada snapshot tersedia untuk rollback")
            _tulis_recovery_log("ROLLBACK GAGAL — tidak ada snapshot tersedia")
            _umount_btrfs_root()
            reset_counter()
            return

        log.info(f"Snapshot untuk rollback: {snapshot}")
        _tulis_recovery_log(f"Snapshot target: {snapshot}")

        # ── 5. Rename @ yang rusak ─────────────────────────────────────────
        subvol_root = BTRFS_MNT_TMP / "@"
        timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
        subvol_lama = BTRFS_MNT_TMP / f"@_broken_{timestamp}"

        log.info(f"Rename @ → @_broken_{timestamp}")
        result = subprocess.run(
            ['btrfs', 'subvolume', 'snapshot',
             str(subvol_root), str(subvol_lama)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            # Coba rename biasa
            subvol_root.rename(subvol_lama)

        _tulis_recovery_log(f"@ lama di-backup ke @_broken_{timestamp}")

        # ── 6. Buat @ baru dari snapshot ──────────────────────────────────
        log.info(f"Buat @ baru dari snapshot: {snapshot}")
        result = subprocess.run(
            ['btrfs', 'subvolume', 'snapshot',
             str(snapshot), str(BTRFS_MNT_TMP / "@")],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            log.error(f"Gagal buat snapshot @: {result.stderr}")
            _tulis_recovery_log(f"ROLLBACK GAGAL — btrfs snapshot error: {result.stderr}")
            # Restore @ lama kalau gagal
            if subvol_lama.exists():
                subvol_lama.rename(BTRFS_MNT_TMP / "@")
            _umount_btrfs_root()
            reset_counter()
            return

        _tulis_recovery_log("@ baru berhasil dibuat dari snapshot ✅")
        log.info("Rollback Btrfs berhasil! Reboot dalam 5 detik...")

    except Exception as e:
        log.error(f"Error saat rollback: {e}")
        _tulis_recovery_log(f"ROLLBACK ERROR: {e}")
    finally:
        _umount_btrfs_root()

    # ── 7. Reset counter + reboot ──────────────────────────────────────────
    reset_counter()
    _tulis_recovery_log("Sistem akan reboot ke snapshot yang dipulihkan")

    log.info("Reboot dalam 5 detik...")
    import time
    time.sleep(5)
    subprocess.run(['systemctl', 'reboot'])


# ══════════════════════════════════════════════════════════════════════════════
# MAIN: CEK BOOT
# ══════════════════════════════════════════════════════════════════════════════

def cek_boot():
    """
    Fungsi utama Boot Watcher.
    Dipanggil setiap kali sistem boot (dari main.py Guardian).

    Alur:
    1. Baca counter gagal boot
    2. Kalau sudah >= MAX_GAGAL → ROLLBACK
    3. Kalau belum → tambah counter, lanjut boot normal
    4. Setelah boot sukses → reset_counter() dipanggil dari main.py
    """
    log.info("Boot Watcher: cek status boot...")

    counter = baca_counter()

    if counter >= MAX_GAGAL:
        log.warning(f"PERHATIAN! Sistem gagal boot {counter}x berturut-turut!")
        log.warning("Memulai prosedur pemulihan otomatis...")
        _tulis_recovery_log(
            f"TRIGGER ROLLBACK setelah {counter}x gagal boot (threshold: {MAX_GAGAL})"
        )
        mulai_rollback()
    else:
        counter_baru = counter + 1
        tulis_counter(counter_baru)
        log.info(f"Boot attempt ke-{counter_baru} — sistem loading...")
        if counter_baru > 0:
            _tulis_recovery_log(f"Boot attempt ke-{counter_baru} — belum trigger rollback")


# ── Test langsung ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

    log.info("=== Test Boot Watcher ===")
    log.info(f"Config: MAX_GAGAL={MAX_GAGAL}, USE_SYSTEMD_BOOT={USE_SYSTEMD_BOOT}")
    log.info(f"Counter file: {BOOT_COUNTER_FILE}")
    log.info(f"Recovery log: {RECOVERY_LOG}")

    log.info("\nSimulasi boot pertama:")
    cek_boot()

    log.info("\nSimulasi boot sukses (reset counter):")
    reset_counter()

    if Path(RECOVERY_LOG).exists():
        print("\nRecovery log:")
        print(Path(RECOVERY_LOG).read_text())
