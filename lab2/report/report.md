# Lab 2：物理内存发现与页分配

小组成员：邹瑛琦（2412744）、丁子昂（2411130）  
实验记录日期：2026-10-21。

## 实验目标与整体流程

本实验从设备树（DTB）读取 QEMU 提供的物理内存范围，建立每个物理页对应的 `struct Page` 描述符，只把未被 OpenSBI、内核和描述符数组占用的完整页面交给物理内存管理器。然后理解 First-Fit，实现 Best-Fit 和 Buddy System 两种连续页分配算法，分别运行内核自检。引导路径为：OpenSBI → `kern_entry` 建立初始页表和栈 → `kern_init` 解析 DTB → `pmm_init` 初始化页分配器 → 自检。

## 练习 1：物理内存发现与初始化

实现位置：`kern/mm/pmm.c` 的 `page_init`（`//lab2 function1 2411130`）。

1. `dtb_init` 先解析 `/memory` 节点，得到物理内存基址与容量。`page_init` 检查数据有效并防止地址加法溢出；当前内核的页描述符索引以 `DRAM_BASE` 为起点，所以要求设备树的基址与之相符。
2. 设置 `va_pa_offset`，用于将内核虚拟地址换算为物理地址。将内存末端限制在此内核当前可映射的 `PHYSICAL_MEMORY_END` 内，再计算 `npage`。
3. 把 `pages` 放在内核符号 `end` 后第一个页边界。对所覆盖 DRAM 的所有 `Page` 描述符先设置保留标志，防止误分配固件、内核和描述符自身。
4. 从描述符数组末尾向上按 4 KiB 对齐，至内存末端向下按 4 KiB 对齐，仅将非空的完整页区间传给 `init_memmap`。这样 OpenSBI、内核、描述符数组以及零碎页尾均不会进入空闲链表。

在本机的 128 MiB QEMU 环境中，DTB 报告 `[0x80000000, 0x88000000)`，本次编译生成的空闲区间为 `[0x80347000, 0x88000000)`。具体起点会随内核大小和 `struct Page` 数量变化，不应写死。

## 练习 2：First-Fit 分析与 Best-Fit 实现

`kern/mm/default_pmm.c` 已提供 First-Fit：空闲块按物理地址排序；申请 `n` 页时从头查找首个大小不少于 `n` 的块，必要时拆分；释放时按地址插入，并与物理地址相邻的前后空闲块合并。其优点是找到第一个合适块即可停止，代码和查找路径较简单；缺点是低地址区域可能逐渐积累较小碎片。

对指导书问题“原有 First-Fit 是否有进一步改进空间”的回答是：有。可以采用 next-fit 减少总从链表头搜索造成的低地址偏向；也可以按块大小建索引减少搜索时间。但这些方案会增加状态维护成本，不能保证彻底消除外部碎片。

`kern/mm/best_fit_pmm.c` 中实现的 Best-Fit 保持同样的地址有序链表，但分配时扫描完整链表，挑选**满足请求且页数最少**的块；相同大小时自然选较低地址的块。若块比请求大，就把剩余部分留在原位置。释放时按地址插入，先尝试与前块合并，再尝试与后块合并，并维护 `nr_free` 与 `PageProperty`。`pmm.c` 已切换到 `best_fit_pmm_manager`。课程提供的 `basic_check` 和 `best_fit_check` 未修改。

Best-Fit 的目的不是保证永远没有碎片，而是尽量不拆分大块；它每次分配通常必须遍历全部空闲块，可能产生很小且难再利用的剩余块。进一步优化可以为不同大小的空闲块建立索引或分级链表，以减少全表扫描，但会增加维护成本。本次按必做要求使用地址有序链表，便于相邻块合并。

## 练习 3：Buddy System（伙伴系统）

`kern/mm/buddy_pmm.c`（`// lab2 function2-3 2411130`）实现了另一套 `pmm_manager`，不改动课程提供的 Best-Fit 检查函数。每个空闲链表只存一种大小为 `2^k` 页的块。初始化时把设备树发现的空闲页区间拆成尽可能大的、按块大小对齐的 2 的幂块；申请 `n` 页时向上取整到最小的 `2^k >= n`，找相应或更大的块，逐层拆成两个伙伴；释放时按页号异或块大小找伙伴，只有对方也是同阶空闲块才合并，再逐层向上尝试。`Page.property` 记录空闲块大小，并在已分配块首页记录实际占用容量，以核验释放请求。

本实现的 `nr_free_pages()` 统计尚未占用的物理页数。因此申请 3 页实际占 4 页、申请 5 页实际占 8 页，这些取整会产生**内部碎片**。伙伴算法用分级链表和快速合并换取较好的分配效率，却不能满足任意大小请求都精确占页。检查函数覆盖 1、3、5 页申请、向上取整、释放前后空闲页计数、零页与过大请求，以及“不能留下可合并的同阶空闲伙伴”这一不变量。初始化的起始地址并非块边界，也由按页号对齐的拆分逻辑处理。

为了保留指导书要求的 Best-Fit 成果，默认仍选 `best_fit_pmm_manager`；用 `mingw32-make -B DEFS=-DPMM_BUDDY` 可编译 Buddy 版本。必须加 `-B` 强制重新编译，因为 Makefile 不会因仅改变编译参数自动重建目标文件。演示结束后用 `mingw32-make -B` 恢复默认版本。

## 调试与验证记录

最初代码可编译，但 QEMU 只打印 OpenSBI，不进入内核。检查裸镜像后发现，`kern_entry` 被写在普通 `.text` 段，链接脚本虽优先放置 `.text.kern_entry`，但该段为空，裸镜像首字节并非入口指令。因此把入口汇编改为 `.text.kern_entry`，让它位于 `ucore.img` 的开头。又将 `Makefile` 的运行目标和 `tools/grade.sh` 的模拟器参数改为已验证可用的 `-kernel bin/ucore.img`。仅把镜像放进内存（`-device loader`）并不等于告诉 OpenSBI 从该镜像入口执行。

本机使用 SiFive GCC-Metal 10.2.0、GNU Make 4.2.1、QEMU 5.1.0。完整构建通过。运行默认 Best-Fit 镜像后，QEMU 的关键输出摘录如下；复现命令及测试边界见 [核验记录](verification.md)：

```text
Physical Memory from DTB:
  Base: 0x0000000080000000
  Size: 0x0000000008000000 (128 MB)
memory management: best_fit_pmm_manager
physical memory map: [0x0000000080000000, 0x0000000088000000], free: [0x0000000080347000, 0x0000000088000000]
check_alloc_page() succeeded!
```

另外，先在独立临时副本中运行课程自带的 `tools/inject.py`，再编译并运行该副本，得到：

```text
[Test 1] Page Init: PASS
[Test 2] Best-Fit: PASS
```

在同一源码上以 `DEFS=-DPMM_BUDDY` 完整重编译后，QEMU 运行得到：

```text
memory management: buddy_pmm_manager
buddy checks: split, round-up, free and counts passed
check_alloc_page() succeeded!
```

第一轮 Buddy 自检只检查分配后的页数恢复，不能证明伙伴真正合并，因此又增加了对所有空闲链表的同阶伙伴检查，并重编译、重启 QEMU 验证通过。

临时检查副本不改动提交用源码；内核完成打印后会进入预期的无限循环，在 Windows PowerShell 中可按 `Ctrl+C` 停止 QEMU。这里 `Ctrl+C` 是结束模拟器，并非内核自己正常关机。

## 与操作系统知识的联系、尚未实现的部分

物理页管理解决的是“哪些 RAM 页可安全分配、如何减少外部碎片”；它与页表不同：页表负责“虚拟地址如何映射到物理地址”。本实验启动时已有引导页表，Lab 2 的重点是发现可用物理页并提供分配/释放接口。`Page` 数组是管理元数据，不是实际内存页内容。First-Fit 与 Best-Fit 的地址有序链表便于合并相邻空闲块，但有外部碎片和查找开销；Buddy 的分级链表便于拆分合并，但非 2 的幂请求有内部碎片。当前内核仍没有完整的进程地址空间、按需分配、换页、并发锁保护或通用设备内存管理；不能把一次自检通过理解为整个操作系统已完成。指导书中的硬件内存探测思考题及 SLUB 是选做 Challenge，本次未实现；QEMU 源码级页表查询分支任务也未执行，不能声称完成。

## 本次使用的提示词与设计约束

针对任务分析、`page_init`、First-Fit、Best-Fit、Buddy 实现与测试，分别给出目标、约束和验收条件，见 [关键提示词与任务规范](prompt.md)。其中 Buddy 的实现提示词和测试提示词分开写，便于分别检查算法与测试覆盖。分析、修正和运行过程见 [AI 辅助分析与修正记录](ai-process.md)。

对分配器为何这样设计、测试覆盖到什么程度，可再看 [分配器复核](allocator-review.md)和[核验记录](verification.md)。

## 参考

- `D:\操作系统\oslab-lab2-full.pdf`（课程 Lab 2 完整指导书）
- [Lab 2 在线指导书](http://oslab.mobisys.top/lab2026/_book/lab2/lab2.html)
