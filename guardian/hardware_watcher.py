#!/usr/bin/env python3

# =============================================
# NusantaraOS - Hardware Watcher
# Tugasnya: deteksi GPU yang ada di sistem
# dan deteksi kalau GPU diganti user
# =============================================

import json
import subprocess
import logging
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

# HW_STATE_PATH — baca dari config kalau tersedia, fallback ke default
try:
    from config import get_config
    _cfg = get_config()
    HW_STATE_PATH = _cfg.state_dir / "hw-state.json"
except ImportError:
    HW_STATE_PATH = Path("/var/lib/nusantara/hw-state.json")

# Map driver aktif berdasarkan vendor
DRIVER_MAP = {
    'nvidia': 'nvidia',
    'intel':  'i915',
    'amd':    'amdgpu',
}


def cek_perubahan_gpu(pci_id_sekarang: str) -> bool:
    """
    Cek apakah GPU sudah diganti sejak boot sebelumnya.
    Bandingkan pci_id_sekarang dengan last_seen_pci_id di hw-state.json.

    Return True kalau GPU berubah → Guardian akan trigger setup wizard.
    """
    if not HW_STATE_PATH.exists():
        return False  # Belum ada state sebelumnya — bukan perubahan

    try:
        data = json.loads(HW_STATE_PATH.read_text())
        pci_id_lama = data.get("last_seen_pci_id", "")

        if pci_id_lama and pci_id_lama != "—" and pci_id_lama != pci_id_sekarang:
            log.warning(
                f"GPU BERUBAH! Sebelumnya: {pci_id_lama} → Sekarang: {pci_id_sekarang}"
            )
            return True
    except (json.JSONDecodeError, OSError) as e:
        log.error(f"Gagal baca hw-state untuk cek perubahan GPU: {e}")

    return False


def _ambil_nama_gpu() -> str:
    """Ekstrak nama model GPU dari output lspci."""
    try:
        hasil = subprocess.run(['lspci', '-v'], capture_output=True, text=True)
        for line in hasil.stdout.split('\n'):
            if 'VGA' in line or 'Display' in line or '3D' in line:
                # Format: "00:02.0 VGA compatible controller: Intel Corporation ..."
                bagian = line.split(':', 2)
                if len(bagian) >= 3:
                    return bagian[2].strip()
        return "Tidak terdeteksi"
    except Exception:
        return "Tidak terdeteksi"


def _ambil_pci_id() -> str:
    """Ambil PCI ID GPU dalam format vendor:device."""
    try:
        hasil = subprocess.run(['lspci', '-n'], capture_output=True, text=True)
        for line in hasil.stdout.split('\n'):
            if '0300' in line or '0302' in line:  # VGA / 3D controller class
                bagian = line.split()
                if len(bagian) >= 3:
                    return bagian[2]
        return "—"
    except Exception:
        return "—"


def tulis_hw_state(vendor: str, gpu_model: str, pci_id: str,
                   driver: str, using_llvmpipe: bool = False):
    """
    Tulis hasil deteksi hardware ke JSON.
    Dibaca oleh health_monitor.py, driver_manager_ui.py, dan welcome_screen.py.
    """
    state = {
        "gpu_vendor":       vendor or "unknown",
        "gpu_model":        gpu_model,
        "pci_id":           pci_id,
        "driver":           driver,
        "using_llvmpipe":   using_llvmpipe,
        "last_seen_pci_id": pci_id,
        "last_updated":     datetime.now().isoformat(),
    }
    try:
        HW_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        HW_STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False))
        log.info(f"hw-state ditulis ke {HW_STATE_PATH}")
    except Exception as e:
        log.error(f"Gagal tulis hw-state: {e}")


def deteksi_gpu() -> str | None:
    log.info("Lagi ngecek GPU yang ada di sistem...")

    try:
        hasil = subprocess.run(['lspci'], capture_output=True, text=True)
        semua_hardware = hasil.stdout.split('\n')
        gpu_ditemukan = []

        for hardware in semua_hardware:
            if 'VGA' in hardware or 'Display' in hardware or '3D' in hardware:
                gpu_ditemukan.append(hardware)

        if gpu_ditemukan:
            for gpu in gpu_ditemukan:
                log.info(f"GPU ditemukan: {gpu}")
                gpu_upper = gpu.upper()

                if 'NVIDIA' in gpu_upper:
                    log.info("Vendor: NVIDIA — perlu driver khusus")
                    vendor = 'nvidia'
                elif 'INTEL' in gpu_upper:
                    log.info("Vendor: Intel — pakai driver iris/xe")
                    vendor = 'intel'
                elif 'AMD' in gpu_upper or 'ATI' in gpu_upper:
                    log.info("Vendor: AMD — pakai driver amdgpu")
                    vendor = 'amd'
                else:
                    log.info("Vendor: Tidak dikenal — pakai llvmpipe")
                    vendor = 'unknown'

                # Cek apakah driver hardware berhasil load
                driver = DRIVER_MAP.get(vendor, 'unknown')
                using_llvmpipe = vendor == 'unknown'

                try:
                    hasil_lsmod = subprocess.run(
                        ['lsmod'], capture_output=True, text=True
                    )
                    modul_dimuat = hasil_lsmod.stdout
                    if driver != 'unknown' and driver not in modul_dimuat:
                        log.warning(f"Driver {driver} tidak ada di lsmod — llvmpipe aktif")
                        using_llvmpipe = True
                except Exception:
                    pass

                # Ambil detail GPU
                gpu_model = _ambil_nama_gpu()
                pci_id    = _ambil_pci_id()

                # Tulis state — inilah yang dibaca oleh GUI dan health_monitor
                tulis_hw_state(vendor, gpu_model, pci_id, driver, using_llvmpipe)

                return vendor
        else:
            log.warning("Gak ada GPU yang ketemu!")
            tulis_hw_state('unknown', 'Tidak terdeteksi', '—', 'llvmpipe', True)
            return None

    except Exception as e:
        log.error(f"Error waktu deteksi GPU: {e}")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
    log.info("Test Hardware Watcher...")
    gpu = deteksi_gpu()
    log.info(f"Hasil akhir: GPU vendor = {gpu}")
    log.info(f"hw-state.json ditulis ke: {HW_STATE_PATH}")
