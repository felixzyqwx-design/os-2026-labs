#!/usr/bin/env python3
"""Observe real trapframes and sret using the QEMU guest GDB interface."""
import argparse
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--mode', choices=['exceptions', 'timer'], default='exceptions')
args = parser.parse_args()
args.out = args.out.resolve()
args.out.mkdir(parents=True, exist_ok=True)
source = Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='lab3-gdb-') as directory:
    root = Path(directory)
    shutil.copytree(source, root, dirs_exist_ok=True,
        ignore=shutil.ignore_patterns('obj', 'bin', '.qemu.*', '__pycache__'))
    if args.mode == 'exceptions':
        for name in ['probe.c', 'probe_registers.S']:
            shutil.copyfile(root / 'tools/tests' / name, root / 'kern/init' / name)
        init = root / 'kern/init/init.c'
        text = init.read_text()
        where = text.rindex('idt_init();') + len('idt_init();')
        init.write_text(text[:where] + '\n    extern void lab3_probe(void);\n    lab3_probe();' + text[where:])
    build = subprocess.run(['make', '-j2'], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=40)
    (args.out / 'build.txt').write_bytes(build.stdout)
    if build.returncode:
        raise SystemExit('GDB probe build failed')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    count = 4 if args.mode == 'exceptions' else 2
    gdb_script = '''set pagination off
set confirm off
set architecture riscv:rv64
set remotetimeout 5
file {elf}
target remote 127.0.0.1:{port}
python
import gdb, json
from pathlib import Path
mask = (1 << 64) - 1
def reg(name):
    return int(gdb.parse_and_eval('$' + name)) & mask
def words(addr):
    data = bytes(gdb.selected_inferior().read_memory(addr, 288))
    return [int.from_bytes(data[i:i+8], 'little') for i in range(0, 288, 8)]
entry = gdb.Breakpoint('__alltraps', internal=True)
c_entry = gdb.Breakpoint('trap', internal=True)
c_entry.enabled = False
ret = gdb.Breakpoint('__trapret', internal=True)
ret.enabled = False
rows = []
try:
    for case in range({count}):
        entry.enabled = True
        gdb.execute('continue', to_string=True)
        entry.enabled = False
        before = [reg('x' + str(i)) for i in range(32)]
        csr = {{name: reg(name) for name in ['sstatus','sepc','scause','stval']}}
        assert csr['sstatus'] & 0x100, 'trap did not come from S mode'
        assert not (csr['sstatus'] & 2), 'SIE was not cleared on entry'
        c_entry.enabled = True
        gdb.execute('continue', to_string=True)
        c_entry.enabled = False
        frame = reg('a0')
        saved = words(frame)
        assert saved[:32] == before, 'SAVE_ALL frame differs from entry registers'
        assert frame == before[2] - 288 and frame % 16 == 0, 'trap stack layout/alignment'
        assert saved[32:] == [csr['sstatus'],csr['sepc'],csr['stval'],csr['scause']], 'CSR layout'
        if {timer}:
            assert csr['scause'] == (1 << 63) | 5
            length = 0
        else:
            assert csr['scause'] == [3,3,2,2][case]
            half = int.from_bytes(bytes(gdb.selected_inferior().read_memory(csr['sepc'], 2)), 'little')
            length = 4 if half & 3 == 3 else 2
            assert length == [2,4,2,4][case]
        ret.enabled = True
        gdb.execute('continue', to_string=True)
        ret.enabled = False
        assert reg('sp') == frame, 'C call did not preserve the trapframe stack'
        returned = words(frame)
        expected_pc = csr['sepc'] + length
        assert returned[33] == expected_pc, 'handler EPC update'
        for step in range(50):
            instruction = gdb.execute('x/i $pc', to_string=True)
            if 'sret' in instruction:
                break
            gdb.execute('stepi', to_string=True)
        else:
            raise AssertionError('RESTORE_ALL did not reach sret')
        after = [reg('x' + str(i)) for i in range(32)]
        assert after == before, 'RESTORE_ALL register mismatch'
        assert reg('sepc') == expected_pc, 'restored sepc mismatch'
        assert reg('sstatus') == returned[32], 'restored sstatus mismatch'
        # Stop at the exact return address: QEMU/GDB may run past sret when
        # single-stepping a privilege-return instruction.
        resumed = gdb.Breakpoint('*' + hex(expected_pc), temporary=True, internal=True)
        gdb.execute('continue', to_string=True)
        assert reg('pc') == expected_pc, 'sret target mismatch'
        assert reg('sp') == before[2], 'post-sret stack mismatch'
        status = reg('sstatus')
        assert (status & 2) == ((csr['sstatus'] & 0x20) >> 4), 'SPIE to SIE transfer'
        assert status & 0x20 and not (status & 0x100), 'sret status transition'
        assert reg('priv') == 1, 'did not return to S mode'
        row = {{'case':case, 'cause':hex(csr['scause']), 'epc_before':hex(csr['sepc']),
            'epc_after':hex(expected_pc), 'instruction_bytes':length,
            'frame':hex(frame), 'sp':hex(before[2]), 'status_at_entry':hex(csr['sstatus']),
            'status_after_sret':hex(status), 'gpr_checked':32, 'passed':True}}
        rows.append(row)
        print('GDB_TRAP_OBSERVATION ' + json.dumps(row))
    Path({json_path!r}).write_text(json.dumps(rows, indent=2) + '\\n')
    gdb.execute('detach', to_string=True)
    print('LAB3_GDB_ALL_PASS')
except Exception as error:
    print('LAB3_GDB_FAIL ' + repr(error))
    gdb.execute('quit 1')
end
quit 0
'''.format(elf=root / 'bin/kernel', port=port, count=count,
        timer=args.mode == 'timer', json_path=str(args.out / 'observations.json'))
    (root / 'probe.gdb').write_text(gdb_script)
    command = ['qemu-system-riscv64', '-machine', 'virt', '-nographic', '-bios', 'default',
        '-kernel', 'bin/ucore.img', '-S', '-gdb', 'tcp:127.0.0.1:' + str(port), '-no-reboot']
    qemu = subprocess.Popen(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        debug = subprocess.run(['gdb-multiarch', '-q', '-batch', '-x', str(root / 'probe.gdb')],
            cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45)
        (args.out / 'gdb.txt').write_bytes(debug.stdout)
        output = debug.stdout.decode(errors='replace')
        passed = debug.returncode == 0 and 'LAB3_GDB_ALL_PASS' in output
        passed = passed and not re.search(r'Python Exception|Traceback|LAB3_GDB_FAIL', output)
        if not passed:
            print(output[-3000:])
            raise RuntimeError('GDB checks failed')
        qemu_output, _ = qemu.communicate(timeout=20)
        (args.out / 'qemu.txt').write_bytes(qemu_output)
        expected = b'LAB3_PROBE_ALL_PASS' if args.mode == 'exceptions' else b'100 ticks'
        passed = qemu.returncode == 0 and expected in qemu_output
        assert passed, 'guest completion missing after detach'
        rows = json.loads((args.out / 'observations.json').read_text())
        result = dict(mode=args.mode, gdb_exit=debug.returncode, qemu_exit=qemu.returncode,
            observations=len(rows), passed=passed)
        (args.out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
    finally:
        if qemu.poll() is None:
            qemu.terminate()
            try:
                output, _ = qemu.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                qemu.kill()
                output, _ = qemu.communicate()
            (args.out / 'qemu-stopped.txt').write_bytes(output)
        else:
            output, _ = qemu.communicate()
            if output:
                (args.out / 'qemu-final.txt').write_bytes(output)
