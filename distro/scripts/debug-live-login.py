#!/usr/bin/env python3
"""CI-only investigation of Live user/session. Never ship the debug kernel arg."""
import os
import select
import socket
import subprocess
import sys
import time
from pathlib import Path

root = Path(sys.argv[1]).resolve()
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
    time.sleep(35)  # SDDM starts asynchronously; allow time for session failure.
    sock = socket.socket(socket.AF_UNIX)
    sock.connect(str(debug_sock))
    sock.setblocking(False)
    cmd = """echo YORO_DIAGNOSTIC_BEGIN; date; getent passwd yoro; passwd -S yoro; ls -la /usr/share/xsessions/; for f in /etc/sddm.conf /etc/sddm.conf.d/*; do echo FILE:$f; cat $f 2>/dev/null; done; echo SDDM_JOURNAL; journalctl --no-pager -b -u sddm; echo LIVE_CONFIG; journalctl --no-pager -b -u live-config | tail -80; echo SESSION_LOGS; find /home/yoro -maxdepth 5 -name '*session*log*' -exec cat {} \\; 2>/dev/null; echo PROCESSES; ps ax -o user=,args= | grep -E 'sddm|plasmashell|kwin' | grep -v grep; echo YORO_DIAGNOSTIC_END\n"""
    sock.sendall(cmd.encode())
    data = b''
    until = time.monotonic() + 60
    while time.monotonic() < until:
        readable, _, _ = select.select([sock], [], [], 1)
        if readable:
            chunk = sock.recv(65536)
            if not chunk:
                break
            data += chunk
            if b'YORO_DIAGNOSTIC_END\r\n' in data:
                break
    print(data.decode('utf-8', 'replace'))
    if b'YORO_DIAGNOSTIC_END' not in data:
        raise RuntimeError('Debug shell did not respond')
finally:
    qemu.terminate()
    try:
        qemu.wait(timeout=10)
    except subprocess.TimeoutExpired:
        qemu.kill()
        qemu.wait()
