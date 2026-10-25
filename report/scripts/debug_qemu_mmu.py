#!/usr/bin/env python3
"""Coordinate host/guest GDB sessions for a QEMU 8.2.2 TCI debug build.

The probe writes a short program and payload into otherwise unused guest RAM,
executes actual RISC-V loads, then restores the stopped kernel's PC/registers.
The submitted kernel files are not modified. This inspects functional software
TLB behavior, not the timing or organization of a physical CPU TLB.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import signal
import socket
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--qemu', type=Path, required=True)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
args.out = args.out.resolve()
args.out.mkdir(parents=True, exist_ok=True)
scripts = Path(__file__).resolve().parent
code = scripts.parents[1] / 'code'
build = subprocess.run(['make', '-j2'], cwd=code, stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT)
(args.out / 'kernel-build.txt').write_bytes(build.stdout)
if build.returncode:
    raise SystemExit('Kernel build failed')
with socket.socket() as listener:
    listener.bind(('127.0.0.1', 0))
    port = listener.getsockname()[1]
offset = 0xffffffff40000000
config = dict(qemu=str(args.qemu.resolve()), source=str(args.source.resolve()),
    kernel=str(code / 'bin/kernel'), port=port, probe_pa=0x81000000,
    data_pa=0x81004000, probe_va=0x81000000 + offset, data_va=0x81004000 + offset,
    payload=0x1122334455667788, host_summary=str(args.out / 'host-summary.json'),
    qemu_pid_file=str(args.out / 'qemu.pid'))
qemu_args = ['-machine', 'virt', '-m', '128', '-nographic', '-bios', 'default',
             '-kernel', 'bin/ucore.img', '-accel', 'tcg,thread=single',
             '-S', '-gdb', 'tcp:127.0.0.1:' + str(port)]
config['qemu_args'] = shlex.join(qemu_args)
config_file = args.out / 'config.json'
config_file.write_text(json.dumps(config, indent=2) + '\n')
env = os.environ.copy()
env['LAB2_MMU_CONFIG'] = str(config_file)
host = guest = None
try:
    with (args.out / 'host-gdb.txt').open('wb') as host_log, \
         (args.out / 'guest-gdb.txt').open('wb') as guest_log:
        host = subprocess.Popen(['gdb', '-q', '-nx', '-batch', '-x',
            str(scripts / 'mmu_host.py')], cwd=code, env=env,
            stdout=host_log, stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.monotonic() + 45
        while True:
            if host.poll() is not None:
                raise RuntimeError('Host debugger exited before opening the guest port')
            lines = Path('/proc/net/tcp').read_text().splitlines()[1:]
            if any(int(line.split()[1].split(':')[1], 16) == port
                   and line.split()[3] == '0A' for line in lines):
                break
            if time.monotonic() > deadline:
                raise TimeoutError('Debug QEMU did not open its guest port')
            time.sleep(0.1)
        print('Host QEMU ready; starting guest debugger', flush=True)
        guest = subprocess.Popen(['gdb-multiarch', '-q', '-nx', '-batch', '-x',
            str(scripts / 'mmu_guest.py')], cwd=code, env=env,
            stdout=guest_log, stderr=subprocess.STDOUT, start_new_session=True)
        host_status = host.wait(timeout=120)
        guest_status = guest.wait(timeout=20)
    host_text = (args.out / 'host-gdb.txt').read_text(errors='replace')
    guest_text = (args.out / 'guest-gdb.txt').read_text(errors='replace')
    passed = (host_status == guest_status == 0 and
        'MMU HOST CHECK COMPLETE' in host_text and 'MMU GUEST CHECK COMPLETE' in guest_text
        and 'Traceback' not in host_text + guest_text)
    if passed:
        for row in json.loads(Path(config['host_summary']).read_text()):
            print(json.dumps(row))
        print('\n'.join(line for line in guest_text.splitlines()
                        if 'VERIFIED' in line or 'COMPLETE' in line))
    else:
        print(host_text[-12000:])
        print(guest_text[-6000:])
    print('MMU DEBUG PASSED' if passed else 'MMU DEBUG FAILED')
    raise SystemExit(not passed)
finally:
    for process in (guest, host):
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
    # GDB can put the inferior in its own process group. After detach, killing
    # the debugger's group alone does not terminate that QEMU. Match both the
    # executable and this run's random guest port before touching the saved PID.
    pid_file = Path(config['qemu_pid_file'])
    if pid_file.exists():
        pid = int(pid_file.read_text())
        proc = Path('/proc') / str(pid)
        try:
            command = (proc / 'cmdline').read_bytes().split(b'\0')
            if (command[0] == config['qemu'].encode() and
                    ('tcp:127.0.0.1:' + str(port)).encode() in command):
                os.kill(pid, signal.SIGTERM)
                deadline = time.monotonic() + 5
                while proc.exists() and time.monotonic() < deadline:
                    if (proc / 'stat').read_text().split()[2] == 'Z':
                        break
                    time.sleep(0.05)
        except FileNotFoundError:
            pass
