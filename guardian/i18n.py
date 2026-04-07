#!/usr/bin/env python3
"""
NusantaraOS — Internationalization (i18n)
File: guardian/i18n.py

Load pesan dari localization/messages.json.
Singleton — load sekali, pakai seterusnya.

Cara pakai:
    from i18n import t
    log.info(t("sehat.semua_aman"))
    log.warning(t("sehat.disk_peringatan", persen=91))
    log.info(t("boot.gagal_peringatan", n=2))
"""

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# Lokasi messages.json — relative dari guardian/ ke localization/
_MESSAGES_PATH = Path(__file__).parent.parent / "localization" / "messages.json"

# Fallback kalau file tidak ditemukan
_FALLBACK: dict = {}

# Cache hasil load
_messages: dict | None = None


def _load() -> dict:
    """Load messages.json sekali, cache untuk seterusnya."""
    global _messages
    if _messages is not None:
        return _messages

    try:
        if _MESSAGES_PATH.exists():
            _messages = json.loads(_MESSAGES_PATH.read_text(encoding="utf-8"))
            log.debug(f"Pesan i18n dimuat dari {_MESSAGES_PATH}")
        else:
            log.warning(f"messages.json tidak ditemukan di {_MESSAGES_PATH} — pakai string default")
            _messages = _FALLBACK
    except (json.JSONDecodeError, OSError) as e:
        log.error(f"Gagal load messages.json: {e}")
        _messages = _FALLBACK

    return _messages


def t(key: str, **kwargs) -> str:
    """
    Ambil teks terlokalisasi berdasarkan dot-notation key.

    Contoh:
        t("sehat.semua_aman")
            → "Sistem kamu sehat — tidak ada masalah ditemukan."

        t("sehat.disk_peringatan", persen=91)
            → "Penyimpanan sudah 91% terpakai — mulai bersihkan file yang tidak perlu."

        t("boot.gagal_peringatan", n=2)
            → "Sistem gagal boot 2x — memantau situasi."

    Kalau key tidak ditemukan → return key itu sendiri (tidak crash).
    """
    msgs = _load()
    bagian = key.split(".")

    nilai = msgs
    for b in bagian:
        if isinstance(nilai, dict):
            nilai = nilai.get(b)
        else:
            nilai = None
            break

    if nilai is None:
        log.debug(f"i18n: key '{key}' tidak ditemukan")
        return key  # fallback ke key itu sendiri

    if not isinstance(nilai, str):
        return str(nilai)

    # Substitusi variabel kalau ada kwargs
    if kwargs:
        try:
            nilai = nilai.format(**kwargs)
        except KeyError as e:
            log.debug(f"i18n: variabel {e} tidak tersedia untuk key '{key}'")

    return nilai


def reload():
    """Force reload messages.json (dipanggil setelah file diupdate)."""
    global _messages
    _messages = None
    _load()
    log.info("i18n: messages.json direload")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] %(message)s')

    print("=== Test i18n ===")
    print(t("guardian.aktif"))
    print(t("boot.gagal_peringatan", n=2))
    print(t("sehat.disk_peringatan", persen=91))
    print(t("notifikasi.disk_kritis"))
    print(t("notifikasi.disk_kritis_isi", persen=96))
    print(t("hardware.gpu_intel"))
    print(t("kunci.tidak.ada"))  # fallback test
