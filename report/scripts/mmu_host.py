"""Run inside native GDB to inspect actual guest loads in a debug QEMU."""
import json
import os
from pathlib import Path
import traceback
import gdb

config = json.loads(Path(os.environ['LAB2_MMU_CONFIG']).read_text())
source = Path(config['source'])
cpu_file = source / 'target/riscv/cpu_helper.c'
tlb_file = source / 'accel/tcg/cputlb.c'
records = []
MASK = (1 << 64) - 1

def value(expression):
    return int(gdb.parse_and_eval(expression)) & MASK

def emit(kind, **fields):
    row = dict(kind=kind, **fields)
    records.append(row)
    print('MMU_RECORD ' + json.dumps(row), flush=True)

def line_of(path, text, after=0):
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if number > after and text in line:
            return number
    raise RuntimeError('source marker missing: ' + text)

def until_line(path, text, after=0):
    number = line_of(path, text, after)
    gdb.Breakpoint(str(path) + ':' + str(number), temporary=True, internal=True)
    gdb.execute('continue')
    assert gdb.selected_frame().find_sal().symtab.fullname() == str(path)

def main():
    for command in ['set pagination off', 'set confirm off',
        'set print thread-events off', 'set debuginfod enabled off',
        'set startup-with-shell off', 'handle SIGPIPE nostop noprint pass']:
        gdb.execute(command)
    gdb.execute('file ' + config['qemu'])
    gdb.execute('set args ' + config['qemu_args'])
    addresses = (config['data_pa'], config['data_va'])
    condition = ' || '.join('data->addr == %#x' % address for address in addresses)
    lookup = gdb.Breakpoint('mmu_lookup1', internal=True)
    lookup.condition = condition
    lookup.enabled = False
    translate = gdb.Breakpoint('get_physical_address', internal=True)
    translate.condition = '(!is_debug) && (' + ' || '.join(
        'addr == %#x' % address for address in addresses) + ')'
    translate.enabled = False
    fill = gdb.Breakpoint('tlb_set_page', internal=True)
    fill.condition = ' || '.join('addr == %#x' % address for address in addresses)
    fill.enabled = False
    def remember_qemu_pid(event):
        pid = gdb.selected_inferior().pid
        if pid:
            Path(config['qemu_pid_file']).write_text(str(pid) + '\n')
    gdb.events.cont.connect(remember_qemu_pid)
    # Arm at the first probe fetch: the guest kernel-entry breakpoint can fire
    # before QEMU fetches that page, so arming at the kernel page is too late.
    arm = gdb.Breakpoint('riscv_cpu_tlb_fill', internal=True)
    arm.condition = 'address == %#x && access_type == 2' % config['probe_pa']
    gdb.execute('run')
    assert gdb.selected_inferior().pid and gdb.selected_frame().name() == 'riscv_cpu_tlb_fill'
    arm.delete()
    print('BARE PROBE FETCH REACHED: arming controlled-load breakpoints', flush=True)
    for index in range(4):
        mode = 'Bare' if index < 2 else 'Sv39'
        ordinal = index % 2 + 1
        expected_addr = addresses[index // 2]
        lookup.enabled = True
        gdb.execute('continue')
        lookup.enabled = False
        assert gdb.selected_frame().name() == 'mmu_lookup1'
        print('LOOKUP ENTRY data->addr=%#x expected=%#x' %
              (value('data->addr'), expected_addr), flush=True)
        until_line(tlb_file, 'if (!tlb_hit(tlb_addr, addr))')
        address = value('addr')
        tag = value('tlb_addr')
        assert address == expected_addr
        # This fixture uses plain aligned RAM with no watchpoint/MMIO flags.
        hit = tag == (address & ~4095)
        assert hit == (ordinal == 2), 'unexpected TLB state for controlled load'
        print(gdb.execute('bt 8', to_string=True), flush=True)
        gdb.execute('next')
        sal = gdb.selected_frame().find_sal()
        emit('lookup', mode=mode, ordinal=ordinal, addr=hex(address),
             tag=hex(tag), hit=hit, next_line=sal.line,
             next_source=tlb_file.read_text().splitlines()[sal.line - 1].strip())
        if hit:
            gdb.execute('finish')
            continue

        translate.enabled = True
        gdb.execute('continue')
        translate.enabled = False
        assert gdb.selected_frame().name() == 'get_physical_address'
        satp = value('env->satp')
        assert value('addr') == expected_addr
        assert satp >> 60 == (0 if mode == 'Bare' else 8)
        print(gdb.execute('bt 8', to_string=True), flush=True)
        if mode == 'Bare':
            marker = line_of(cpu_file, 'case VM_1_10_MBARE:')
            until_line(cpu_file, '*physical = addr;', marker)
            gdb.execute('next')
            physical = value('*physical')
            assert physical == config['data_pa']
            emit('translation', mode=mode, satp=hex(satp), va=hex(expected_addr),
                 pa=hex(physical), page_walk=False)
        else:
            until_line(cpu_file, 'pte_addr = base + idx * ptesize;')
            root = value('base')
            vpn2 = value('idx')
            levels = value('levels')
            shift = value('ptshift')
            assert levels == 3 and vpn2 == 511 and shift == 18
            until_line(cpu_file, 'if (!(pte & PTE_V))')
            pte_address = value('pte_addr')
            pte = value('pte')
            assert pte_address == root + vpn2 * 8
            assert pte & 0xcf == 0xcf
            until_line(cpu_file, 'if (ppn & ((1ULL << ptshift) - 1))')
            assert value('ptshift') == 18, 'expected root-level 1 GiB leaf'
            assert value('i') == 0 and root == (satp & ((1 << 44) - 1)) << 12
            until_line(cpu_file, '*physical = (((ppn & ~napot_mask)')
            gdb.execute('next')
            # A source-level step can stop on a continuation line before the
            # multi-line assignment has stored through physical.
            until_line(cpu_file, 'if (access_type != MMU_DATA_STORE && !(pte & PTE_D))')
            physical = value('*physical')
            assert physical == config['data_pa']
            emit('translation', mode=mode, satp=hex(satp), va=hex(expected_addr),
                 root_pa=hex(root), vpn2=vpn2, levels=levels, pte_pa=hex(pte_address),
                 pte=hex(pte), pa=hex(physical), leaf_size=1 << 30,
                 walked_entries=1, page_walk=True)
        gdb.execute('finish')
        fill.enabled = True
        gdb.execute('continue')
        fill.enabled = False
        assert gdb.selected_frame().name() == 'tlb_set_page'
        assert value('addr') == expected_addr and value('paddr') == config['data_pa']
        emit('fill', mode=mode, va=hex(value('addr')), pa=hex(value('paddr')),
             protection=value('prot'), mmu_index=value('mmu_idx'), size=value('size'))
        gdb.execute('finish')
    assert len([r for r in records if r['kind'] == 'lookup']) == 4
    assert len([r for r in records if r['kind'] == 'translation']) == 2
    Path(config['host_summary']).write_text(json.dumps(records, indent=2) + '\n')
    print('MMU HOST CHECK COMPLETE', flush=True)
    gdb.execute('detach')
    gdb.execute('quit 0')

try:
    main()
except Exception:
    traceback.print_exc()
    print('MMU HOST CHECK FAILED', flush=True)
    gdb.execute('quit 1')
