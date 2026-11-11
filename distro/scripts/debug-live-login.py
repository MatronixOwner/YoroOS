#!/usr/bin/env python3
"""CI-only investigation of Live user/session. Never ship the debug kernel arg."""
import base64
import select
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

root = Path(sys.argv[1]).resolve()
expect_desktop = '--expect-desktop' in sys.argv[2:]
expect_browser = '--expect-browser' in sys.argv[2:]
iso = root / 'yoroos-desktop-amd64.iso'
kernels = list((root / 'live').glob('vmlinuz-*'))
initrds = list((root / 'live').glob('initrd.img-*'))
if len(kernels) != 1 or len(initrds) != 1:
    raise SystemExit('Expected one kernel and one initrd')
serial_log = root / 'serial.log'
debug_sock = root / 'debug.sock'
qemu = subprocess.Popen([
    'qemu-system-x86_64', '-machine', 'q35', '-accel', 'tcg', '-m', '4096', '-smp', '2',
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
        if serial_log.exists() and re.search(rb'Reached target[^\n]*graphical\.target', serial_log.read_bytes()):
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
hash=$(getent shadow yoro | cut -d: -f2)
if [ -n "$hash" ] && perl -e 'exit(crypt("live", $ARGV[0]) eq $ARGV[0] ? 0 : 1)' "$hash"; then
    echo YORO_LIVE_PASSWORD_VALID
else
    echo YORO_LIVE_PASSWORD_INVALID
fi
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
if id yoro >/dev/null 2>&1 && pgrep -u yoro -x plasmashell >/dev/null; then
    pshell=$(pgrep -u yoro -x plasmashell | head -n 1)
    bus=$(tr '\0' '\n' < /proc/$pshell/environ | sed -n 's/^DBUS_SESSION_BUS_ADDRESS=//p' | head -n 1)
    echo "DBUS_SESSION_BUS_ADDRESS=$bus"
    echo PANEL_TEST_START
    for i in $(seq 1 30); do
        [ -f /home/yoro/.config/yoroos/panel-setup-done ] && break
        sleep 2
    done
    ls -l /home/yoro/.config/yoroos/panel-setup-done 2>&1 || true
    runuser -u yoro -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS="$bus" /usr/lib/qt6/bin/qdbus org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript 'var result=[]; var p=panels(); for (var i=0; i<p.length; ++i) { var w=p[i].widgets(); var names=[]; for(var j=0;j<w.length;++j) names.push(w[j].type); result.push(p[i].location+":"+names.join(",")); } print("YORO_PANELS="+result.join(";"));' 2>&1 || true
    echo BROWSER_TEST_START
    pshell=$(pgrep -u yoro -x plasmashell | head -n 1)
    display=$(tr '\0' '\n' < /proc/$pshell/environ | sed -n 's/^DISPLAY=//p' | head -n 1)
    xauth=$(tr '\0' '\n' < /proc/$pshell/environ | sed -n 's/^XAUTHORITY=//p' | head -n 1)
    display=${display:-:0}
    xauth=${xauth:-/home/yoro/.Xauthority}
    echo "DISPLAY=$display XAUTHORITY=$xauth"
    printf %s '__MATRONIX_TEST__' | base64 -d > /tmp/yoro-matronix-smoke.py
    chmod 644 /tmp/yoro-matronix-smoke.py
    if timeout 110 runuser -u yoro -- env DISPLAY="$display" XAUTHORITY="$xauth" XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS="$bus" PYTHONFAULTHANDLER=1 PYTHONUNBUFFERED=1 /usr/bin/python3 /tmp/yoro-matronix-smoke.py >/tmp/matronix-test.log 2>&1; then
        cat /tmp/matronix-test.log
        echo YORO_BROWSER_OK
    else
        cat /tmp/matronix-test.log
        echo YORO_BROWSER_FAILED
    fi
fi
echo YORO_DIAGNOSTIC_END
"""
    smoke = Path(__file__).with_name('matronix-smoke.py').read_bytes()
    cmd = cmd.replace('__MATRONIX_TEST__', base64.b64encode(smoke).decode())
    # Base64 prevents the echoed input line from resembling output markers.
    encoded = base64.b64encode(cmd.encode()).decode()
    sock.sendall(('echo ' + encoded + ' | base64 -d | /bin/sh\n').encode())
    data = b''
    until = time.monotonic() + 390
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
    if expect_desktop and b'\r\nYORO_LIVE_PASSWORD_VALID\r\n' not in data:
        raise RuntimeError('The expected Live fallback password is not valid')
    if expect_browser and b'\r\nYORO_BROWSER_OK\r\n' not in data:
        raise RuntimeError('Matronix did not start and render the test page')

finally:
    qemu.terminate()
    try:
        qemu.wait(timeout=10)
    except subprocess.TimeoutExpired:
        qemu.kill()
        qemu.wait()
