#!/usr/bin/env python3

# =============================================
# NusantaraOS - System Guardian Daemon
# Ini "jantung" NusantaraOS — semua modul
# dikontrol dari sini
# =============================================

import time
import logging
from boot_watcher import cek_boot, reset_counter
from hardware_watcher import deteksi_gpu
from health_monitor import laporan_sehat
from notification_dispatcher import (
    notif_sistem_sehat,
    notif_disk_hampir_penuh,
    notif_disk_kritis,
    notif_ram_penuh,
    notif_gpu_fallback
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    handlers=[
        logging.FileHandler('/var/log/nusantara/guardian.log'),
        logging.StreamHandler()
    ]
)

log = logging.getLogger(__name__)

# Seberapa sering Guardian cek kesehatan sistem
# 300 detik = 5 menit
INTERVAL_CEK = 300

def jalankan_guardian():
    log.info("=" * 50)
    log.info("NUSANTARA OS — GUARDIAN DAEMON AKTIF")
    log.info("Sistem kamu sedang dipantau")
    log.info("=" * 50)

    # 1. Cek boot — aman atau perlu rollback?
    log.info("Langkah 1: Cek status boot...")
    cek_boot()

    # 2. Deteksi GPU
    log.info("Langkah 2: Deteksi hardware...")
    gpu = deteksi_gpu()
    if gpu == 'unknown' or gpu is None:
        log.warning("GPU tidak dikenal — aktifkan llvmpipe")
        notif_gpu_fallback()

    # 3. Boot berhasil — reset counter
    log.info("Langkah 3: Boot sukses, reset counter...")
    reset_counter()

    # 4. Loop utama — cek kesehatan tiap 5 menit
    log.info("Langkah 4: Mulai loop pemantauan...")
    log.info(f"Sistem akan dicek setiap {INTERVAL_CEK // 60} menit")
    log.info("=" * 50)

    while True:
        log.info("Menjalankan Sehat Check...")
        semua_aman = laporan_sehat()

        if semua_aman:
            notif_sistem_sehat()

        log.info(f"Istirahat {INTERVAL_CEK // 60} menit, lalu cek lagi...")
        time.sleep(INTERVAL_CEK)

if __name__ == "__main__":
    jalankan_guardian()
