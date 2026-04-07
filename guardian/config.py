#!/usr/bin/env python3
"""
NusantaraOS — Guardian Config
File: guardian/config.py

Baca /etc/nusantara/guardian.conf (INI format).
Kalau file tidak ada, pakai default values.
Semua modul import GuardianConfig dari sini — single source of truth.
"""

import configparser
import logging
from pathlib import Path

log = logging.getLogger(__name__)

CONFIG_PATH = Path("/etc/nusantara/guardian.conf")


class GuardianConfig:
    """
    Konfigurasi lengkap Guardian daemon.
    Auto-load dari /etc/nusantara/guardian.conf.
    Kalau file tidak ada, semua pakai default.
    """

    # ── Defaults ──────────────────────────────────────────────────────────────
    _DEFAULTS = {
        "guardian": {
            "interval_cek":    "300",     # detik antara health check
            "log_level":       "INFO",
            "socket_path":     "/run/nusantara/guardian.sock",
            "state_dir":       "/var/lib/nusantara",
            "log_dir":         "/var/log/nusantara",
        },
        "health": {
            "disk_warn_pct":   "85",      # % disk terpakai → peringatan
            "disk_crit_pct":   "95",      # % disk terpakai → kritis
            "ram_warn_pct":    "75",      # % RAM terpakai → peringatan
            "ram_crit_pct":    "90",      # % RAM terpakai → kritis
            "gpu_temp_warn":   "85",      # °C GPU → peringatan
            "gpu_temp_crit":   "100",     # °C GPU → kritis
        },
        "gpu": {
            "fallback_timeout": "30",     # detik sebelum fallback ke llvmpipe
            "dkms_auto_rebuild": "true",  # auto rebuild DKMS setelah kernel update
        },
        "boot": {
            "max_gagal":       "2",       # boot gagal berturut → rollback
            "use_systemd_boot": "true",   # pakai bootctl, fallback ke file
            "recovery_log":    "/var/log/nusantara/recovery.log",
        },
        "smart": {
            "enabled":         "true",    # aktifkan S.M.A.R.T monitoring
            "warn_reallocated": "10",     # jumlah reallocated sectors → peringatan
            "crit_pending":    "5",       # pending sectors → kritis
        },
    }

    def __init__(self, config_path: Path = CONFIG_PATH):
        self._parser = configparser.ConfigParser()

        # Load defaults dulu
        self._parser.read_dict(self._DEFAULTS)

        # Override dengan file kalau ada
        if config_path.exists():
            self._parser.read(config_path)
            log.info(f"Config dimuat dari {config_path}")
        else:
            log.info(f"Config file tidak ada di {config_path} — pakai default")

    # ── Guardian ──────────────────────────────────────────────────────────────

    @property
    def interval_cek(self) -> int:
        return self._parser.getint("guardian", "interval_cek")

    @property
    def log_level(self) -> str:
        return self._parser.get("guardian", "log_level")

    @property
    def socket_path(self) -> str:
        return self._parser.get("guardian", "socket_path")

    @property
    def state_dir(self) -> Path:
        return Path(self._parser.get("guardian", "state_dir"))

    @property
    def log_dir(self) -> Path:
        return Path(self._parser.get("guardian", "log_dir"))

    # ── Health ────────────────────────────────────────────────────────────────

    @property
    def disk_warn_pct(self) -> float:
        return self._parser.getfloat("health", "disk_warn_pct")

    @property
    def disk_crit_pct(self) -> float:
        return self._parser.getfloat("health", "disk_crit_pct")

    @property
    def ram_warn_pct(self) -> float:
        return self._parser.getfloat("health", "ram_warn_pct")

    @property
    def ram_crit_pct(self) -> float:
        return self._parser.getfloat("health", "ram_crit_pct")

    @property
    def gpu_temp_warn(self) -> int:
        return self._parser.getint("health", "gpu_temp_warn")

    @property
    def gpu_temp_crit(self) -> int:
        return self._parser.getint("health", "gpu_temp_crit")

    # ── GPU ───────────────────────────────────────────────────────────────────

    @property
    def fallback_timeout(self) -> int:
        return self._parser.getint("gpu", "fallback_timeout")

    @property
    def dkms_auto_rebuild(self) -> bool:
        return self._parser.getboolean("gpu", "dkms_auto_rebuild")

    # ── Boot ──────────────────────────────────────────────────────────────────

    @property
    def max_gagal(self) -> int:
        return self._parser.getint("boot", "max_gagal")

    @property
    def use_systemd_boot(self) -> bool:
        return self._parser.getboolean("boot", "use_systemd_boot")

    @property
    def recovery_log(self) -> Path:
        return Path(self._parser.get("boot", "recovery_log"))

    # ── S.M.A.R.T ─────────────────────────────────────────────────────────────

    @property
    def smart_enabled(self) -> bool:
        return self._parser.getboolean("smart", "enabled")

    @property
    def smart_warn_reallocated(self) -> int:
        return self._parser.getint("smart", "warn_reallocated")

    @property
    def smart_crit_pending(self) -> int:
        return self._parser.getint("smart", "crit_pending")

    def __repr__(self) -> str:
        return (
            f"GuardianConfig("
            f"interval={self.interval_cek}s, "
            f"disk_warn={self.disk_warn_pct}%, "
            f"ram_crit={self.ram_crit_pct}%, "
            f"socket={self.socket_path})"
        )


# Singleton — import ini dari modul manapun
_config: GuardianConfig | None = None


def get_config() -> GuardianConfig:
    """
    Return singleton GuardianConfig.
    Load sekali, reuse seterusnya.
    """
    global _config
    if _config is None:
        _config = GuardianConfig()
    return _config


def reload_config() -> GuardianConfig:
    """Force reload dari file (dipanggil setelah SIGHUP)."""
    global _config
    _config = GuardianConfig()
    return _config


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
    cfg = get_config()
    print(cfg)
    print(f"  interval_cek   = {cfg.interval_cek}s")
    print(f"  disk_warn_pct  = {cfg.disk_warn_pct}%")
    print(f"  disk_crit_pct  = {cfg.disk_crit_pct}%")
    print(f"  ram_warn_pct   = {cfg.ram_warn_pct}%")
    print(f"  ram_crit_pct   = {cfg.ram_crit_pct}%")
    print(f"  socket_path    = {cfg.socket_path}")
    print(f"  max_gagal      = {cfg.max_gagal}")
    print(f"  smart_enabled  = {cfg.smart_enabled}")
