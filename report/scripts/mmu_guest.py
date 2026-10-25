"""Run in RISC-V GDB: execute two real loads in Bare and Sv39 modes."""
import json
import os
from pathlib import Path
import traceback
import gdb

config = json.loads(Path(os.environ['LAB2_MMU_CONFIG']).read_text())
MASK = (1 << 64) - 1

def register(name):
    return int(gdb.parse_and_eval('$' + name)) & MASK

def probe(mode, pc, address):
    saved = {name: register(name) for name in ('pc', 't0', 't1', 't2')}
    # sfence.vma; ld t0,0(t1); ld t2,0(t1); ebreak (not executed).
    instructions = [0x12000073, (6 << 15) | (3 << 12) | (5 << 7) | 3,
                    (6 << 15) | (3 << 12) | (7 << 7) | 3, 0x00100073]
    inferior = gdb.selected_inferior()
    saved_code = inferior.read_memory(pc, 16).tobytes()
    saved_data = inferior.read_memory(address, 8).tobytes()
    inferior.write_memory(pc, b''.join(i.to_bytes(4, 'little') for i in instructions))
    inferior.write_memory(address, config['payload'].to_bytes(8, 'little'))
    stop = gdb.Breakpoint('*%#x' % (pc + 12), type=gdb.BP_HARDWARE_BREAKPOINT,
                          internal=True)
    gdb.execute('set $t1 = %#x' % address)
    gdb.execute('set $pc = %#x' % pc)
    print(mode + ' FIXTURE: two guest ld instructions; data=' + hex(address), flush=True)
    print(gdb.execute('x/4i $pc', to_string=True), flush=True)
    gdb.execute('continue')
    assert register('pc') == pc + 12
    assert register('t0') == config['payload'] and register('t2') == config['payload']
    print(mode + ' LOADS VERIFIED: t0=t2=' + hex(register('t0')), flush=True)
    stop.delete()
    inferior.write_memory(pc, saved_code)
    inferior.write_memory(address, saved_data)
    for name, value in saved.items():
        gdb.execute('set $%s = %#x' % (name, value))

try:
    gdb.execute('set pagination off')
    gdb.execute('set confirm off')
    gdb.execute('set remotetimeout 120')
    gdb.execute('set architecture riscv:rv64')
    gdb.execute('file ' + config['kernel'])
    gdb.execute('target remote 127.0.0.1:' + str(config['port']))
    start = gdb.Breakpoint('*0x80200000', type=gdb.BP_HARDWARE_BREAKPOINT,
                           internal=True)
    gdb.execute('continue')
    start.delete()
    assert register('satp') == 0
    probe('Bare', config['probe_pa'], config['data_pa'])
    entry = gdb.Breakpoint('kern_init', type=gdb.BP_HARDWARE_BREAKPOINT, internal=True)
    gdb.execute('continue')
    entry.delete()
    assert register('satp') >> 60 == 8
    probe('Sv39', config['probe_va'], config['data_va'])
    print('MMU GUEST CHECK COMPLETE', flush=True)
    gdb.execute('detach')
    gdb.execute('quit 0')
except Exception:
    traceback.print_exc()
    print('MMU GUEST CHECK FAILED', flush=True)
    gdb.execute('quit 1')
