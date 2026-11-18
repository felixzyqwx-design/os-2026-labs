/* Included only in a temporary test copy of proc.c; static helpers stay private. */
#include <sbi.h>
#include <intr.h>
#include <clock.h>

static int fail_pages_after = -1, fail_heap_once;
static int selection_only;
static struct proc_struct *selected_proc;
struct Page *lab4_real_alloc_pages(size_t n);
void *lab4_real_kmalloc(size_t n);
void lab4_real_proc_run(struct proc_struct *proc);
int lab4_probe_regs(void);
int lab4_probe_exceptions(void);

struct Page *alloc_pages(size_t n)
{
    if (fail_pages_after == 0) {
        fail_pages_after = -1;
        return NULL;
    }
    if (fail_pages_after > 0) --fail_pages_after;
    return lab4_real_alloc_pages(n);
}

void *kmalloc(size_t n)
{
    if (fail_heap_once) {
        fail_heap_once = 0;
        return NULL;
    }
    return lab4_real_kmalloc(n);
}

void proc_run(struct proc_struct *proc)
{
    if (selection_only) selected_proc = proc;
    else lab4_real_proc_run(proc);
}

static size_t list_count(void)
{
    size_t n = 0;
    list_entry_t *le = &proc_list;
    while ((le = list_next(le)) != &proc_list) {
        assert(++n < MAX_PROCESS);
    }
    return n;
}

void lab4_extra_pmm(void)
{
#ifdef TEST_SEGMENTS
    extern char kern_init[], etext[];
    extern char erodata[] __attribute__((weak));
    pte_t *text_pte = get_pte(boot_pgdir_va, (uintptr_t)kern_init, 0);
    assert(text_pte != NULL && (*text_pte & (PTE_R | PTE_X)) == (PTE_R | PTE_X));
    assert((*text_pte & (PTE_W | PTE_U)) == 0);
    pte_t *ro_pte = get_pte(boot_pgdir_va, (uintptr_t)etext, 0);
    assert(ro_pte != NULL && (*ro_pte & PTE_R) && !(*ro_pte & (PTE_W | PTE_X | PTE_U)));
    pte_t *rw_pte = get_pte(boot_pgdir_va, (uintptr_t)erodata, 0);
    assert(rw_pte != NULL && (*rw_pte & (PTE_R | PTE_W)) == (PTE_R | PTE_W));
    assert(!(*rw_pte & (PTE_X | PTE_U)));
    cprintf("[Extra segment PTEs] PASS\n");
#endif
    const uintptr_t va = 0x40000000;
    assert(boot_pgdir_va[1] == 0);
    struct Page *p = alloc_page();
    assert(p != NULL);
    size_t before = nr_free_pages();
    for (int fail = 0; fail < 2; ++fail) {
        fail_pages_after = fail;
        assert(page_insert(boot_pgdir_va, p, va, PTE_R | PTE_W) == -E_NO_MEM);
        assert(page_ref(p) == 0);
        assert(nr_free_pages() == before);
        assert(boot_pgdir_va[1] == 0);
    }
    free_page(p);
    cprintf("[Extra OOM rollback] PASS\n");

    static pde_t fake_root[NPDEENTRY] __attribute__((aligned(PGSIZE)));
    p = alloc_page();
    fake_root[0] = pte_create(page2ppn(p), PTE_R | PTE_W);
    assert(get_pte(fake_root, 0, 0) == NULL);
    assert(get_pte(fake_root, 0, 1) == NULL);
    fake_root[0] = 0;
    free_page(p);
    cprintf("[Extra large-leaf rejection] PASS\n");

    before = nr_free_pages();
    struct Page *a = alloc_page(), *b = alloc_page();
    assert(a != NULL && b != NULL);
    *(volatile uintptr_t *)page2kva(a) = 0x12345678;
    *(volatile uintptr_t *)page2kva(b) = 0xabcdef;
    assert(page_insert(boot_pgdir_va, a, va, PTE_R | PTE_W) == 0);
    assert(*(volatile uintptr_t *)va == 0x12345678);
    size_t existing_before = nr_free_pages();
    pde_t existing_root = boot_pgdir_va[1];
    fail_pages_after = 0;
    assert(page_insert(boot_pgdir_va, b, va + PTSIZE, PTE_R | PTE_W) == -E_NO_MEM);
    assert(nr_free_pages() == existing_before && boot_pgdir_va[1] == existing_root);
    assert(page_ref(a) == 1 && page_ref(b) == 0 && *(volatile uintptr_t *)va == 0x12345678);
    assert(page_insert(boot_pgdir_va, a, va + PGSIZE, PTE_R | PTE_W) == 0);
    assert(page_ref(a) == 2);
    *(volatile uintptr_t *)(va + PGSIZE) = 0x56789;
    assert(*(volatile uintptr_t *)va == 0x56789);
    page_remove(boot_pgdir_va, va + PGSIZE);
    assert(page_ref(a) == 1);
    assert(page_insert(boot_pgdir_va, b, va, PTE_R | PTE_W) == 0);
    assert(*(volatile uintptr_t *)va == 0xabcdef);
    assert(page_ref(a) == 0 && page_ref(b) == 1);
    assert(page_insert(boot_pgdir_va, b, va, PTE_R) == 0);
    assert(page_ref(b) == 1);
    page_remove(boot_pgdir_va, va);
    page_remove(boot_pgdir_va, va);
    page_remove(boot_pgdir_va, va + 2 * PGSIZE);
    pde_t *middle = KADDR(PDE_ADDR(boot_pgdir_va[1]));
    free_page(pde2page(middle[0]));
    free_page(pde2page(boot_pgdir_va[1]));
    boot_pgdir_va[1] = 0;
    flush_tlb();
    assert(nr_free_pages() == before);
    cprintf("[Extra aliases TLB refs] PASS\n");
}

static int never_started(void *unused)
{
    panic("failure test unexpectedly created a runnable thread");
}

static void lab4_extra_create(void)
{
    assert(current == idleproc && nr_process == 2 && list_count() == 1);
    size_t count = list_count(), before = nr_free_pages();
    struct proc_struct *p = alloc_proc();
    assert(p && p->state == PROC_UNINIT && p->pid == -1);
    assert(p->pgdir == boot_pgdir_pa && !p->parent && !p->mm);
    assert(!p->kstack && !p->tf && !p->runs && !p->flags && !p->need_resched);
    struct context empty = {0};
    assert(memcmp(&p->context, &empty, sizeof(empty)) == 0);
    assert(list_empty(&p->list_link) && list_empty(&p->hash_link));
    assert(setup_kstack(p) == 0);
    struct trapframe tf;
    memset(&tf, 0x5a, sizeof(tf));
    copy_thread(p, 0x12345678, &tf);
    assert(p->tf->gpr.a0 == 0 && p->tf->gpr.sp == 0x12345678);
    assert(p->tf->epc == tf.epc && p->context.ra == (uintptr_t)forkret);
    assert(p->context.sp == (uintptr_t)p->tf && (p->context.sp & 15) == 0);
    assert((uintptr_t)p->tf >= p->kstack);
    assert((uintptr_t)(p->tf + 1) == p->kstack + KSTACKSIZE);
    put_kstack(p);
    kfree(p);
    assert(nr_free_pages() == before);

    fail_heap_once = 1;
    assert(kernel_thread(never_started, NULL, 0) == -E_NO_MEM);
    fail_pages_after = 0;
    assert(kernel_thread(never_started, NULL, 0) == -E_NO_MEM);
    current->mm = (struct mm_struct *)1;
    assert(kernel_thread(never_started, NULL, 0) == -E_INVAL);
    current->mm = NULL;
    nr_process = MAX_PROCESS;
    assert(kernel_thread(never_started, NULL, 0) == -E_NO_FREE_PROC);
    nr_process = 2;
    assert(nr_free_pages() == before && list_count() == count);
    assert(find_proc(2) == NULL);
    cprintf("[Extra PCB fork rollback] PASS\n");
}

static volatile unsigned order_count;
static unsigned order[64];
static int worker(void *argument)
{
    unsigned id = (uintptr_t)argument;
    uintptr_t local = 0xcafef00d + id;
    for (unsigned round = 0; round < 32; ++round) {
        assert(order_count < 64);
        order[order_count++] = id;
        assert(lab4_probe_regs() == 0);
        assert(local == 0xcafef00d + id);
    }
    current->state = PROC_SLEEPING;
    schedule();
    panic("sleeping test worker ran again");
}

static int lab4_extra_threads(void *argument)
{
    struct proc_struct *initial = current;
    uintptr_t satp = read_csr(satp);
    assert((satp >> 60) == SATP_MODE_SV39);
    assert((satp & ((((uintptr_t)1) << 44) - 1)) == (current->pgdir >> PGSHIFT));

    for (int enabled = 0; enabled < 2; ++enabled) {
        if (enabled) intr_enable(); else intr_disable();
        bool outer, inner;
        local_intr_save(outer);
        assert(outer == enabled && !(read_csr(sstatus) & SSTATUS_SIE));
        local_intr_save(inner);
        assert(!inner);
        local_intr_restore(inner);
        assert(!(read_csr(sstatus) & SSTATUS_SIE));
        local_intr_restore(outer);
        assert(!!(read_csr(sstatus) & SSTATUS_SIE) == enabled);
        proc_run(current);
        assert(!!(read_csr(sstatus) & SSTATUS_SIE) == enabled);
    }
    intr_enable();
    cprintf("[Extra SIE nested same-thread] PASS\n");
    assert(lab4_probe_exceptions() == 4);
    cprintf("[Extra 16 32 bit breakpoint illegal returns] PASS\n");
#ifdef TEST_SEGMENTS
    extern void lab4_check_faults(void);
    lab4_check_faults();
#endif

    int first = kernel_thread(worker, (void *)1, 0);
    int second = kernel_thread(worker, (void *)2, 0);
    struct proc_struct *a = find_proc(first), *b = find_proc(second);
    assert(first == 2 && second == 3 && a && b && a->parent == initial && b->parent == initial);
    assert(a->kstack != b->kstack && a->kstack != current->kstack);
    assert(a->mm == NULL && b->mm == NULL && a->pgdir == b->pgdir);
    intr_disable();
    schedule();
    assert(!(read_csr(sstatus) & SSTATUS_SIE));
    intr_enable();
    for (int i = 0; i < 33; ++i) schedule();
    assert(current == initial && order_count == 64);
    for (unsigned i = 0; i < 64; ++i) assert(order[i] == 1 + (i & 1));
    assert(a->state == PROC_SLEEPING && b->state == PROC_SLEEPING);
    assert(read_csr(satp) == satp);
    cprintf("[Extra 64 yields registers stack order] PASS\n");

    selection_only = 1;
    selected_proc = NULL;
    current->state = PROC_SLEEPING;
    a->state = PROC_UNINIT;
    b->state = PROC_ZOMBIE;
    schedule();
    assert(selected_proc == idleproc);
    current->state = PROC_RUNNABLE;
    selected_proc = NULL;
    int runs = current->runs;
    schedule();
    assert(selected_proc == NULL && current->runs == runs + 1);
    selection_only = 0;
    a->state = b->state = PROC_SLEEPING;
    cprintf("[Extra scheduler empty single skip] PASS\n");

    /* Reserve near-wrap IDs through the real allocator, preserving its cache contract. */
    for (int i = 4; i < MAX_PID - 2; ++i) assert(get_pid() == i);
    for (int i = 0; i < 2; ++i) {
        int pid = kernel_thread(never_started, NULL, 0);
        assert(pid == MAX_PID - 2 + i);
        find_proc(pid)->state = PROC_SLEEPING;
    }
    for (int i = 0; i < MAX_PID + 4; ++i) {
        int pid = get_pid();
        assert(pid > 3 && pid < MAX_PID - 2);
    }
    cprintf("[Extra PID wrap collision] PASS\n");

    size_t start = ticks;
    while (ticks - start < 2) asm volatile("" ::: "memory");
    cprintf("[Extra live timer] PASS\n");
    cprintf("[Extra ALL] PASS\n");
    sbi_shutdown();
    for (;;) { }
}

static uintptr_t fault_resume, fault_address;
static int fault_expected, fault_seen;
extern char lab4_store_resume[], lab4_load_resume[], lab4_exec_resume[];
void lab4_fault_store(uintptr_t address);
void lab4_fault_load(uintptr_t address);
void lab4_fault_exec(uintptr_t address);
bool lab4_extra_fault(struct trapframe *tf)
{
    if (fault_resume && tf->cause == fault_expected && tf->badvaddr == fault_address) {
        ++fault_seen;
        tf->epc = fault_resume;
        fault_resume = 0;
        return 1;
    }
    return 0;
}

void lab4_check_faults(void)
{
    static const char read_only[] __attribute__((aligned(8))) = "read only";
    static uint32_t data_code = 0x00008067;
    fault_expected = CAUSE_STORE_PAGE_FAULT;
    fault_address = ROUNDDOWN((uintptr_t)kernel_thread_entry, 8);
    fault_resume = (uintptr_t)lab4_store_resume;
    lab4_fault_store(fault_address);
    assert(fault_seen == 1 && !fault_resume);
    fault_address = (uintptr_t)read_only;
    fault_resume = (uintptr_t)lab4_store_resume;
    lab4_fault_store(fault_address);
    assert(fault_seen == 2 && !fault_resume && read_only[0] == 'r');
    fault_expected = CAUSE_FETCH_PAGE_FAULT;
    fault_address = (uintptr_t)&data_code;
    fault_resume = (uintptr_t)lab4_exec_resume;
    lab4_fault_exec(fault_address);
    assert(fault_seen == 3 && !fault_resume);
    struct Page *p = alloc_page();
    assert(page_insert(boot_pgdir_va, p, 0x40000000, PTE_R | PTE_W) == 0);
    *(volatile uintptr_t *)0x40000000 = 42;
    page_remove(boot_pgdir_va, 0x40000000);
    fault_expected = CAUSE_LOAD_PAGE_FAULT;
    fault_address = 0x40000000;
    fault_resume = (uintptr_t)lab4_load_resume;
    lab4_fault_load(fault_address);
    assert(fault_seen == 4 && !fault_resume);
    pde_t *middle = KADDR(PDE_ADDR(boot_pgdir_va[1]));
    free_page(pde2page(middle[0]));
    free_page(pde2page(boot_pgdir_va[1]));
    boot_pgdir_va[1] = 0;
    flush_tlb();
    cprintf("[Extra text rodata NX unmap faults] PASS\n");
}
