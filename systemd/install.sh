#!/bin/bash

# =============================================
# NusantaraOS — Install Guardian Services
# Jalankan sebagai root: sudo bash install.sh
# =============================================

set -e  # keluar langsung kalau ada error

# Warna
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[ OK ]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERR ]${NC} $1"; }

# ── Cek root ──────────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    log_error "Script ini harus dijalankan sebagai root"
    echo "  Jalankan: sudo bash install.sh"
    exit 1
fi

# ── Tentukan direktori sumber ─────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

log_info "Direktori repo: $REPO_DIR"

# ── Buat direktori yang dibutuhkan ────────────────────────────────────────────
log_info "Membuat direktori sistem..."
mkdir -p /usr/lib/nusantara/guardian
mkdir -p /usr/lib/nusantara/gpu-automation
mkdir -p /var/lib/nusantara
mkdir -p /var/log/nusantara
mkdir -p /etc/nusantara
log_ok "Direktori siap"

# ── Copy file Guardian ────────────────────────────────────────────────────────
log_info "Menginstall Guardian daemon..."
cp -r "$REPO_DIR/guardian/"* /usr/lib/nusantara/guardian/
log_ok "Guardian diinstall ke /usr/lib/nusantara/guardian/"

# ── Copy hw-detect.sh ─────────────────────────────────────────────────────────
log_info "Menginstall hardware detection script..."
cp "$REPO_DIR/gpu-automation/hw-detect.sh" /usr/lib/nusantara/gpu-automation/
chmod +x /usr/lib/nusantara/gpu-automation/hw-detect.sh
log_ok "hw-detect.sh diinstall"

# ── Copy konfigurasi ──────────────────────────────────────────────────────────
if [[ ! -f /etc/nusantara/guardian.conf ]]; then
    log_info "Menginstall guardian.conf..."
    cp "$REPO_DIR/etc/nusantara/guardian.conf" /etc/nusantara/ 2>/dev/null || \
    cp /dev/stdin /etc/nusantara/guardian.conf << 'CONF'
[guardian]
interval_cek = 300
log_level = INFO
socket_path = /run/nusantara/guardian.sock
state_dir = /var/lib/nusantara
log_dir = /var/log/nusantara

[health]
disk_warn_pct = 85
disk_crit_pct = 95
ram_warn_pct = 75
ram_crit_pct = 90

[boot]
max_gagal = 2
use_systemd_boot = true
recovery_log = /var/log/nusantara/recovery.log

[smart]
enabled = true
warn_reallocated = 10
crit_pending = 5
CONF
    log_ok "guardian.conf diinstall"
else
    log_warn "guardian.conf sudah ada — tidak ditimpa"
fi

# ── Install systemd services ──────────────────────────────────────────────────
log_info "Menginstall systemd services..."
cp "$SCRIPT_DIR/nusantara-hw-detect.service" /etc/systemd/system/
cp "$SCRIPT_DIR/nusantara-guardian.service"  /etc/systemd/system/

# Update WorkingDirectory di service file agar sesuai lokasi install
sed -i "s|WorkingDirectory=.*|WorkingDirectory=/usr/lib/nusantara/guardian|" \
    /etc/systemd/system/nusantara-guardian.service

systemctl daemon-reload
log_ok "Service files diinstall dan daemon-reload selesai"

# ── Enable services ───────────────────────────────────────────────────────────
log_info "Mengaktifkan services..."
systemctl enable nusantara-hw-detect.service
systemctl enable nusantara-guardian.service
log_ok "Services diaktifkan (akan jalan otomatis saat boot)"

# ── Set permissions ───────────────────────────────────────────────────────────
chmod 755 /var/log/nusantara
chmod 755 /var/lib/nusantara
log_ok "Permissions diset"

# ── Ringkasan ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}=======================================${NC}"
echo -e "${GREEN}  NusantaraOS Guardian TERINSTALL ✅  ${NC}"
echo -e "${GREEN}=======================================${NC}"
echo ""
echo "Perintah berguna:"
echo "  sudo systemctl start nusantara-guardian    # Jalankan sekarang"
echo "  sudo systemctl status nusantara-guardian   # Cek status"
echo "  sudo systemctl stop nusantara-guardian     # Stop daemon"
echo "  journalctl -u nusantara-guardian -f        # Lihat log live"
echo "  journalctl -u nusantara-hw-detect          # Log hardware detection"
echo ""
echo "Config: /etc/nusantara/guardian.conf"
echo "Log:    /var/log/nusantara/guardian.log"
echo "State:  /var/lib/nusantara/"
echo ""

# ── Tanya mau langsung start? ─────────────────────────────────────────────────
read -r -p "Jalankan Guardian sekarang? [Y/n] " JAWAB
JAWAB="${JAWAB:-Y}"
if [[ "$JAWAB" =~ ^[Yy]$ ]]; then
    log_info "Menjalankan nusantara-guardian..."
    systemctl start nusantara-guardian
    sleep 2
    systemctl status nusantara-guardian --no-pager
fi
