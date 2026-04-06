#!/usr/bin/env python3

# =============================================
# NusantaraOS - Boot Watcher
# Tugasnya: deteksi kalau sistem gagal boot
# Kalau gagal 2x berturut-turut = auto rollback
# Ini yang bikin NusantaraOS "tidak bisa rusak"
# =============================================

import os
import logging

log = logging.getLogger(__name__)

# File ini yang nyimpen hitungan gagal boot
# Lokasinya di /var/lib/nusantara/ nanti
# Sementara kita test di /tmp dulu
BOOT_COUNTER_FILE = '/tmp/nusantara-boot-counter'
MAX_GAGAL = 2  # berapa kali gagal sebelum rollback

def baca_counter():
    """
    Baca berapa kali sistem sudah gagal boot.
    Kalau filenya belum ada, berarti baru pertama boot = 0
    """
    try:
        if os.path.exists(BOOT_COUNTER_FILE):
            with open(BOOT_COUNTER_FILE, 'r') as f:
                angka = int(f.read().strip())
                log.info(f"Counter boot gagal saat ini: {angka}x")
                return angka
        else:
            log.info("Belum ada counter — ini boot pertama, semua aman")
            return 0
    except Exception as e:
        log.error(f"Gagal baca counter: {e}")
        return 0

def tulis_counter(angka):
    """
    Simpan angka counter ke file
    """
    try:
        with open(BOOT_COUNTER_FILE, 'w') as f:
            f.write(str(angka))
        log.info(f"Counter disimpan: {angka}x")
    except Exception as e:
        log.error(f"Gagal simpan counter: {e}")

def reset_counter():
    """
    Reset counter ke 0 kalau boot berhasil normal
    Dipanggil setelah sistem berhasil masuk desktop
    """
    try:
        if os.path.exists(BOOT_COUNTER_FILE):
            os.remove(BOOT_COUNTER_FILE)
        log.info("Boot berhasil! Counter direset ke 0")
    except Exception as e:
        log.error(f"Gagal reset counter: {e}")

def cek_boot():
    """
    Fungsi utama Boot Watcher.
    Dipanggil setiap kali sistem boot.
    
    Alurnya:
    1. Baca counter gagal boot
    2. Kalau sudah 2x atau lebih = ROLLBACK
    3. Kalau belum = tambah counter, lanjut boot normal
    4. Kalau boot sukses = reset counter
    """
    log.info("Boot Watcher mulai ngecek...")

    counter = baca_counter()

    if counter >= MAX_GAGAL:
        # Sudah gagal 2x — saatnya rollback!
        log.warning(f"PERHATIAN! Sistem gagal boot {counter}x berturut-turut!")
        log.warning("Memulai prosedur pemulihan otomatis...")
        mulai_rollback()
    else:
        # Belum gagal 2x — tambah counter dulu
        # Nanti kalau boot sukses, counter direset
        counter_baru = counter + 1
        tulis_counter(counter_baru)
        log.info(f"Boot attempt ke-{counter_baru}, sistem lagi loading...")
        log.info("Kalau boot sukses, counter akan direset otomatis")

def mulai_rollback():
    """
    Prosedur rollback ke snapshot Btrfs terakhir yang bagus.
    Ini yang nanti konek ke Btrfs snapshot system.
    Untuk sekarang kita log dulu — implementasi Btrfs menyusul.
    """
    log.warning("=" * 50)
    log.warning("NUSANTARA OS — PEMULIHAN OTOMATIS")
    log.warning("Sistem akan dipulihkan ke kondisi sebelumnya")
    log.warning("Data kamu di /home TIDAK akan terpengaruh")
    log.warning("=" * 50)

    # TODO: ini yang nanti kita implementasi
    # 1. Mount snapshot Btrfs terakhir yang bagus
    # 2. Set sebagai root baru
    # 3. Reboot ke snapshot tersebut
    # 4. Kirim notifikasi ke user setelah berhasil

    log.info("(Implementasi Btrfs rollback menyusul di Phase 5)")
    reset_counter()

# --- Test langsung kalau file ini dijalanin sendiri ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
    
    log.info("=== Simulasi Boot Watcher ===")
    log.info("Boot pertama:")
    cek_boot()
    
    print()
    log.info("Simulasi boot gagal kedua:")
    cek_boot()
    
    print()
    log.info("Simulasi boot gagal ketiga — harusnya trigger rollback:")
    cek_boot()
    
    print()
    log.info("Simulasi boot sukses — reset counter:")
    reset_counter()
