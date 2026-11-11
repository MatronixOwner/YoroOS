#!/bin/bash
# UEFI boot smoke test. This checks Linux and a display-manager/graphical target,
# not a usable Plasma session or Hyper-V synthetic hardware.
set -euo pipefail
iso=${1:?usage: qemu-live-smoke.sh image.iso}
log=${2:-out/uefi-serial.log}
firmware=/usr/share/OVMF/OVMF_CODE_4M.fd
[ -f "$firmware" ] || firmware=/usr/share/OVMF/OVMF_CODE.fd
[ -f "$firmware" ] || { echo 'OVMF firmware missing' >&2; exit 1; }
mkdir -p "$(dirname "$log")"
rm -f "$log"
qemu-system-x86_64 -machine q35 -accel tcg -m 3072 -smp 2 \
  -drive "if=pflash,format=raw,readonly=on,file=$firmware" \
  -cdrom "$iso" -boot d -vga std -display none -monitor none \
  -serial "file:$log" -no-reboot >"${log}.qemu" 2>&1 &
pid=$!
cleanup() { kill "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true; }
trap cleanup EXIT
for ((i=0; i<72; i++)); do
    if [ -f "$log" ] && grep -aEiq 'Reached target.*(graphical|Graphical)|Started.*(Simple Desktop Display Manager|sddm)' "$log"; then
        echo 'UEFI smoke test: display manager or graphical.target reached (Plasma session not verified).'
        exit 0
    fi
    if ! kill -0 "$pid" 2>/dev/null; then echo 'QEMU exited before desktop target' >&2; break; fi
    sleep 5
done
echo 'UEFI smoke test failed: no display-manager/graphical-target marker.' >&2
tail -n 100 "$log" 2>/dev/null || true
cat "${log}.qemu" 2>/dev/null || true
exit 1
