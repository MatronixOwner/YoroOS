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
rm -f "$log" "${log}.monitor" "${log}.ppm"
monitor="${log}.monitor"
qemu-system-x86_64 -machine q35 -accel tcg -m 3072 -smp 2 \
  -drive "if=pflash,format=raw,readonly=on,file=$firmware" \
  -cdrom "$iso" -boot d -vga std -display none -monitor "unix:$monitor,server=on,wait=off" \
  -serial "file:$log" -no-reboot >"${log}.qemu" 2>&1 &
pid=$!
cleanup() { kill "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true; }
trap cleanup EXIT
for ((i=0; i<72; i++)); do
    # Select the default GRUB entry also on older images with no timeout.
    if [ "$i" -eq 8 ]; then
        python3 - "$monitor" <<'PYKEY'
import socket, sys
try:
    s = socket.socket(socket.AF_UNIX)
    s.connect(sys.argv[1])
    s.sendall(b'sendkey ret\n')
    s.close()
except OSError as exc:
    print('Could not send GRUB selection:', exc)
PYKEY
    fi
    if [ "$i" -eq 6 ]; then
        python3 - "$monitor" "$(dirname "$log")/boot-screen.ppm" <<'PYSHOT'
import socket, sys, time
try:
    with socket.socket(socket.AF_UNIX) as s:
        s.connect(sys.argv[1]); s.sendall(('screendump ' + sys.argv[2] + '\n').encode()); time.sleep(1)
except OSError as exc:
    print('Boot screenshot unavailable:', exc)
PYSHOT
    fi
    if [ -f "$log" ] && grep -aEiq 'Reached target.*(graphical|Graphical)|Started.*(Simple Desktop Display Manager|sddm)' "$log"; then
        echo 'UEFI smoke test: display manager or graphical.target reached (Plasma session not verified).'
        exit 0
    fi
    # With Plymouth, systemd suppresses progress on the serial console.
    # A getty login prompt proves userspace is running; the next QEMU test
    # separately checks the actual Plasma session, apps and effects.
    if [ -f "$log" ] && grep -aq 'matroos login:' "$log"; then
        echo 'UEFI smoke test: login prompt reached (desktop checked separately).'
        exit 0
    fi
    if ! kill -0 "$pid" 2>/dev/null; then echo 'QEMU exited before desktop target' >&2; break; fi
    sleep 5
done
# Save the VGA screen as well: GRUB and firmware do not necessarily log to
# serial. OCR is diagnostic only, never a successful boot criterion.
python3 - "$monitor" "${log}.ppm" <<'PYMON'
import socket, sys, time
try:
    s = socket.socket(socket.AF_UNIX)
    s.connect(sys.argv[1])
    s.sendall(('screendump ' + sys.argv[2] + '\n').encode())
    time.sleep(2)
    s.close()
except OSError as exc:
    print('Cannot capture VGA screen:', exc)
PYMON
if command -v tesseract >/dev/null && [ -s "${log}.ppm" ]; then
    echo 'VGA screen OCR (diagnostic only):'
    tesseract "${log}.ppm" stdout 2>/dev/null || true
fi
echo 'UEFI smoke test failed: no display-manager/graphical-target marker.' >&2
tail -n 100 "$log" 2>/dev/null || true
cat "${log}.qemu" 2>/dev/null || true
exit 1
