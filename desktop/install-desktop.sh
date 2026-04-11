#!/bin/bash
# NusantaraOS — Install Desktop Files
# Jalankan: sudo bash install-desktop.sh

DESKTOP_SRC="$(dirname "$0")"
SYSTEM_APPS="/usr/share/applications"

echo "📦 Install NusantaraOS desktop entries..."

for f in "$DESKTOP_SRC"/*.desktop; do
    name=$(basename "$f")
    cp "$f" "$SYSTEM_APPS/$name"
    chmod 644 "$SYSTEM_APPS/$name"
    echo "  ✓ $name"
done

# Update database
update-desktop-database "$SYSTEM_APPS" 2>/dev/null || true

echo "✅ Semua desktop entries terinstall!"
echo "   Cari di Application Launcher: ketik 'Nusantara'"
