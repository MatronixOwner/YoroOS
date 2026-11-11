#!/usr/bin/env python3
"""CI-only investigation of Live user/session. Never ship the debug kernel arg."""
import base64
import select
import socket
import subprocess
import sys
import time
from pathlib import Path

root = Path(sys.argv[1]).resolve()
expect_desktop = '--expect-desktop' in sys.argv[2:]
iso = root / 'yoroos-desktop-amd64.iso'
kernels = list((root / 'live').glob('vmlinuz-*'))
initrds = list((root / 'live').glob('initrd.img-*'))
if len(kernels) != 1 or len(initrds) != 1:
    raise SystemExit('Expected one kernel and one initrd')
serial_log = root / 'serial.log'
debug_sock = root / 'debug.sock'
qemu = subprocess.Popen([
    'qemu-system-x86_64', '-machine', 'q35', '-accel', 'tcg', '-m', '3072', '-smp', '2',
    '-kernel', str(kernels[0]), '-initrd', str(initrds[0]),
    '-append', 'boot=live components username=yoro hostname=yoroos console=tty0 console=ttyS0,115200n8 systemd.debug_shell=ttyS1',
    '-cdrom', str(iso), '-boot', 'd', '-display', 'none', '-monitor', 'none',
    '-serial', 'file:' + str(serial_log),
    '-serial', 'unix:' + str(debug_sock) + ',server=on,wait=off', '-no-reboot',
], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        if qemu.poll() is not None:
            raise RuntimeError('QEMU exited: ' + qemu.stdout.read())
        if serial_log.exists() and b'graphical.target' in serial_log.read_bytes():
            break
        time.sleep(3)
    else:
        raise RuntimeError('Timed out before graphical target')
    time.sleep(25)  # SDDM starts asynchronously after the graphical target.
    sock = socket.socket(socket.AF_UNIX)
    sock.connect(str(debug_sock))
    sock.setblocking(False)
    cmd = r"""
echo YORO_DIAGNOSTIC_BEGIN
if getent passwd yoro >/dev/null; then
    for i in $(seq 1 90); do
        pgrep -u yoro -x plasmashell >/dev/null && break
        sleep 2
    done
fi
echo USER_DETAILS
getent passwd yoro || true
passwd -S yoro || true
ls -la /usr/share/xsessions/
for f in /etc/sddm.conf /etc/sddm.conf.d/*; do echo FILE:$f; cat "$f" 2>/dev/null || true; done
echo SDDM_JOURNAL
journalctl --no-pager -b -u sddm || true
echo LIVE_CONFIG
journalctl --no-pager -b -u live-config | tail -80
echo SESSION_LOGS
find /home/yoro -maxdepth 5 -name '*session*log*' -exec cat {} \; 2>/dev/null || true
echo PROCESSES
ps ax -o user=,args= | grep -E 'sddm|plasmashell|kwin' | grep -v grep || true
if id yoro >/dev/null 2>&1 && pgrep -u yoro -x plasmashell >/dev/null; then
    echo YORO_DESKTOP_RUNNING
else
    echo YORO_DESKTOP_NOT_RUNNING
fi
echo YORO_DIAGNOSTIC_END
"""
    # Base64 prevents the echoed input line from resembling output markers.
    encoded = base64.b64encode(cmd.encode()).decode()
    sock.sendall(('echo ' + encoded + ' | base64 -d | /bin/sh\n').encode())
    data = b''
    until = time.monotonic() + 240
    while time.monotonic() < until:
        readable, _, _ = select.select([sock], [], [], 1)
        if readable:
            chunk = sock.recv(65536)
            if not chunk:
                break
            data += chunk
            if b'\r\nYORO_DIAGNOSTIC_END\r\n' in data:
                break
    text = data.decode('utf-8', 'replace')
    print(text)
    if b'\r\nYORO_DIAGNOSTIC_END\r\n' not in data:
        raise RuntimeError('Debug shell did not complete diagnosis')
    if expect_desktop and b'\r\nYORO_DESKTOP_RUNNING\r\n' not in data:
        raise RuntimeError('The live user or Plasma desktop did not start')

finally:
    qemu.terminate()
    try:
        qemu.wait(timeout=10)
    except subprocess.TimeoutExpired:
        qemu.kill()
        qemu.wait()
