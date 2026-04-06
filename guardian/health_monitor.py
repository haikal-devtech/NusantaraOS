#!/usr/bin/env python3

# =============================================
# NusantaraOS - Health Monitor (Sehat Check)
# Tugasnya: pantau kesehatan sistem
# Laporannya dalam Bahasa Indonesia biasa
# Bukan kode error — bahasa manusia!
# =============================================

import shutil
import logging
import subprocess

log = logging.getLogger(__name__)

def cek_disk():
    """
    Cek ruang penyimpanan yang tersisa.
    Kasih peringatan kalau hampir penuh.
    """
    log.info("Ngecek ruang penyimpanan...")
    try:
        total, terpakai, tersisa = shutil.disk_usage('/')
        persen = (terpakai / total) * 100

        # Konversi ke GB biar mudah dibaca
        total_gb = total // (2**30)
        tersisa_gb = tersisa // (2**30)

        log.info(f"Penyimpanan: {tersisa_gb} GB tersisa dari {total_gb} GB")

        if persen >= 95:
            log.warning("KRITIS! Penyimpanan hampir penuh — segera hapus file yang tidak perlu!")
            return 'kritis'
        elif persen >= 85:
            log.warning(f"Peringatan: Penyimpanan sudah {persen:.0f}% terpakai — mulai bersihkan")
            return 'peringatan'
        else:
            log.info(f"Penyimpanan aman — {persen:.0f}% terpakai")
            return 'aman'

    except Exception as e:
        log.error(f"Gagal cek penyimpanan: {e}")
        return 'error'

def cek_ram():
    """
    Cek penggunaan RAM saat ini.
    """
    log.info("Ngecek penggunaan memori...")
    try:
        hasil = subprocess.run(
            ['free', '-m'],
            capture_output=True,
            text=True
        )

        baris = hasil.stdout.split('\n')[1].split()
        total = int(baris[1])
        terpakai = int(baris[2])
        persen = (terpakai / total) * 100

        log.info(f"RAM: {terpakai} MB terpakai dari {total} MB ({persen:.0f}%)")

        if persen >= 90:
            log.warning("RAM hampir habis! Coba tutup beberapa aplikasi")
            return 'kritis'
        elif persen >= 75:
            log.warning(f"RAM mulai banyak terpakai — {persen:.0f}%")
            return 'peringatan'
        else:
            log.info(f"RAM aman — {persen:.0f}% terpakai")
            return 'aman'

    except Exception as e:
        log.error(f"Gagal cek RAM: {e}")
        return 'error'

def cek_layanan():
    """
    Cek apakah ada layanan sistem yang bermasalah.
    Pakai systemctl untuk deteksi.
    """
    log.info("Ngecek layanan sistem...")
    try:
        hasil = subprocess.run(
            ['systemctl', '--failed', '--no-legend'],
            capture_output=True,
            text=True
        )

        layanan_gagal = hasil.stdout.strip()

        if layanan_gagal:
            jumlah = len(layanan_gagal.split('\n'))
            log.warning(f"Ada {jumlah} layanan yang bermasalah!")
            log.warning(layanan_gagal)
            return 'bermasalah'
        else:
            log.info("Semua layanan sistem berjalan normal")
            return 'aman'

    except Exception as e:
        log.error(f"Gagal cek layanan: {e}")
        return 'error'

def laporan_sehat():
    """
    Fungsi utama — jalanin semua pengecekan
    dan kasih laporan lengkap dalam Bahasa Indonesia
    """
    log.info("=" * 45)
    log.info("SEHAT CHECK — LAPORAN KESEHATAN SISTEM")
    log.info("=" * 45)

    hasil_disk = cek_disk()
    hasil_ram = cek_ram()
    hasil_layanan = cek_layanan()

    print()
    log.info("=" * 45)
    log.info("RINGKASAN:")

    semua_aman = all(h == 'aman' for h in [hasil_disk, hasil_ram, hasil_layanan])

    if semua_aman:
        log.info("Sistem kamu sehat — tidak ada masalah!")
    else:
        if hasil_disk != 'aman':
            log.warning("Penyimpanan perlu diperhatikan")
        if hasil_ram != 'aman':
            log.warning("Memori perlu diperhatikan")
        if hasil_layanan != 'aman':
            log.warning("Ada layanan yang bermasalah")

    log.info("=" * 45)
    return semua_aman

# --- Test langsung ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
    laporan_sehat()
