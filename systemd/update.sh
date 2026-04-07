#!/bin/bash

# =============================================
# NusantaraOS — Guardian Update Script
# PRD 5.3: Zero-downtime update procedure
#
# Usage: sudo bash systemd/update.sh [--no-restart]
# =============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[ OK ]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERR ]${NC} $1"; }
log_title() { echo -e "${CYAN}$1${NC}"; }

# ── Parse args ────────────────────────────────────────────────────────────────
NO_RESTART=false
for arg in "$@"; do
    [[ "$arg" == "--no-restart" ]] && NO_RESTART=true
done

# ── Cek root ──────────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    log_error "Harus dijalankan sebagai root: sudo bash systemd/update.sh"
    exit 1
fi

# ── Cek Guardian sudah terinstall ─────────────────────────────────────────────
if [[ ! -d /usr/lib/nusantara/guardian ]]; then
    log_error "Guardian belum terinstall. Jalankan: sudo bash systemd/install.sh"
    exit 1
fi

# ── Tentukan direktori repo ────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

log_title ""
log_title "╔══════════════════════════════════════════╗"
log_title "║  NusantaraOS Guardian — Update Script   ║"
log_title "╚══════════════════════════════════════════╝"
echo ""
log_info "Repo: $REPO_DIR"
log_info "Target: /usr/lib/nusantara/"

# ── Versi sebelum update ──────────────────────────────────────────────────────
VERSI_LAMA=""
if systemctl is-active --quiet nusantara-guardian 2>/dev/null; then
    VERSI_LAMA="aktif"
    log_info "Status sekarang: Guardian sedang berjalan"
else
    VERSI_LAMA="tidak aktif"
    log_warn "Status sekarang: Guardian tidak berjalan"
fi

echo ""

# ── Langkah 1: Backup file lama ───────────────────────────────────────────────
log_info "Langkah 1: Backup file guardian lama..."
BACKUP_DIR="/var/lib/nusantara/backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r /usr/lib/nusantara/guardian/ "$BACKUP_DIR/" 2>/dev/null && \
    log_ok "Backup disimpan di $BACKUP_DIR" || \
    log_warn "Backup gagal — lanjut tanpa backup"

# ── Langkah 2: Update file Python ─────────────────────────────────────────────
log_info "Langkah 2: Update modul Guardian..."
cp -f "$REPO_DIR/guardian/"*.py /usr/lib/nusantara/guardian/
# Hapus .pyc lama agar tidak pakai cache yang sudah usang (PRD: tidak ada stale state)
find /usr/lib/nusantara/guardian -name "*.pyc" -delete 2>/dev/null || true
find /usr/lib/nusantara/guardian -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
log_ok "Modul Python diupdate"

# ── Langkah 3: Update localization ────────────────────────────────────────────
log_info "Langkah 3: Update localization/messages.json..."
mkdir -p /usr/lib/nusantara/localization
cp -f "$REPO_DIR/localization/messages.json" /usr/lib/nusantara/localization/
log_ok "Lokalisasi diupdate"

# ── Langkah 4: Update hw-detect.sh ────────────────────────────────────────────
log_info "Langkah 4: Update GPU detection script..."
cp -f "$REPO_DIR/gpu-automation/hw-detect.sh" /usr/lib/nusantara/gpu-automation/
chmod +x /usr/lib/nusantara/gpu-automation/hw-detect.sh
log_ok "hw-detect.sh diupdate"

# ── Langkah 5: Update config template ─────────────────────────────────────────
log_info "Langkah 5: Cek guardian.conf..."
CONF_SRC="$REPO_DIR/etc/nusantara/guardian.conf"
CONF_DEST="/etc/nusantara/guardian.conf"
if [[ -f "$CONF_SRC" ]]; then
    if [[ -f "$CONF_DEST" ]]; then
        log_warn "guardian.conf sudah ada — tidak ditimpa (edit manual kalau perlu)"
    else
        cp "$CONF_SRC" "$CONF_DEST"
        log_ok "guardian.conf diinstall"
    fi
fi

# ── Langkah 6: Update systemd service files ───────────────────────────────────
log_info "Langkah 6: Update systemd service files..."
cp -f "$SCRIPT_DIR/nusantara-guardian.service"  /etc/systemd/system/
cp -f "$SCRIPT_DIR/nusantara-hw-detect.service" /etc/systemd/system/
systemctl daemon-reload
log_ok "Service files diupdate dan daemon-reload selesai"

# ── Langkah 7: Verifikasi ordering (PRD 5.3) ─────────────────────────────────
log_info "Langkah 7: Verifikasi ordering cycle..."
VERIFY_OUT=$(systemd-analyze verify nusantara-guardian.service nusantara-hw-detect.service 2>&1)
if echo "$VERIFY_OUT" | grep -qi "cycle\|error"; then
    log_error "Ordering cycle terdeteksi:"
    echo "$VERIFY_OUT"
    exit 2
fi
log_ok "Tidak ada ordering cycle ✅"

# ── Langkah 8: Restart Guardian ──────────────────────────────────────────────
echo ""
if [[ "$NO_RESTART" == "true" ]]; then
    log_warn "Flag --no-restart diset — Guardian tidak di-restart"
    log_warn "Jalankan manual: sudo systemctl restart nusantara-guardian"
else
    log_info "Langkah 8: Restart Guardian daemon..."
    systemctl restart nusantara-guardian
    sleep 2

    if systemctl is-active --quiet nusantara-guardian; then
        MEM=$(systemctl show nusantara-guardian --property=MemoryCurrent --value 2>/dev/null | \
              awk '{printf "%.1f MB", $1/1024/1024}')
        log_ok "Guardian aktif kembali (Memory: $MEM)"
    else
        log_error "Guardian gagal start setelah restart!"
        journalctl -u nusantara-guardian --no-pager -n 20
        exit 3
    fi
fi

# ── Selesai ───────────────────────────────────────────────────────────────────
echo ""
log_title "╔══════════════════════════════════════════╗"
log_title "║      Update Selesai ✅                   ║"
log_title "╚══════════════════════════════════════════╝"
echo ""
echo "  Backup lama  : $BACKUP_DIR"
echo "  Config       : /etc/nusantara/guardian.conf"
echo "  Log live     : journalctl -u nusantara-guardian -f"
echo "  Test IPC     : echo '{\"type\":\"GUARDIAN_STATUS\"}' | sudo socat - UNIX-CONNECT:/run/nusantara/guardian.sock"
echo ""
