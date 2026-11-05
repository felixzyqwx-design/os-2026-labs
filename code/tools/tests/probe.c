#include <assert.h>
#include <clock.h>
#include <defs.h>
#include <intr.h>
#include <pmm.h>
#include <riscv.h>
#include <sbi.h>
#include <stdio.h>
#include <string.h>
#include <trap.h>
#include <../sync/sync.h>

extern int probe_registers(void);
extern void interrupt_handler(struct trapframe *tf);
extern void exception_handler(struct trapframe *tf);

void lab3_probe(void) {
    assert(sizeof(struct trapframe) == 288);
    assert((uintptr_t)&((struct trapframe *)0)->epc == 264);
    assert(probe_registers() == 0);
    cprintf("LAB3_PROBE: registers and four exception returns PASS\n");

#ifndef PROBE_MODULE1
    struct trapframe tf;
    memset(&tf, 0, sizeof(tf));
    tf.epc = 0x12345678;
    tf.cause = ((uintptr_t)1 << 63) | IRQ_S_TIMER;
    const size_t before[] = {98, 99, 100, 198, 199};
    for (unsigned i = 0; i < sizeof(before) / sizeof(before[0]); ++i) {
        ticks = before[i];
        interrupt_handler(&tf);
        assert(ticks == before[i] + 1);
        assert(tf.epc == 0x12345678);
    }
    cprintf("LAB3_PROBE: timer boundaries 99/100/101/199/200 PASS\n");
    ticks = 0;

    const unsigned irq[] = {IRQ_U_SOFT, IRQ_S_SOFT, IRQ_H_SOFT, IRQ_M_SOFT,
        IRQ_U_TIMER, IRQ_H_TIMER, IRQ_M_TIMER, IRQ_U_EXT, IRQ_S_EXT,
        IRQ_H_EXT, IRQ_M_EXT, IRQ_COP, IRQ_HOST, 15};
    for (unsigned i = 0; i < sizeof(irq) / sizeof(irq[0]); ++i) {
        tf.cause = ((uintptr_t)1 << 63) | irq[i];
        interrupt_handler(&tf);
        assert(tf.epc == 0x12345678 && ticks == 0);
    }
    tf.cause = 20;
    exception_handler(&tf);
    assert(tf.epc == 0x12345678);
    cprintf("LAB3_PROBE: known and unknown cause dispatch PASS\n");

    intr_disable();
    bool outer, inner;
    local_intr_save(outer);
    assert(!outer && !(read_csr(sstatus) & SSTATUS_SIE));
    local_intr_restore(outer);
    assert(!(read_csr(sstatus) & SSTATUS_SIE));
    intr_enable();
    local_intr_save(outer);
    assert(outer && !(read_csr(sstatus) & SSTATUS_SIE));
    local_intr_save(inner);
    assert(!inner);
    local_intr_restore(inner);
    assert(!(read_csr(sstatus) & SSTATUS_SIE));
    local_intr_restore(outer);
    assert(read_csr(sstatus) & SSTATUS_SIE);
    size_t free_before = nr_free_pages();
    struct Page *page = alloc_pages(3);
    assert(page && (read_csr(sstatus) & SSTATUS_SIE));
    free_pages(page, 3);
    assert(nr_free_pages() == free_before && (read_csr(sstatus) & SSTATUS_SIE));
    intr_disable();
    page = alloc_page();
    assert(page && !(read_csr(sstatus) & SSTATUS_SIE));
    free_page(page);
    assert(nr_free_pages() == free_before && !(read_csr(sstatus) & SSTATUS_SIE));
    cprintf("LAB3_PROBE: interrupt state, nesting and page recovery PASS\n");
#endif
    cprintf("LAB3_PROBE_ALL_PASS\n");
    sbi_shutdown();
    while (1) {}
}
