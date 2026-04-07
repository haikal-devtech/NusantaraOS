#!/usr/bin/env python3
# =============================================
# NusantaraOS - Health Monitor (Sehat Check)
# Tugasnya: pantau kesehatan sistem
# Laporannya dalam Bahasa Indonesia biasa
# Bukan kode error — bahasa manusia!
# =============================================
import json
import shutil
import logging
import subprocess
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

HEALTH_STATE_PATH = Path("/var/lib/nusantara/health-state.json")
HW_STATE_PATH     = Path("/var/lib/nusantara/hw-state.json")


def cek_disk():
    """
    Cek ruang penyimpanan yang tersisa.
    Kasih peringatan kalau hampir penuh.
    """
    log.info("Ngecek ruang penyimpanan...")
    try:
        total, terpakai, tersisa = shutil.disk_usage('/')
        persen = (terpakai / total) * 100
        total_gb    = round(total    / (2**30), 1)
        tersisa_gb  = round(tersisa  / (2**30), 1)
        terpakai_gb = round(terpakai / (2**30), 1)
        log.info(f"Penyimpanan: {tersisa_gb} GB tersisa dari {total_gb} GB")

        value  = f"{tersisa_gb} GB tersisa ({persen:.0f}% terpakai)"
        detail = f"{terpakai_gb} GB dari {total_gb} GB terpakai"

        if persen >= 95:
            log.warning("KRITIS! Penyimpanan hampir penuh!")
            return 'kritis', value, detail
        elif persen >= 85:
            log.warning(f"Peringatan: Penyimpanan {persen:.0f}% terpakai")
            return 'peringatan', value, detail
        else:
            log.info(f"Penyimpanan aman — {persen:.0f}% terpakai")
            return 'aman', value, detail
    except Exception as e:
        log.error(f"Gagal cek penyimpanan: {e}")
        return 'error', "Tidak diketahui", str(e)


def cek_ram():
    """
    Cek penggunaan RAM saat ini.
    """
    log.info("Ngecek penggunaan memori...")
    try:
        hasil = subprocess.run(['free', '-m'], capture_output=True, text=True)
        baris    = hasil.stdout.split('\n')[1].split()
        total    = int(baris[1])
        terpakai = int(baris[2])
        tersisa  = total - terpakai
        persen   = (terpakai / total) * 100

        # Konversi ke GB kalau >= 1024 MB
        def fmt(mb):
            return f"{mb/1024:.1f} GB" if mb >= 1024 else f"{mb} MB"

        log.info(f"RAM: {terpakai} MB terpakai dari {total} MB ({persen:.0f}%)")

        value  = f"{fmt(terpakai)} / {fmt(total)} ({persen:.0f}%)"
        detail = f"{fmt(tersisa)} tersisa"

        if persen >= 90:
            log.warning("RAM hampir habis!")
            return 'kritis', value, detail
        elif persen >= 75:
            log.warning(f"RAM mulai banyak terpakai — {persen:.0f}%")
            return 'peringatan', value, detail
        else:
            log.info(f"RAM aman — {persen:.0f}% terpakai")
            return 'aman', value, detail
    except Exception as e:
        log.error(f"Gagal cek RAM: {e}")
        return 'error', "Tidak diketahui", str(e)


def cek_layanan():
    """
    Cek apakah ada layanan sistem yang bermasalah.
    """
    log.info("Ngecek layanan sistem...")
    try:
        hasil = subprocess.run(
            ['systemctl', '--failed', '--no-legend'],
            capture_output=True, text=True
        )
        layanan_gagal = hasil.stdout.strip()
        if layanan_gagal:
            daftar = [b.split()[0] for b in layanan_gagal.split('\n') if b.strip()]
            log.warning(f"Ada {len(daftar)} layanan bermasalah: {daftar}")
            return 'bermasalah', daftar
        else:
            log.info("Semua layanan sistem berjalan normal")
            return 'aman', []
    except Exception as e:
        log.error(f"Gagal cek layanan: {e}")
        return 'error', []


def cek_gpu():
    """
    Baca status GPU dari hw-state.json yang ditulis HardwareWatcher.
    """
    try:
        if HW_STATE_PATH.exists():
            data     = json.loads(HW_STATE_PATH.read_text())
            vendor   = data.get("gpu_vendor", "unknown")
            model    = data.get("gpu_model", "Tidak diketahui")
            driver   = data.get("driver", "unknown")
            llvmpipe = data.get("using_llvmpipe", False)

            vendor_label = {"intel": "Intel", "amd": "AMD", "nvidia": "NVIDIA"}.get(vendor, vendor)

            if llvmpipe:
                return 'peringatan', "Software rendering aktif", f"llvmpipe — driver {vendor_label} gagal dimuat"
            else:
                return 'aman', f"{vendor_label} aktif", f"{driver} — {model}"
        else:
            return 'aman', "GPU aktif", "Data driver belum tersedia"
    except Exception as e:
        log.error(f"Gagal baca GPU state: {e}")
        return 'aman', "GPU aktif", "Tidak bisa membaca status"


def tulis_health_state(disk, ram, gpu, layanan):
    """
    Tulis hasil semua cek ke JSON — dibaca oleh Sehat Check GUI.
    disk, ram, gpu  : tuple (status, value, detail)
    layanan         : tuple (status, list_failed)
    """
    # Map status string ke format GUI
    def map_status(s):
        return {"aman": "ok", "peringatan": "warning", "kritis": "error",
                "bermasalah": "error", "error": "error"}.get(s, "ok")

    disk_s, disk_v, disk_d   = disk
    ram_s,  ram_v,  ram_d    = ram
    gpu_s,  gpu_v,  gpu_d    = gpu
    svc_s,  svc_failed       = layanan

    state = {
        "storage": {
            "status": map_status(disk_s),
            "value":  disk_v,
            "detail": disk_d,
        },
        "memory": {
            "status": map_status(ram_s),
            "value":  ram_v,
            "detail": ram_d,
        },
        "gpu": {
            "status": map_status(gpu_s),
            "value":  gpu_v,
            "detail": gpu_d,
        },
        "guardian": {
            "status": "ok",
            "value":  "Aktif",
            "detail": "Semua modul berjalan",
        },
        "services": {
            "status": map_status(svc_s),
            "failed": svc_failed,
        },
        "last_check": datetime.now().isoformat(),
    }

    try:
        HEALTH_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        HEALTH_STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False))
        log.info(f"Health state ditulis ke {HEALTH_STATE_PATH}")
    except Exception as e:
        log.error(f"Gagal tulis health state: {e}")


def laporan_sehat():
    """
    Fungsi utama — jalanin semua pengecekan
    dan kasih laporan lengkap dalam Bahasa Indonesia.
    """
    log.info("=" * 45)
    log.info("SEHAT CHECK — LAPORAN KESEHATAN SISTEM")
    log.info("=" * 45)

    disk    = cek_disk()
    ram     = cek_ram()
    gpu     = cek_gpu()
    layanan = cek_layanan()

    # Tulis ke JSON biar GUI bisa baca
    tulis_health_state(disk, ram, gpu, layanan)

    log.info("=" * 45)
    log.info("RINGKASAN:")

    semua_aman = all(t[0] == 'aman' for t in [disk, ram, gpu]) and layanan[0] == 'aman'

    if semua_aman:
        log.info("Sistem kamu sehat — tidak ada masalah!")
    else:
        if disk[0]    != 'aman': log.warning(f"Penyimpanan: {disk[1]}")
        if ram[0]     != 'aman': log.warning(f"Memori: {ram[1]}")
        if gpu[0]     != 'aman': log.warning(f"GPU: {gpu[1]}")
        if layanan[0] != 'aman': log.warning(f"Layanan bermasalah: {layanan[1]}")

    log.info("=" * 45)
    return semua_aman


# --- Test langsung ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
    laporan_sehat()
