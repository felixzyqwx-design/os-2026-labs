# Lab 4 关键提示词

邹瑛琦（2412744）、丁子昂（2411130）

本文依据本次实验需求、确认方案和实施记录提炼，不是逐字聊天。实现与测试分别记录；标为“迭代”的要求是在定位问题后补充的。路径均相对于实验根目录。接口上下文以当前 `code/` 为准，辅助函数保持模块内部可见，不改无关模块或原评分条件。

## P1-I：物理内存依赖的迁入

[PROMPT]

任务：在 `code/kern/mm/pmm.c` 和 `default_pmm.c` 的 Lab2 标记区迁入已有的物理内存初始化和 Best-Fit，适配 Lab4 的 Page 与管理器接口。

操作要求：修改实际文件，保留本次框架及 `basic_check()`、`best_fit_check()` 原函数体。不要整体替换为旧实验目录，也不迁入旧 SLUB。

输出要求：给出可编译的必要依赖，保留实验标记并填写学号；新增内部辅助函数用 static。

[RELY]

读取 `memlayout.h` 中完整的 `struct Page`、`free_area_t` 和页标志接口；当前 Page 有 ref、flags、property、page_link、pra_page_link、pra_vaddr。页大小为 `PGSIZE=4096`。`pmm_manager` 的接口是 init、init_memmap、alloc_pages、free_pages、nr_free_pages、check，本框架使用 `default_pmm_manager`。

可调用 DTB 的 `get_memory_base()`、`get_memory_size()`，以及 `PADDR/KADDR`、`PPN`、`pa2page()`、`init_memmap()`、`set_page_ref()`、页标志和链表接口。`PHYSICAL_MEMORY_OFFSET` 是当前虚实偏移；`KERNEL_BEGIN_PADDR` 为0x80200000，管理上界为该值加 KMEMSIZE。

[GUARANTEE]

```c
static void page_init(void);
static void best_fit_init(void);
static void best_fit_init_memmap(struct Page *base, size_t n);
static struct Page *best_fit_alloc_pages(size_t n);
static void best_fit_free_pages(struct Page *base, size_t n);
static size_t best_fit_nr_free_pages(void);
const struct pmm_manager default_pmm_manager;
```

允许模块内静态空闲区及链表辅助函数，不改变公开管理器签名。

[SPECIFICATION]

| 函数 | Pre-Condition | Post-Condition |
| --- | --- | --- |
| `page_init` | DTB初始化完成；内核结束符号有效，分配器已初始化 | 设置地址偏移、npage和Page数组；固件、内核、描述符所占页保留；仅登记对齐后的完整空闲页 |
| `best_fit_init` | 管理器尚未接管空闲块 | 建立空链表，空闲页计数为0 |
| `best_fit_init_memmap` | base起的n页是待接管保留页，n>0 | 建立可用块并维护计数和页属性，不把已用页重复登记 |
| `best_fit_alloc_pages` | n>0，空闲结构有效 | 返回最小足够块的前n页；余块和计数正确；无足够块时返回NULL |
| `best_fit_free_pages` | 归还的是已分配、非保留且未重复归还的n页 | 按地址合并相邻空闲块，引用和属性复位，计数增加n |
| `best_fit_nr_free_pages` | 空闲结构有效 | 返回当前可分配页数，不改变状态 |

Case：DTB基址或大小无效、加法溢出、内核或描述符无法容纳时终止初始化；超过框架管理上界时截断；没有剩余整页时不调用 `init_memmap()`。不更改原测试去适应分配策略。

## P1-T：物理内存依赖验证

[PROMPT]

任务：验证迁入后的地址范围和分配行为。先保留官方原骨架的构建失败，再检查适配后的构建和原分配器自检。

操作要求：测试只写到独立副本。真实QEMU内存配置与合成边界输入分开记录，不把旧实验结果当本轮结果。

输出要求：保存命令、配置、退出状态和完整预期；预期panic的拒绝路径与成功路径分开判定。

[RELY]

使用当前 `page_init()`、原 `basic_check()/best_fit_check()` 和 `run_lab4.py` 的 `--memory`、`--boundary` 参数。构造输入时尚未设置 `va_pa_offset`，不能提前用 PADDR 推导物理地址，应使用已知固定偏移。

[GUARANTEE]

验证64/128/256 MiB三种真实配置；验证 invalid-base、zero、overflow、no-kernel、descriptors、no-free、fragment 七项合成输入。不修改生产 `page_init()` 来接受错误输入。

[SPECIFICATION]

Pre-Condition：保存源散列，在新输出目录中复制源码并构建。

Post-Condition：真实配置能够完成分配器和后续测试；256 MiB按框架上限管理。无效输入在预期位置被拒绝；无整页和碎片输入的空闲页数为0，不错误登记页面。仅有退出0或超时不能算通过。

迭代：最初三个边界探针在偏移初始化前误用PADDR，修正的是探针输入计算，生产实现未改。

## P2-I：Trap 机制的迁入

[PROMPT]

任务：补齐 `code/kern/trap/trapentry.S` 和 `trap.c` 的 Lab3 依赖区，使中断返回及新线程首次恢复可用。

操作要求：保留Lab4的SAVE_ALL、trap分流和forkrets，迁入已有恢复与处理逻辑；时钟机制保留预约/计数，不沿用Lab3专用的十次输出后关机策略。

输出要求：实际修改标记区，说明必要的向量对齐调整；不引入用户态切换或一般缺页恢复。

[RELY]

`struct trapframe` 含32个GPR槽和 status、epc、badvaddr、cause，共36个RV64槽。汇编STORE/LOAD使用REGBYTES。`trap(struct trapframe *)` 接收a0指向的帧；`__trapret` 恢复后sret；Lab4新增 `forkrets(tf)` 将sp指向给定帧。

已有 `clock_set_next_event()`、ticks、`print_ticks()` 和RISC-V原因码。当前异常处理对断点和非法指令按低两位判断2/4字节长度。

[GUARANTEE]

```c
void __alltraps(void);  /* 汇编入口符号 */
void interrupt_handler(struct trapframe *tf);
void exception_handler(struct trapframe *tf);
```

补全汇编宏 RESTORE_ALL；`__alltraps` 保存后将帧传给trap。保持forkrets和__trapret的接口。

[SPECIFICATION]

Pre-Condition：使用当前36槽布局；入口和返回现场都在可用栈内。

Post-Condition：`__alltraps` 以a0传帧，C处理返回后仍定位原帧；RESTORE_ALL恢复需要的CSR/GPR，sp最后恢复；sret到调整后的epc。时钟预约下一事件并增加ticks。断点和非法指令按2/4字节推进epc，其他未支持异常保留诊断行为。异常向量入口满足四字节对齐。

| 接口 | Pre-Condition | Post-Condition |
| --- | --- | --- |
| `__alltraps` | 当前栈可容纳36槽，向量已对齐 | 原现场保存为tf并通过a0传给trap；返回后仍指向该帧 |
| `RESTORE_ALL` | sp指向完整有效tf | 恢复返回所需的sstatus/sepc和GPR，最后恢复原sp，供sret使用 |
| `interrupt_handler` | tf的cause有效；时钟中断前驱动已初始化 | 时钟重新预约并增加ticks，达到输出间隔时打印；其他分支保留对应诊断 |
| `exception_handler` | 断点/非法指令的epc可读，tf可修改 | 按编码推进2/4字节并返回；未支持异常保留诊断，不伪造一般故障恢复 |

## P2-T：Trap 依赖回归

[PROMPT]

任务：在当前Lab4中验证真实时钟和四种异常返回，不用Lab3历史结果代替。

操作要求：在测试副本加入ABI正确的汇编探针；生产init不加入演示触发代码。

输出要求：记录四次异常的实际PC和返回计数，以及时钟推进结果。

[RELY]

测试入口 `int lab4_probe_exceptions(void)` 位于 `register_probe.S`，依次触发16位断点、32位断点、16位非法指令和32位非法指令；每次返回后增加计数。正常中断路径使用原时钟代码。

[GUARANTEE]

四次返回后探针返回4；真实ticks至少推进两次。与后续线程首次恢复共用当前trapframe和恢复代码。

[SPECIFICATION]

Pre-Condition：idt和时钟已初始化，测试地址确实属于本次ELF。

Post-Condition：四次异常均返回其后续指令，无死循环；寄存器计数未被恢复破坏；时钟继续工作。受控页故障恢复是其他测试的独立注入，不当作正式异常处理新增能力。

## P3-I：虚拟内存页操作

[PROMPT]

任务：在 `code/kern/mm/pmm.c` 的function1区完成映射建立和撤销，维护PTE、物理页引用和TLB。

操作要求：实际修改文件，保留其他逻辑；允许一个static删除辅助函数。定位分配失败问题后，最小修正get_pte回滚和上层叶项防护。

输出要求：接口与pmm.h一致，保留LAB4标记并填写两位学号，不增加无关公开接口。

[RELY]

`pde_t/pte_t` 是uintptr_t；Sv39的PDX1/PDX0/PTX各9位，普通页4096字节。现有接口包括get_pte、pte_create、pte2page、page2ppn、page_ref_inc/dec、alloc_page/free_page、tlb_invalidate和flush_tlb。get_pte的create=false路径不能分配页。

迭代上下文：最小RV64探针已确认非叶U=1引发页故障。经具体修正确认，两处非叶项只置V，并将旧根U断言改为检查非叶U/A/D/R/W/X均为0；其他断言与评分测试保持。

[GUARANTEE]

```c
int page_insert(pde_t *pgdir, struct Page *page, uintptr_t la, uint32_t perm);
void page_remove(pde_t *pgdir, uintptr_t la);
pte_t *get_pte(pde_t *pgdir, uintptr_t la, bool create);
```

允许内部 `static void page_remove_pte(pde_t *, uintptr_t, pte_t *)`，不改变公开签名。

[SPECIFICATION]

### page_insert

Pre-Condition：pgdir/page有效，数据页由调用者持有；地址属于可处理的普通页路径。

Post-Condition：成功返回0，la映射到目标页且权限匹配，引用和实际翻译同步；失败返回-E_NO_MEM，目标页引用、旧映射和已有资源不变。

Case：空项建立新引用；同页重插仅更新权限，不多占引用；不同页替换撤销旧引用，旧页零引用时还页。中间级分配失败不留下半完成路径。

### page_remove

Pre-Condition：pgdir有效，调用地址可查询。

Post-Condition：存在映射时清项、失效翻译、减少引用，零引用页归还；不存在映射时不分配也不报错。重复删除不重复释放。

### get_pte

Pre-Condition：根表和地址有效；调用者明确是否允许创建普通页表路径。

Post-Condition：成功返回末级PTE地址；不创建且路径不存在、内存不足或遇到不支持的大页叶项时返回NULL。失败只撤销本次新分配的中间表，保留原路径。

Requirements：非叶项不携带叶权限；页表结构与叶项更新使用相应TLB同步，带编译器内存约束；不针对评分路径特判。

## P3-T：映射、引用和失败回滚验证

[PROMPT]

任务：为映射模块编写独立验收，验证返回值、PTE、引用、页数和真实访问结果。

操作要求：在新副本中包装分配入口注入失败，实际调用当前生产函数；不改变生产init和评分检查。

输出要求：保存失败原文和复测结果，分别指出元数据检查与实际MMU访问。

[RELY]

`void lab4_extra_pmm(void)` 在测试副本中运行。使用真实Page、nr_free_pages、boot_pgdir_va和页表接口，测试低地址区不覆盖内核。原框架的perm=0或仅W可作元数据测试；实际读写使用合法R/W组合。

[GUARANTEE]

覆盖空项、同页、换页、别名、重复删除、大页拒绝、第一次/第二次分配失败及已有路径下的失败；检查真实TLB替换与撤销后故障。

[SPECIFICATION]

Pre-Condition：保存进入前的父项、页数和引用，失败计数只对本次操作生效。

Post-Condition：成功映射的数据和别名一致；替换后实际读到新页；失败后状态守恒；已有父表不被回滚误删。原第二级分配失败测试曾检出少一页，修正后相同判据通过。测试退出0还需完整成功标记，非预期panic或超时均失败。

## P4-I：线程创建和初始化

[PROMPT]

任务：在 `code/kern/process/proc.c` 的function2区完成线程从PCB到可运行实体的创建闭环。

操作要求：只补本模块及必要static辅助函数，保留给定的PID/哈希、栈申请释放和入口函数；不实现用户地址空间复制或完整退出。

输出要求：六个函数实际落地，失败路径与资源取得配对，按当前布局构造首帧。

[RELY]

读取proc.h中的完整proc_struct。相关字段为state、pid、runs、kstack、need_resched、parent、mm、context、tf、pgdir、flags、name、list_link、hash_link。context为ra/sp/s0～s11；trapframe为36个RV64槽。KSTACKPAGE=2，MAX_PROCESS=4096，MAX_PID=8192。

可调用kmalloc/kfree、setup_kstack/put_kstack、get_pid/hash_proc/find_proc、wakeup_proc、set_proc_name、memset/memcpy和链表接口。boot_pgdir_pa是物理根地址，bootstack是启动栈。forkret调用forkrets进入__trapret；kernel_thread_entry使用s0函数与s1参数。

[GUARANTEE]

```c
static struct proc_struct *alloc_proc(void);
void proc_init(void);
int kernel_thread(int (*fn)(void *), void *arg, uint32_t clone_flags);
int do_fork(uint32_t clone_flags, uintptr_t stack, struct trapframe *tf);
static void copy_thread(struct proc_struct *proc, uintptr_t esp, struct trapframe *tf);
static int copy_mm(uint32_t clone_flags, struct proc_struct *proc);
```

[SPECIFICATION]

### alloc_proc

Pre-Condition：SLOB可用。

Post-Condition：失败返回NULL；成功返回安全空白PCB，state=UNINIT、pid=-1、pgdir为内核根物理地址，context/name等为零，两链节点可独立使用，尚未登记。

### proc_init

Pre-Condition：内存和异常基础可用，进程管理尚未初始化。

Post-Condition：列表和哈希有效；idle pid0、RUNNABLE、复用bootstack、parent/mm/tf为空、need_resched置位；current指向idle。init pid1、父为idle、独立栈、RUNNABLE，可按PID找到并命名init；总数为2，普通进程链表登记init。

### kernel_thread

Pre-Condition：current有效，fn和参数符合线程入口约定。

Post-Condition：临时tf清零，函数/参数及入口PC正确，状态位支持S态首次恢复；创建成功返回新PID，失败透传负错误码。

### do_fork

Pre-Condition：current和tf有效，stack参数与调用场景一致。

Post-Condition：成功后PCB、独立栈、mm/pgdir、首帧、parent、PID、列表/哈希、计数和RUNNABLE状态一致；返回PID。达到上限返回-E_NO_FREE_PROC；资源不足返回-E_NO_MEM；不支持的mm返回-E_INVAL。失败不登记、不唤醒，并释放已经取得的PCB/栈。

Requirements：可见登记和唤醒在中断保护内完成，不能先发布半初始化实体。

### copy_thread

Pre-Condition：proc拥有可用的两页内核栈，tf可读；非零esp由调用者保证可用。

Post-Condition：帧位于自身栈顶且对齐，内容复制完整，子a0为0；gpr.sp按esp或默认栈位置设置；context.ra=forkret，context.sp指向首帧。

### copy_mm

Pre-Condition：current和未发布proc有效。

Post-Condition：当前内核线程mm为空时成功，子mm为空、pgdir共享内核根；用户mm非空时返回-E_INVAL，不伪造复制成功。

## P4-T：创建、资源回收与 PID 验证

[PROMPT]

任务：验证PCB初态、首帧、成功登记和每类失败清理，并检查真实线程及PID回绕。

操作要求：在临时proc.c副本内调用static函数，故障包装只存在于副本；不要为可测试性扩展生产公开接口。

输出要求：同时记录资源归属、可见链表/哈希/计数和后续可用性；考虑SLOB可能缓存页。

[RELY]

测试函数 `static void lab4_extra_create(void)`，实际alloc_proc、copy_thread、kernel_thread和do_fork；heap/page失败包装及nr_process、proc_list、find_proc。

[GUARANTEE]

检查PCB所有基础字段、零context、链节点、显式esp和默认栈；注入PCB/栈失败、mm拒绝、数量上限；创建两个实际线程检查栈互异和PID查找；经真实接口登记高端PID后触发回绕。

[SPECIFICATION]

Pre-Condition：记录原线程数、列表和页/对象状态。

Post-Condition：失败未产生可见实体，资源可再次使用；成功实体的栈和父子关系正确。首帧在栈内且16字节对齐。PID为合法范围内未在用的值，回绕避开已登记项。

迭代：最初绕过接口插入任意PID破坏了get_pid缓存前提，随后修正测试登记方式，未修改正确的get_pid。

## P5-I：调度和上下文切换

[PROMPT]

任务：在proc.c的function3区、sched.c和switch.S完成空闲循环、调度选择、运行切换和寄存器迁移。

操作要求：分开调度策略与切换机制，按真实context偏移写汇编；不加入抢占或多核调度，不使用Sv32遗留lsatp。

输出要求：四个接口实际可链接、可运行，保持原中断状态语义。

[RELY]

proc_list/current/idleproc、PROC_RUNNABLE、need_resched/runs、list_next/le2proc、local_intr_save/restore和flush_tlb。`SATP_MODE_SV39=8`，MODE位于RV64 satp的高4位，根物理页号右移RISCV_PGSHIFT。

```c
struct context {
    uintptr_t ra, sp;
    uintptr_t s0, s1, s2, s3, s4, s5;
    uintptr_t s6, s7, s8, s9, s10, s11;
};
```

此处字段顺序与当前proc.h一致；汇编参数a0/a1分别指向from/to。

[GUARANTEE]

```c
void cpu_idle(void);
void schedule(void);
void proc_run(struct proc_struct *proc);
void switch_to(struct context *from, struct context *to);
```

[SPECIFICATION]

### cpu_idle

Pre-Condition：current为可用idle，进程管理已初始化。

Post-Condition：保持不返回循环；有need_resched时调用schedule，无需求时继续等待。

### schedule

Pre-Condition：current和链表有效。

Post-Condition：清除当前重调度请求，从当前之后或idle对应的表头扫描RUNNABLE；无候选回退idle。选中者runs加一，必要时切换。被切出的调用者需在后续重新获调度时才从原调用处返回。

### proc_run

Pre-Condition：目标可运行且context、栈、根表已准备；普通路径共享内核映射。

Post-Condition：转移时current、satp和执行现场均属于目标；原线程再次获调度后从原调用点继续，并恢复其调用前的中断状态。目标就是current时不重复切换。

Requirements：current更新、根表/TLB与context切换的中间状态不可被中断打断。

### switch_to

Pre-Condition：两个context指针可访问，目标ra/sp有效，调用者已完成临界区和根表准备。

Post-Condition：保存旧ra/sp/s0～s11，恢复目标14字段，沿目标ra继续；不负责选择线程或分配资源。使用64位访存，偏移与结构一致。

## P5-T：多轮调度、寄存器和 GDB

[PROMPT]

任务：以真实RV64执行验证多轮切换，并核对空集、单候选和首次运行链。

操作要求：测试副本中运行两个线程各32轮；用ABI正确的汇编探针保存调用者现场、设置s寄存器哨兵并调用真实schedule。策略边界包装与真实切换分开记录。

输出要求：独立核对顺序、寄存器、栈值、current/satp和SIE；保存客体GDB原始观察，不手改寄存器。

[RELY]

测试 `int lab4_probe_regs(void)`、两个worker、order序列及局部栈数据。`debug_lab4.py` 使用正常ELF和 `make debug` 启动QEMU，再连接gdb-multiarch。

[GUARANTEE]

检查64次主动让出后的交替顺序和数据保持；跳过UNINIT/SLEEPING/ZOMBIE；空集回退和单候选行为；初始SIE开关、两层嵌套及关中断切回。GDB观察kern_init、proc_init完成、schedule、proc_run、switch_to、forkret、forkrets、__trapret、线程入口、init_main十个位置。

[SPECIFICATION]

Pre-Condition：当前ELF和源码对应，端口未被其他任务占用。

Post-Condition：全部哨兵、sp/调用返回、局部值和顺序正确；切回后根表和SIE一致；首帧恢复真实进入fn(arg)。成功需全部断言和标记，超时不是通过。只结束本次启动的进程。

## P6-I：分段权限映射

[PROMPT]

任务：在pmm_init中另建规范内核页表，以普通页区分text、rodata和可写内存；在链接脚本给出页对齐边界。

操作要求：不沿启动大页继续向下走表。保留低地址自检和VMA/SLOB初始化，只调整建立正式根表所需代码。

输出要求：正常路径切换到完整新根表，不留下可绕过权限的粗别名。

[RELY]

KERNBASE、KERNEL_BEGIN_PADDR、当前npage/va_pa_offset；boot_alloc_page、boot_map_segment、enable_paging、flush_tlb；链接符号etext、erodata和内核数据边界。

[GUARANTEE]

修改 `void pmm_init(void)` 及 `tools/kernel.ld` 的段边界；复用现有内部映射接口，不新增用户地址空间接口。

[SPECIFICATION]

Pre-Condition：PMM可用，建立新表期间仍可通过启动映射访问代码、栈和分配页。

Post-Condition：text为RX、rodata为R、数据/BSS及剩余可管理RAM为RW；边界按页对齐。切根表前映射齐备，切后TLB同步，内核可继续运行。

## P6-T：实际权限和撤销访问

[PROMPT]

任务：先检查原粗映射能被段权限测试检出，再验证细映射的实际访问限制。

操作要求：临时副本加入受控故障恢复入口，不改变正式异常处理。普通读写与拒绝访问分别判定。

输出要求：记录PTE检查和四类真实故障，不只打印页表。

[RELY]

真实链接符号和get_pte；测试 `lab4_check_faults()`、`lab4_extra_fault(tf)` 及汇编访问/恢复标签。预期cause和badvaddr必须同时匹配。

[GUARANTEE]

检查text/rodata/data的PTE，实际写text、写rodata、执行data、访问刚撤销的映射。

[SPECIFICATION]

Pre-Condition：idt可用，测试地址对齐且确属相应段，故障恢复位置有效。

Post-Condition：四次分别触发预期页故障并返回测试后续点；正常读写不受破坏；无非预期panic后到达成功标记。该注入不进入正式trap.c。

## P7-I：固定地址内核栈变体

[PROMPT]

任务：作为正文兴趣探索，在独立变体中尝试两个线程使用相同虚拟栈区间、不同物理栈。对照Linux实际源码说明区别。

操作要求：只由测试运行器向副本注入，默认内核继续使用共享根表和直映栈。不要在旧sp上先换根表再继续执行C。

输出要求：给出可运行变体、公共过渡栈和保护页；保留默认路径。

[RELY]

现有kernel_thread、copy_thread、schedule和context；每线程根表复制共享高映射，栈别名为 `[0x7fffe000,0x80000000)`，下方一页不映射。PCB的kstack仍保留稳定直映地址，运行tf/sp使用别名。Linux对照版本为v6.12。

[GUARANTEE]

```c
static struct proc_struct *make_fixed_worker(unsigned id);
static int fixed_worker(void *argument);
static int lab4_fixed_experiment(void *argument);
void lab4_fixed_switch(struct context *from, struct context *to, uintptr_t satp);
```

以上仅在临时变体构建，不修改生产公开结构。

[SPECIFICATION]

Pre-Condition：代码、PCB和公共过渡栈在各根表均可访问；切换时中断关闭。

Post-Condition：两个线程根表和物理栈不同，但栈VA相同；首帧可恢复；切换先保存旧现场并进入公共过渡栈，再换根表、刷新TLB和恢复新sp。默认路径不受变体影响。

| 接口 | Pre-Condition | Post-Condition |
| --- | --- | --- |
| `make_fixed_worker` | id为0或1；新线程尚未获调度，分配器可用 | 返回已登记线程，其私有根表含两页栈别名及下方guard，tf/context使用别名，kstack保留直映地址 |
| `fixed_worker` | 运行在对应别名栈，id有效 | 完成32轮数据/寄存器检查及一次guard故障检查后置睡眠并让出，不返回到占位退出函数 |
| `lab4_fixed_experiment` | 当前为可运行的init，所有根表可共享高映射 | 两线程完成64轮和两次guard检查，比较地址并输出结果后SBI关机 |
| `lab4_fixed_switch` | 中断关闭，from/to及过渡栈在各根表可访问，目标satp有效 | 旧现场保存；在公共栈上切换根表并失效TLB；恢复目标ra/sp/s寄存器后转移执行 |

## P7-T：固定栈与保护页验证

[PROMPT]

任务：实际运行固定栈变体，验证栈数据独立和保护页拒绝访问。

操作要求：用真实sp、satp和物理栈记录，不以地址示意图代替运行；保持与正常共享根表测试分开。

输出要求：保存64次切换、两个线程的地址及各一次guard写故障，并写清实验范围。

[RELY]

`run_lab4.py --fixed-stack`、两个fixed_worker、寄存器探针、受控store page fault恢复；日志含两个物理栈和相同sp。

[GUARANTEE]

两个线程各32轮，局部cookie和寄存器保持，观察sp相同、物理栈不同；两次guard访问各出现预期故障。

[SPECIFICATION]

Pre-Condition：运行独立变体，目标保护页确实不映射。

Post-Condition：全部断言及成功标记通过后关机。受控guard访问只证明边界保护，不声称已经处理sp越界后的通用紧急栈恢复，不据此给出多核或性能结论。

## P8-A：Challenge 1 的分析与实测核对

[PROMPT]

任务：回答local_intr_save/restore如何实现中断控制，并结合本轮记录解释初始开、初始关和嵌套三种情况。

操作要求：读取当前sync.h和intr.c，不修改代码；回答对应本次S态、单hart环境。

输出要求：先给出保存、关闭和恢复的直接解释，再说明嵌套顺序和使用前提，引用已有SIE观察。

[RELY]

`__intr_save()` 检查 `read_csr(sstatus) & SSTATUS_SIE`，原来开启时调用intr_disable并返回1，否则返回0；`__intr_restore(bool flag)` 仅在flag非零时调用intr_enable。local_intr_save宏用do/while包装赋值。intr_enable/disable分别置位或清除SSTATUS_SIE。

本轮探针已验证初始SIE=0/1、两层嵌套、同线程proc_run和实际切回，不需要另造运行记录。

[GUARANTEE]

形成Challenge第1项的完整文字回答，解释flag的含义、嵌套恢复次序及单hart范围；不新增函数或虚构实验结果。

[SPECIFICATION]

Pre-Condition：解释与当前真实代码一致，临界区内不自行开启中断，恢复按相反顺序进行。

Post-Condition：明确原来关闭时退出该层不会启用中断；外层从开启进入时，内层先退出仍保持关闭，外层退出才开启。区分SIE位、完整CSR保存和多核互斥，文字结论能与已有观察对应。

## P9-A：Challenge 2 的分页比较与接口取舍

[PROMPT]

任务：回答不同分页模式的共同点，以及get_pte中的两个非叶步骤为何相似；再讨论查找和分配合并或拆分的取舍。

操作要求：对照当前get_pte和RISC-V规范，不要求实现或运行Sv32/Sv48，也不为回答强制重构公开接口。

输出要求：给出模式比较表、两段相似代码的层级解释，以及结合本轮分配失败的有条件建议。

[RELY]

Sv32为RV32两级，每级10位索引、4字节PTE、每表1024项；Sv39/Sv48为RV64的三级/四级，每级9位索引、8字节PTE、每表512项。普通页均4KiB。当前get_pte使用PDX1、PDX0定位两个非叶步骤，最后按PTX返回末级项。

本轮只实际运行Sv39。第二级分配失败留下中间页表已被独立测试发现，并通过本次资源回滚修正。

[GUARANTEE]

分别回答Challenge第2项的两个子问：模式与重复结构、接口设计。给出查询副作用、错误回滚和调用者复杂度方面的比较。

[SPECIFICATION]

Pre-Condition：规范比较与本机运行证据分开，当前接口仍为get_pte(pgdir,la,create)。

Post-Condition：表中级数/索引/PTE/页大小正确；解释Sv39为何有两个类似步骤，且不把末级PTE定位说成分配数据页。接口建议说明适用条件：当前可保留公开接口并补回滚，复杂功能下可拆只读查询和确保路径的内部接口；不声称拆函数本身就能消除资源泄漏。
