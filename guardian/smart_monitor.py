#!/usr/bin/env python3
"""
NusantaraOS — S.M.A.R.T Disk Health Monitor
File: guardian/smart_monitor.py

Monitor kesehatan fisik disk (SSD/HDD) via S.M.A.R.T.
Deteksi reallocated sectors, pending sectors, uncorrectable errors.
Diintegrasikan ke health_monitor.py lewat cek_smart().

Butuh: smartmontools (smartctl) terinstall di sistem.
Install: sudo pacman -S smartmontools
"""

import json
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

# Baca config kalau tersedia
try:
    from config import get_config
    _cfg = get_config()
    WARN_REALLOCATED = _cfg.smart_warn_reallocated
    CRIT_PENDING     = _cfg.smart_crit_pending
    SMART_ENABLED    = _cfg.smart_enabled
except ImportError:
    WARN_REALLOCATED = 10
    CRIT_PENDING     = 5
    SMART_ENABLED    = True


def _cari_disk() -> list[str]:
    """
    Temukan semua disk yang terdeteksi di sistem.
    Return list path seperti ['/dev/sda', '/dev/nvme0n1'].
    """
    try:
        hasil = subprocess.run(
            ['lsblk', '-d', '-n', '-o', 'NAME,TYPE'],
            capture_output=True, text=True
        )
        disks = []
        for line in hasil.stdout.strip().split('\n'):
            parts = line.split()
            if len(parts) >= 2 and parts[1] in ('disk',):
                disks.append(f"/dev/{parts[0]}")
        return disks
    except Exception as e:
        log.error(f"Gagal cari disk: {e}")
        return []


def _parse_smartctl(output: dict, disk: str) -> dict:
    """
    Parse output JSON dari smartctl -j dan return status + detail.
    """
    result = {
        "disk":       disk,
        "status":     "aman",
        "nilai":      "Sehat",
        "detail":     "",
        "masalah":    [],
    }

    # Cek apakah disk SMART-capable
    smart_status = output.get("smart_status", {})
    passed = smart_status.get("passed", True)

    if not passed:
        result["status"] = "kritis"
        result["nilai"]  = "GAGAL"
        result["masalah"].append("S.M.A.R.T self-test GAGAL — disk berisiko tinggi!")

    # Parse ATA attributes (HDD)
    ata_attrs = {
        attr["id"]: attr
        for attr in output.get("ata_smart_attributes", {}).get("table", [])
    }

    # ID penting:
    # 5   = Reallocated Sectors Count
    # 187 = Reported Uncorrectable Errors
    # 196 = Reallocation Event Count
    # 197 = Current Pending Sector Count
    # 198 = Offline Uncorrectable

    for attr_id, label, threshold, level in [
        (5,   "Reallocated Sectors",       WARN_REALLOCATED, "peringatan"),
        (187, "Uncorrectable Errors",       1,                "kritis"),
        (196, "Reallocation Events",        WARN_REALLOCATED, "peringatan"),
        (197, "Pending Sectors",            CRIT_PENDING,     "kritis"),
        (198, "Offline Uncorrectable",      1,                "kritis"),
    ]:
        attr = ata_attrs.get(attr_id)
        if not attr:
            continue

        raw_val = attr.get("raw", {}).get("value", 0)
        if isinstance(raw_val, str):
            try:
                raw_val = int(raw_val.split()[0])
            except (ValueError, IndexError):
                raw_val = 0

        if raw_val >= threshold:
            msg = f"{label}: {raw_val}"
            result["masalah"].append(msg)
            # Eskalasi ke level tertinggi
            if level == "kritis":
                result["status"] = "kritis"
            elif result["status"] == "aman" and level == "peringatan":
                result["status"] = "peringatan"

    # NVMe — cek via nvme_smart_health_information_log
    nvme_log = output.get("nvme_smart_health_information_log", {})
    if nvme_log:
        critical_warn = nvme_log.get("critical_warning", 0)
        media_errors  = nvme_log.get("media_errors", 0)
        if critical_warn > 0:
            result["masalah"].append(f"NVMe critical warning: {critical_warn}")
            result["status"] = "kritis"
        if media_errors > 0:
            result["masalah"].append(f"NVMe media errors: {media_errors}")
            result["status"] = "peringatan" if result["status"] == "aman" else result["status"]

    # Susun nilai dan detail
    if result["masalah"]:
        result["nilai"]  = "; ".join(result["masalah"][:2])  # max 2 di UI
        result["detail"] = f"{disk}: {', '.join(result['masalah'])}"
    else:
        result["nilai"]  = "Sehat"
        result["detail"] = f"{disk}: tidak ada masalah S.M.A.R.T"

    return result


def cek_smart(disk: str | None = None) -> list[dict]:
    """
    Cek kesehatan S.M.A.R.T satu atau semua disk.
    Return list hasil per disk:
      [{"disk": "/dev/sda", "status": "ok/peringatan/kritis",
        "nilai": "...", "detail": "...", "masalah": [...]}]
    """
    if not SMART_ENABLED:
        log.info("S.M.A.R.T monitoring dinonaktifkan di config")
        return []

    disks = [disk] if disk else _cari_disk()
    if not disks:
        log.warning("Tidak ada disk ditemukan untuk S.M.A.R.T check")
        return []

    hasil_semua = []
    for d in disks:
        log.info(f"Cek S.M.A.R.T untuk {d}...")
        try:
            result = subprocess.run(
                ['smartctl', '-j', '-a', d],
                capture_output=True, text=True, timeout=15
            )
            # smartctl exit code: 0=ok, 4=SMART error, 64=no smart, 128=no permission
            if result.returncode == 64:
                log.info(f"{d}: tidak support S.M.A.R.T")
                continue
            if result.returncode == 128:
                log.warning(f"{d}: perlu akses root untuk S.M.A.R.T")
                continue

            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                log.warning(f"{d}: output smartctl tidak valid JSON")
                continue

            parsed = _parse_smartctl(data, d)
            hasil_semua.append(parsed)

            if parsed["status"] == "aman":
                log.info(f"{d}: S.M.A.R.T aman")
            else:
                log.warning(f"{d}: S.M.A.R.T {parsed['status']} — {parsed['nilai']}")

        except FileNotFoundError:
            log.warning("smartctl tidak terinstall — skip S.M.A.R.T check")
            log.warning("Install: sudo pacman -S smartmontools")
            break  # Tidak perlu coba disk lain
        except subprocess.TimeoutExpired:
            log.error(f"{d}: smartctl timeout")
        except Exception as e:
            log.error(f"{d}: error S.M.A.R.T — {e}")

    return hasil_semua


def status_smart_overall(hasil: list[dict]) -> tuple[str, str, str]:
    """
    Agregat semua hasil S.M.A.R.T menjadi satu status untuk health_monitor.
    Return (status, nilai, detail) — format sama dengan cek_disk(), cek_ram(), dll.
    """
    if not hasil:
        return 'aman', 'Sehat', 'S.M.A.R.T tidak tersedia atau dinonaktifkan'

    ada_kritis    = any(h["status"] == "kritis"    for h in hasil)
    ada_peringatan = any(h["status"] == "peringatan" for h in hasil)

    if ada_kritis:
        disk_kritis = next(h for h in hasil if h["status"] == "kritis")
        return 'kritis', disk_kritis["nilai"], disk_kritis["detail"]
    elif ada_peringatan:
        disk_warn = next(h for h in hasil if h["status"] == "peringatan")
        return 'peringatan', disk_warn["nilai"], disk_warn["detail"]
    else:
        n = len(hasil)
        return 'aman', f'{n} disk sehat', ', '.join(h["disk"] for h in hasil)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
    log.info("Test S.M.A.R.T Monitor...")
    hasil = cek_smart()
    if hasil:
        for h in hasil:
            print(f"  {h['disk']}: {h['status']} — {h['nilai']}")
            if h["masalah"]:
                for m in h["masalah"]:
                    print(f"    ⚠ {m}")
    else:
        print("  Tidak ada data S.M.A.R.T (smartctl mungkin belum terinstall)")
    status, nilai, detail = status_smart_overall(hasil)
    print(f"\nOverall: {status} | {nilai} | {detail}")
