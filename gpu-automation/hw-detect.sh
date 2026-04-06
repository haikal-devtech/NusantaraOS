#!/bin/bash

# =============================================
# NusantaraOS - Hardware Detection Script
# Dijalanin sebelum display manager start
# Lebih cepat dari Python — cocok buat early boot
# =============================================

LOG="/tmp/nusantara-hw.log"
echo "[$(date)] hw-detect.sh mulai jalan..." | tee -a $LOG

# --- Deteksi GPU ---
echo "[$(date)] Mencari GPU..." | tee -a $LOG

GPU_INFO=$(lspci | grep -i 'VGA\|Display\|3D')

if echo "$GPU_INFO" | grep -qi 'nvidia'; then
    VENDOR="nvidia"
    echo "[$(date)] GPU: NVIDIA ditemukan" | tee -a $LOG

elif echo "$GPU_INFO" | grep -qi 'intel'; then
    VENDOR="intel"
    echo "[$(date)] GPU: Intel ditemukan — pakai driver iris" | tee -a $LOG

elif echo "$GPU_INFO" | grep -qi 'amd\|ati'; then
    VENDOR="amd"
    echo "[$(date)] GPU: AMD ditemukan — pakai driver amdgpu" | tee -a $LOG

else
    VENDOR="unknown"
    echo "[$(date)] GPU: Tidak dikenal — fallback ke llvmpipe" | tee -a $LOG
fi

# --- Load driver sesuai vendor ---
echo "[$(date)] Memuat driver untuk: $VENDOR" | tee -a $LOG

case $VENDOR in
    intel)
        modprobe i915 2>/dev/null && \
        echo "[$(date)] Driver i915 berhasil dimuat" | tee -a $LOG || \
        echo "[$(date)] Driver i915 gagal — pakai llvmpipe" | tee -a $LOG
        ;;
    amd)
        modprobe amdgpu 2>/dev/null && \
        echo "[$(date)] Driver amdgpu berhasil dimuat" | tee -a $LOG || \
        echo "[$(date)] Driver amdgpu gagal — pakai llvmpipe" | tee -a $LOG
        ;;
    nvidia)
        modprobe nvidia 2>/dev/null && \
        echo "[$(date)] Driver nvidia berhasil dimuat" | tee -a $LOG || \
        echo "[$(date)] Driver nvidia gagal — pakai llvmpipe" | tee -a $LOG
        ;;
    *)
        echo "[$(date)] Vendor tidak dikenal — llvmpipe aktif" | tee -a $LOG
        ;;
esac

echo "[$(date)] hw-detect.sh selesai — sistem siap" | tee -a $LOG
