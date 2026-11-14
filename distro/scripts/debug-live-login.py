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
monitor_sock = root / 'monitor.sock'
screenshot = root / 'desktop-screen.ppm'
qemu = subprocess.Popen([
    'qemu-system-x86_64', '-machine', 'q35', '-accel', 'tcg', '-m', '4096', '-smp', '2',
    '-kernel', str(kernels[0]), '-initrd', str(initrds[0]),
    '-append', 'boot=live components username=yoro hostname=matroos console=tty0 console=ttyS0,115200n8 systemd.debug_shell=ttyS1',
    '-cdrom', str(iso), '-boot', 'd', '-display', 'none',
    '-monitor', 'unix:' + str(monitor_sock) + ',server=on,wait=off',
    '-serial', 'file:' + str(serial_log),
    '-serial', 'unix:' + str(debug_sock) + ',server=on,wait=off', '-no-reboot',
], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        if qemu.poll() is not None:
            raise RuntimeError('QEMU exited: ' + qemu.stdout.read())
        if serial_log.exists():
            boot_log = serial_log.read_bytes()
            # Plymouth suppresses systemd status on the serial console.
            # The login prompt only proves userspace reached a getty; below we
            # independently require Plasma, welcome, terminal and browser.
            if re.search(rb'Reached target[^\n]*graphical\.target|matroos login:', boot_log):
                break
        time.sleep(3)
    else:
        raise RuntimeError('Timed out before userspace login or graphical target')
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
    echo WELCOME_TEST_START
    for i in $(seq 1 30); do
        [ -f /home/yoro/.config/yoroos/welcome-seen ] && pgrep -u yoro -f 'python3 -m yoroapps.welcome' >/dev/null && break
        sleep 2
    done
    if [ -f /home/yoro/.config/yoroos/welcome-seen ] && pgrep -u yoro -f 'python3 -m yoroapps.welcome' >/dev/null; then
        echo YORO_WELCOME_OK
    else
        echo YORO_WELCOME_FAILED
    fi
    echo COMPOSITOR_TEST_START
    dpkg-query -W libgl1-mesa-dri libglx-mesa0 libegl-mesa0 2>&1 || true
    echo KWIN_CONFIG
    cat /home/yoro/.config/kwinrc || true
    echo KWIN_INFO
    runuser -u yoro -- env LANG=C.UTF-8 XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS="$bus" /usr/lib/qt6/bin/qdbus org.kde.KWin /KWin org.kde.KWin.supportInformation 2>&1 || true
    echo COMPOSITOR_PROPERTIES
    for prop in active compositingPossible compositingNotPossibleReason compositingType; do echo PROP:$prop; runuser -u yoro -- env LANG=C.UTF-8 XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS="$bus" /usr/lib/qt6/bin/qdbus org.kde.KWin /Compositor org.kde.kwin.Compositing.$prop 2>&1 || true; done
    echo XORG_LOG
    grep -iE 'glx|dri|error|render' /var/log/Xorg.0.log /home/yoro/.local/share/xorg/Xorg.0.log 2>/dev/null || true
    echo KWIN_LOADED_EFFECTS
    runuser -u yoro -- env LANG=C.UTF-8 XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS="$bus" /usr/lib/qt6/bin/qdbus org.kde.KWin /Effects org.kde.kwin.Effects.loadedEffects 2>&1 || true
    for effect in blur magiclamp kwin4_effect_magiclamp scale kwin4_effect_scale; do
        echo "EFFECT:$effect"
        runuser -u yoro -- env LANG=C.UTF-8 XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS="$bus" /usr/lib/qt6/bin/qdbus org.kde.KWin /Effects org.kde.kwin.Effects.isEffectLoaded "$effect" 2>&1 || true
    done
    echo BROWSER_TEST_START
    pshell=$(pgrep -u yoro -x plasmashell | head -n 1)
    display=$(tr '\0' '\n' < /proc/$pshell/environ | sed -n 's/^DISPLAY=//p' | head -n 1)
    xauth=$(tr '\0' '\n' < /proc/$pshell/environ | sed -n 's/^XAUTHORITY=//p' | head -n 1)
    display=${display:-:0}
    xauth=${xauth:-/home/yoro/.Xauthority}
    echo "DISPLAY=$display XAUTHORITY=$xauth"
    printf %s '__TERMINAL_TEST__' | base64 -d > /tmp/yoro-terminal-smoke.py
    chmod 644 /tmp/yoro-terminal-smoke.py
    if timeout 90 runuser -u yoro -- env DISPLAY="$display" XAUTHORITY="$xauth" XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS="$bus" PYTHONUNBUFFERED=1 /usr/bin/python3 /tmp/yoro-terminal-smoke.py >/tmp/terminal-test.log 2>&1; then
        cat /tmp/terminal-test.log
    else
        cat /tmp/terminal-test.log
        echo YORO_TERMINAL_FAILED
    fi
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
    terminal_smoke = Path(__file__).with_name('terminal-smoke.py').read_bytes()
    cmd = cmd.replace('__TERMINAL_TEST__', base64.b64encode(terminal_smoke).decode())
    # Base64 prevents the echoed input line from resembling output markers.
    encoded = base64.b64encode(cmd.encode()).decode()
    sock.sendall(('echo ' + encoded + ' | base64 -d | /bin/sh\n').encode())
    data = b''
    captured = False
    until = time.monotonic() + 650
    while time.monotonic() < until:
        readable, _, _ = select.select([sock], [], [], 1)
        if readable:
            chunk = sock.recv(65536)
            if not chunk:
                break
            data += chunk
            if not captured and b'\r\nYORO_SCREENSHOT_READY\r\n' in data:
                captured = True
                try:
                    with socket.socket(socket.AF_UNIX) as monitor:
                        monitor.settimeout(10)
                        monitor.connect(str(monitor_sock))
                        monitor.recv(4096)
                        monitor.sendall(('screendump ' + str(screenshot) + '\n').encode())
                        time.sleep(3)
                except OSError as exc:
                    print('Screenshot failed:', exc, flush=True)
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
    if expect_desktop and b'\r\nYORO_WELCOME_OK\r\n' not in data:
        raise RuntimeError('Yoro welcome did not appear on first login')
    if expect_desktop and b'\r\nYORO_TERMINAL_OK\r\n' not in data:
        raise RuntimeError('Yoro terminal did not start an interactive shell')
    if expect_desktop and 'Theme: __aurorae__svg__YoroArc' not in text:
        raise RuntimeError('Yoro Arc window decoration was not loaded')
    if expect_desktop:
        for effect in ('magiclamp', 'scale'):
            if not re.search(r'EFFECT:' + effect + r'\r?\ntrue\r?\n', text):
                raise RuntimeError(f'Expected window effect not loaded: {effect}')
    if expect_desktop and not re.search(r'EFFECT:blur\r?\nfalse\r?\n', text):
        raise RuntimeError('KWin blur should be disabled')
    if expect_browser and b'\r\nYORO_BROWSER_OK\r\n' not in data:
        raise RuntimeError('Matronix did not start and render the test page')

finally:
    qemu.terminate()
    try:
        qemu.wait(timeout=10)
    except subprocess.TimeoutExpired:
        qemu.kill()
        qemu.wait()
