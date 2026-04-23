#!/bin/bash

# =============================================
# NusantaraOS - Hardware Detection Script
# Dijalanin sebelum display manager start
# Lebih cepat dari Python — cocok buat early boot
# =============================================

LOG_DIR="/var/log/nusantara"
STATE_DIR="/var/lib/nusantara"
LOG="$LOG_DIR/hw-detect.log"

# Buat direktori kalau belum ada
mkdir -p "$LOG_DIR" "$STATE_DIR"

echo "[$(date)] hw-detect.sh mulai jalan..." | tee -a "$LOG"

# --- Deteksi GPU ---
echo "[$(date)] Mencari GPU..." | tee -a "$LOG"

GPU_INFO=$(lspci | grep -i 'VGA\|Display\|3D')
GPU_MODEL=$(lspci 2>/dev/null | grep -i 'VGA\|Display\|3D' | head -1 | sed 's/.*: //')
PCI_ID=$(lspci -n 2>/dev/null | awk '/0300|0302/ {print $3; exit}')
[ -z "$PCI_ID" ] && PCI_ID="—"
[ -z "$GPU_MODEL" ] && GPU_MODEL="Tidak terdeteksi"

if echo "$GPU_INFO" | grep -qi 'nvidia'; then
    VENDOR="nvidia"
    DRIVER="nvidia"
    echo "[$(date)] GPU: NVIDIA ditemukan" | tee -a "$LOG"

elif echo "$GPU_INFO" | grep -qi 'intel'; then
    VENDOR="intel"
    DRIVER="i915"
    echo "[$(date)] GPU: Intel ditemukan — pakai driver iris/i915" | tee -a "$LOG"

elif echo "$GPU_INFO" | grep -qi 'amd\|ati'; then
    VENDOR="amd"
    DRIVER="amdgpu"
    echo "[$(date)] GPU: AMD ditemukan — pakai driver amdgpu" | tee -a "$LOG"

else
    VENDOR="unknown"
    DRIVER="llvmpipe"
    echo "[$(date)] GPU: Tidak dikenal — fallback ke llvmpipe" | tee -a "$LOG"
fi

# --- Load driver sesuai vendor ---
echo "[$(date)] Memuat driver untuk: $VENDOR ($DRIVER)" | tee -a "$LOG"

USING_LLVMPIPE="false"

case $VENDOR in
    intel)
        if modprobe i915 2>/dev/null; then
            echo "[$(date)] Driver i915 berhasil dimuat" | tee -a "$LOG"
        else
            echo "[$(date)] Driver i915 gagal — pakai llvmpipe" | tee -a "$LOG"
            USING_LLVMPIPE="true"
            DRIVER="llvmpipe"
        fi
        ;;
    amd)
        if modprobe amdgpu 2>/dev/null; then
            echo "[$(date)] Driver amdgpu berhasil dimuat" | tee -a "$LOG"
        else
            echo "[$(date)] Driver amdgpu gagal — pakai llvmpipe" | tee -a "$LOG"
            USING_LLVMPIPE="true"
            DRIVER="llvmpipe"
        fi
        ;;
    nvidia)
        if modprobe nvidia 2>/dev/null; then
            echo "[$(date)] Driver nvidia berhasil dimuat" | tee -a "$LOG"
        else
            echo "[$(date)] Driver nvidia gagal — pakai llvmpipe" | tee -a "$LOG"
            USING_LLVMPIPE="true"
            DRIVER="llvmpipe"
        fi
        ;;
    *)
        echo "[$(date)] Vendor tidak dikenal — llvmpipe aktif" | tee -a "$LOG"
        USING_LLVMPIPE="true"
        ;;
esac

# --- Tulis hw-state.json ---
# File ini dibaca oleh health_monitor.py, driver_manager_ui.py, welcome_screen.py
TIMESTAMP=$(date -Iseconds)
cat > "$STATE_DIR/hw-state.json" << EOF
{
  "gpu_vendor": "$VENDOR",
  "gpu_model": "$GPU_MODEL",
  "pci_id": "$PCI_ID",
  "driver": "$DRIVER",
  "using_llvmpipe": $USING_LLVMPIPE,
  "last_seen_pci_id": "$PCI_ID",
  "last_updated": "$TIMESTAMP"
}
EOF

echo "[$(date)] hw-state.json ditulis ke $STATE_DIR/hw-state.json" | tee -a "$LOG"
echo "[$(date)] hw-detect.sh selesai — sistem siap" | tee -a "$LOG"

