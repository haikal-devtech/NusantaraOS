#!/usr/bin/env python3

# =============================================
# NusantaraOS - Notification Dispatcher
# Tugasnya: kirim notifikasi ke user
# Semua notifikasi dari Guardian lewat sini
# Bahasa Indonesia, bukan error code!
# =============================================

import subprocess
import logging

log = logging.getLogger(__name__)

# Tipe notifikasi
INFO     = 'info'
PERINGATAN = 'peringatan'
KRITIS   = 'kritis'
SUKSES   = 'sukses'

def kirim_notifikasi(judul, pesan, tipe=INFO):
    """
    Kirim notifikasi desktop ke user.
    Pakai notify-send yang built-in di Linux.
    """
    log.info(f"Mengirim notifikasi [{tipe.upper()}]: {judul}")

    # Pilih icon sesuai tipe
    if tipe == SUKSES:
        icon = 'dialog-information'
        urgency = 'normal'
    elif tipe == PERINGATAN:
        icon = 'dialog-warning'
        urgency = 'normal'
    elif tipe == KRITIS:
        icon = 'dialog-error'
        urgency = 'critical'
    else:
        icon = 'dialog-information'
        urgency = 'low'

    try:
        subprocess.run([
            'notify-send',
            '--app-name=NusantaraOS',
            f'--urgency={urgency}',
            f'--icon={icon}',
            judul,
            pesan
        ])
        log.info("Notifikasi berhasil dikirim")

    except FileNotFoundError:
        # notify-send belum terinstall atau tidak ada display
        # Di terminal langsung print aja dulu
        log.info(f"[NOTIFIKASI] {judul}: {pesan}")

    except Exception as e:
        log.error(f"Gagal kirim notifikasi: {e}")

# --- Pesan-pesan siap pakai ---

def notif_sistem_sehat():
    kirim_notifikasi(
        "Sistem Kamu Sehat ✓",
        "Tidak ada masalah yang ditemukan. Guardian terus memantau.",
        SUKSES
    )

def notif_disk_hampir_penuh(persen):
    kirim_notifikasi(
        "Penyimpanan Hampir Penuh",
        f"Disk sudah {persen:.0f}% terpakai. Segera hapus file yang tidak perlu.",
        PERINGATAN
    )

def notif_disk_kritis(persen):
    kirim_notifikasi(
        "⚠️ Penyimpanan Kritis!",
        f"Disk sudah {persen:.0f}% terpakai. Sistem bisa terganggu kalau tidak segera dibersihkan.",
        KRITIS
    )

def notif_ram_penuh():
    kirim_notifikasi(
        "Memori Hampir Habis",
        "RAM hampir penuh. Coba tutup beberapa aplikasi yang tidak dipakai.",
        PERINGATAN
    )

def notif_layanan_bermasalah(nama_layanan):
    kirim_notifikasi(
        "Ada Layanan yang Bermasalah",
        f"Layanan '{nama_layanan}' tidak berjalan normal. Klik untuk perbaiki.",
        PERINGATAN
    )

def notif_gpu_fallback():
    kirim_notifikasi(
        "Driver GPU Bermasalah",
        "NusantaraOS memakai mode cadangan. Klik 'Perbaiki Driver' untuk mengembalikan performa normal.",
        PERINGATAN
    )

def notif_pemulihan_berhasil():
    kirim_notifikasi(
        "Sistem Berhasil Dipulihkan 🛡️",
        "Sistem sempat bermasalah tapi sudah dipulihkan otomatis. Data kamu aman.",
        SUKSES
    )

def notif_pembaruan_tersedia(jumlah):
    kirim_notifikasi(
        "Pembaruan Tersedia",
        f"Ada {jumlah} pembaruan yang siap dipasang. Disarankan untuk segera memperbarui.",
        INFO
    )

# --- Test langsung ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

    log.info("Test semua jenis notifikasi...")
    print()

    notif_sistem_sehat()
    notif_disk_hampir_penuh(87)
    notif_disk_kritis(96)
    notif_ram_penuh()
    notif_gpu_fallback()
    notif_pemulihan_berhasil()
    notif_pembaruan_tersedia(5)

    log.info("Semua notifikasi berhasil dikirim!")
