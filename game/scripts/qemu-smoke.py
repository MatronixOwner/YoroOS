#!/usr/bin/env python3
"""Boot a disposable CI-only Game disk under UEFI, check serial login.

This checks boot and the display manager service, not a graphical session,
Hyper-V, game performance, installation or update reliability.
"""
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import time

image = Path(sys.argv[1]).resolve()
vars_file = Path('game-ci-ovmf-vars.fd').resolve()
shutil.copyfile('/usr/share/OVMF/OVMF_VARS.fd', vars_file)
cmd = ['qemu-system-x86_64', '-machine', 'q35,accel=tcg', '-cpu', 'max',
       '-m', '4096', '-smp', '2', '-display', 'none', '-no-reboot',
       '-drive', 'if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE.fd',
       '-drive', f'if=pflash,format=raw,file={vars_file}',
       '-drive', f'file={image},if=virtio,format=qcow2,cache=unsafe',
       '-device', 'virtio-vga', '-serial', 'stdio', '-monitor', 'none', '-net', 'none']
process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
output = bytearray()
state = 'login'
start = time.monotonic()
check = ("if test -x /usr/bin/yoro-files && test -x /usr/bin/matronix-browser "
         "&& test -f /usr/share/applications/steam.desktop "
         "&& grep -q 'MatroOS Game' /usr/lib/os-release "
         "&& timeout 90 sh -c 'until systemctl is-active --quiet display-manager.service; do sleep 3; done'; "
         "then echo MATRO_GAME_BOOT_OK; else echo MATRO_GAME_BOOT_FAILED; fi\n")
try:
    while time.monotonic() - start < 900 and process.poll() is None:
        if not select.select([process.stdout], [], [], 2)[0]:
            continue
        data = os.read(process.stdout.fileno(), 65536)
        if not data:
            break
        output.extend(data)
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
        recent = bytes(output[-6000:])
        if state == 'login' and b'login:' in recent:
            process.stdin.write(b'game-ci\n'); process.stdin.flush(); state = 'password'; output.clear()
        elif state == 'password' and b'Password:' in recent:
            process.stdin.write(b'ci-only-do-not-use\n'); process.stdin.flush(); state = 'shell'; output.clear()
        elif state == 'shell' and (b'$ ' in recent or b'# ' in recent):
            process.stdin.write(check.encode()); process.stdin.flush(); state = 'verify'; output.clear()
        elif state == 'verify' and b'\r\nMATRO_GAME_BOOT_OK\r\n' in recent:
            print('\nUEFI disk boot, serial login and display-manager service verified.')
            sys.exit(0)
        elif state == 'verify' and b'\r\nMATRO_GAME_BOOT_FAILED\r\n' in recent:
            raise RuntimeError('Guest validation failed')
    raise RuntimeError(f'Guest smoke test did not complete, last state: {state}')
finally:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    vars_file.unlink(missing_ok=True)
