#!/usr/bin/env python3
"""Verify the live Sv39 boot mapping in guest GDB; no host-QEMU source debugging."""
import argparse
from pathlib import Path
import socket
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=True)
code = Path(__file__).resolve().parents[2] / 'code'
with socket.socket() as listener:
    listener.bind(('127.0.0.1', 0))
    port = listener.getsockname()[1]
commands = '''set pagination off
set confirm off
set architecture riscv:rv64
file bin/kernel
target remote 127.0.0.1:PORT
hbreak kern_init
continue
python
mask = (1 << 64) - 1
satp = int(gdb.parse_and_eval('$satp')) & mask
va = int(gdb.parse_and_eval('$pc')) & mask
offset = 0xffffffff40000000
root_pa = (satp & ((1 << 44) - 1)) << 12
root_va = int(gdb.parse_and_eval('&boot_page_table_sv39')) & mask
assert satp >> 60 == 8, 'Sv39 not enabled'
assert root_pa == root_va - offset, 'satp root mismatch'
inferior = gdb.selected_inferior()
def pte_at(index):
    return int.from_bytes(inferior.read_memory(root_va + index * 8, 8).tobytes(), 'little')
index = (va >> 30) & 511
pte = pte_at(index)
assert index == 511 and pte & 0xcf == 0xcf, 'missing high 1GiB leaf'
pa = ((pte >> 10) << 12) | (va & ((1 << 30) - 1))
assert pa == va - offset, 'VA/PA mismatch'
assert pte_at(2) == pte, 'missing low boot transition leaf'
print('satp=%#018x root_pa=%#018x root_va=%#018x' % (satp, root_pa, root_va))
print('VA=%#018x VPN2=%d PTE=%#018x PA=%#018x' % (va, index, pte, pa))
print('bytes at high VA: ' + inferior.read_memory(va, 8).tobytes().hex())
print(gdb.execute('monitor xp /8bx %#x' % pa, to_string=True))
print(gdb.execute('info registers pc sp satp scause sepc stval', to_string=True))
print('MAPPING CHECK COMPLETE')
end
detach
quit
'''.replace('PORT', str(port))
with tempfile.TemporaryDirectory(prefix='lab2-mapping-') as temp:
    command_file = Path(temp) / 'mapping.gdb'
    command_file.write_text(commands)
    with (args.out / 'mapping-qemu.txt').open('wb') as qlog:
        qemu = subprocess.Popen(['qemu-system-riscv64', '-machine', 'virt',
            '-nographic', '-bios', 'default', '-kernel', 'bin/ucore.img',
            '-S', '-gdb', 'tcp:127.0.0.1:' + str(port)], cwd=code,
            stdout=qlog, stderr=subprocess.STDOUT)
        try:
            probe = subprocess.run(['gdb-multiarch', '-q', '-nx', '-batch',
                '-x', str(command_file)], cwd=code, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=20)
            text = probe.stdout.decode(errors='replace')
            (args.out / 'mapping-gdb.txt').write_text(text)
            print(text)
            passed = (probe.returncode == 0 and 'MAPPING CHECK COMPLETE' in text
                and not any(error in text for error in ('Traceback', 'Error in', 'AssertionError')))
        finally:
            qemu.terminate()
            qemu.wait(timeout=5)
raise SystemExit(not passed)
