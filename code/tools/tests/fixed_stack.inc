/* Optional, temporary experiment: distinct roots share all high kernel mappings. */
#define FIXED_TOP ((uintptr_t)0x80000000)
static uintptr_t observed_sp[2];
static volatile unsigned fixed_steps, guard_seen;
static int fixed_worker(void *argument)
{
    unsigned id = (uintptr_t)argument;
    volatile uintptr_t cookie = 0xfedc12340000UL + id;
    uintptr_t sp;
    asm volatile("mv %0, sp" : "=r"(sp));
    observed_sp[id] = sp;
    assert(sp >= FIXED_TOP - KSTACKSIZE && sp < FIXED_TOP);
    for (unsigned round = 0; round < 32; ++round) {
        assert(cookie == 0xfedc12340000UL + id);
        assert(((read_csr(satp) & ((((uintptr_t)1) << 44) - 1)) << PGSHIFT) == current->pgdir);
        ++fixed_steps;
        assert(lab4_probe_regs() == 0);
    }
    fault_address = FIXED_TOP - KSTACKSIZE - 8;
    fault_expected = CAUSE_STORE_PAGE_FAULT;
    fault_resume = (uintptr_t)lab4_store_resume;
    int expected = fault_seen + 1;
    lab4_fault_store(fault_address);
    assert(!fault_resume && fault_seen == expected);
    ++guard_seen;
    current->state = PROC_SLEEPING;
    schedule();
    panic("fixed-stack sleeping worker ran again");
}

static struct proc_struct *make_fixed_worker(unsigned id)
{
    int pid = kernel_thread(fixed_worker, (void *)(uintptr_t)id, 0);
    struct proc_struct *p = find_proc(pid);
    assert(p != NULL);
    struct Page *root_page = alloc_page();
    assert(root_page != NULL);
    pde_t *root = page2kva(root_page);
    memcpy(root, boot_pgdir_va, PGSIZE);
    root[PDX1(FIXED_TOP - 1)] = 0;
    for (unsigned i = 0; i < KSTACKPAGE; ++i) {
        assert(page_insert(root, kva2page((void *)(p->kstack + i * PGSIZE)),
                           FIXED_TOP - KSTACKSIZE + i * PGSIZE, PTE_R | PTE_W) == 0);
    }
    p->pgdir = page2pa(root_page);
    uintptr_t alias_tf = FIXED_TOP - sizeof(struct trapframe);
    /* The underlying physical stack still has a stable direct-map alias. */
    p->tf->gpr.sp = alias_tf;
    p->context.sp = alias_tf;
    p->tf = (struct trapframe *)alias_tf;
    return p;
}

static int lab4_fixed_experiment(void *argument)
{
    struct proc_struct *a = make_fixed_worker(0), *b = make_fixed_worker(1);
    assert(a->pgdir != b->pgdir && a->kstack != b->kstack);
    for (int i = 0; i < 34; ++i) schedule();
    assert(fixed_steps == 64 && guard_seen == 2 && observed_sp[0] == observed_sp[1]);
    assert(a->state == PROC_SLEEPING && b->state == PROC_SLEEPING);
    cprintf("[Fixed stack] same sp=0x%016lx, physical stacks=0x%016lx/0x%016lx\n",
            observed_sp[0], PADDR(a->kstack), PADDR(b->kstack));
    cprintf("[Fixed stack 64 yields and two guard faults] PASS\n");
    cprintf("[Extra ALL] PASS\n");
    sbi_shutdown();
    for (;;) { }
}
