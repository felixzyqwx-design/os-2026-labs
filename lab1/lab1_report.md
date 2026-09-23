# Lab 1：最小可执行内核与 RISC-V 启动流程

## 基本信息

| 项目 | 内容 |
| --- | --- |
| 小组成员 | 邹瑛琦（2412744）、丁子昂（2411130） |
| 代码仓库 | <https://github.com/felixzyqwx-design/os-2026-labs> |
| 实验系统 | WSL2，Ubuntu 24.04.1 LTS |
| 构建工具 | GNU Make 4.3 |
| 交叉编译器 | riscv64-unknown-elf-gcc 13.2.0 |
| 链接器 | GNU ld 2.42 |
| 调试器 | GNU GDB 15.1（通过 `riscv64-unknown-elf-gdb` 兼容链接调用） |
| 模拟器 | QEMU 8.2.2，内置 OpenSBI 1.3 |

本实验没有需要补全的内核功能代码。我们的工作是读懂最小内核，完成编译和运行，并用 GDB 验证 CPU 从复位地址进入 OpenSBI、再进入 uCore 内核的过程。

## 1. 本章整体逻辑线

本章从“怎样得到一个能运行的内核”展开，顺序如下：

```text
C/汇编源文件
→ RISC-V 交叉编译得到目标文件
→ kernel.ld 安排内存布局并链接为 ELF
→ objcopy 提取裸二进制镜像 ucore.img
→ QEMU 创建 RISC-V virt 机器并预装镜像
→ CPU 从 0x1000 的 MROM 复位代码开始执行
→ 跳到 0x80000000 的 OpenSBI
→ OpenSBI 完成初始化并以 S 模式跳到 0x80200000
→ kern_entry 设置内核栈并跳到 kern_init
→ kern_init 处理 .bss、输出启动信息并进入死循环
```

这条逻辑线同时涉及构建过程和运行过程。前半部分解决“代码怎样成为指定地址上的 RISC-V 镜像”，后半部分解决“上电后的 CPU 怎样找到并执行这份镜像”。

## 2. 项目执行流与核心模块

| 文件或模块 | 本实验中的职责 |
| --- | --- |
| `Makefile` | 组织编译、链接、`objcopy`、QEMU 启动和 GDB 连接 |
| `tools/kernel.ld` | 指定 RISC-V 架构、入口 `kern_entry`、基址 `0x80200000` 和各段布局 |
| `kern/init/entry.S` | 预留 8192 字节内核栈，初始化 `sp`，尾调用 `kern_init` |
| `kern/init/init.c` | 按链接器符号处理 `.bss`，打印启动信息，随后保持内核运行 |
| `kern/libs/stdio.c` | 实现 `cprintf`、`vcprintf` 和字符输出回调 |
| `libs/printfmt.c` | 解析格式字符串，并逐字符调用上层传入的输出函数 |
| `kern/driver/console.c` | 将 `cons_putc` 转发到 SBI 字符输出服务 |
| `libs/sbi.c` | 按 SBI 调用约定设置寄存器并执行 `ecall` |

### 2.1 链接布局和镜像

`kernel.ld` 使用 `ENTRY(kern_entry)` 指定入口，并把位置计数器设置为 `0x80200000`。本机 ELF 的主要段为：

```text
.text    0x80200000  size 0x4c0
.rodata  0x802004c0  size 0x270
.data    0x80201000  size 0x2000
.sdata   0x80203000  size 0x8
```

ELF 文件保存了入口、段、符号和调试信息，适合链接器、加载器和 GDB 使用。`objcopy --strip-all -O binary` 生成的 `ucore.img` 是裸二进制镜像，供 QEMU 启动。两者包含的机器代码对应，但用途和保留的元数据不同。

链接脚本在 `.data/.sdata` 之后定义 `edata`，在 `.bss` 之后定义 `end`。`kern_init` 用下面的代码建立 C 语言规定的未初始化全局数据为零的环境：

```c
extern char edata[], end[];
memset(edata, 0, end - edata);
```

本次生成的镜像没有独立的非空 `.bss` 内容，实测 `edata` 和 `end` 都是 `0x80203008`，所以这次 `memset` 的长度为 0。代码具备清零机制，不等于本次运行真的清零了若干字节。

### 2.2 输出调用链

内核没有 glibc，`#include <stdio.h>` 引入的是项目自己的头文件。启动字符串的输出路径是：

```text
cprintf
→ vcprintf
→ vprintfmt
→ cputch
→ cons_putc
→ sbi_console_putchar
→ sbi_call
→ ecall
→ OpenSBI 控制台服务
```

`sbi_call` 把服务号放入 `a7/x17`，参数放入 `a0-a2/x10-x12`，随后执行 `ecall`。内核处在 S 模式，OpenSBI 服务处在 M 模式，因此不能把它当作同一特权级中的普通 C 函数调用。`ecall` 提供了受控的跨级入口。

## 3. 编译与运行结果

### 3.1 干净构建

执行：

```bash
make clean
make
```

关键输出如下：

```text
+ cc kern/init/entry.S
+ cc kern/init/init.c
+ cc kern/libs/stdio.c
+ cc kern/driver/console.c
+ cc libs/printfmt.c
+ cc libs/readline.c
+ cc libs/sbi.c
+ cc libs/string.c
+ ld bin/kernel
riscv64-unknown-elf-objcopy bin/kernel --strip-all -O binary bin/ucore.img
```

ELF 头和关键符号：

```text
Class:                             ELF64
Machine:                           RISC-V
Entry point address:               0x80200000

0000000080200000 T kern_entry
000000008020000a T kern_init
0000000080201000 D bootstack
0000000080203000 D bootstacktop
0000000080203008 D edata
0000000080203008 D end
```

### 3.2 QEMU 启动

本机 QEMU 8.2.2 使用旧式
`-device loader,file=bin/ucore.img,addr=0x80200000` 时，OpenSBI 显示的下一阶段地址是 0，无法进入内核。将 `qemu` 和 `debug` 目标改为 `-kernel bin/ucore.img` 后，QEMU 会向 OpenSBI 提供正确的下一阶段入口。

实际启动输出的关键部分为：

```text
OpenSBI v1.3
Firmware Base             : 0x80000000
Domain0 Next Address      : 0x0000000080200000
Domain0 Next Mode         : S-mode
(THU.CST) os is loading ...
```

网页示例使用较旧的 QEMU/OpenSBI，输出和参数与本机不同。这里记录的是本机结果。内核输出后执行 `while (1)`，因此限时运行最终由 `timeout` 结束是预期现象，不是启动失败。

## 4. 练习 1：理解内核入口操作

### 4.1 问题与静态分析

入口代码是：

```asm
kern_entry:
    la sp, bootstacktop
    tail kern_init

.section .data
    .align PGSHIFT
bootstack:
    .space KSTACKSIZE
bootstacktop:
```

头文件给出的常量为：

```text
PGSIZE     = 4096
PGSHIFT    = 12
KSTACKPAGE = 2
KSTACKSIZE = 8192
```

`bootstack` 到 `bootstacktop` 是链接时预留的 8192 字节空间。RISC-V 栈向低地址增长，所以空栈的初始 `sp` 应指向这片空间的高地址 `bootstacktop`。`la sp, bootstacktop` 只是把符号地址装入寄存器，不是在运行时申请内存。

`tail kern_init` 是尾调用伪指令。这里不需要保存新的返回地址，因为 `kern_init` 被声明为 `noreturn`，最后也确实进入无限循环。

### 4.2 GDB 操作与观察

启动两个终端，分别运行：

```bash
make debug
make gdb
```

在 `kern_entry` 处设置断点后，得到：

```text
pc = 0x80200000
sp = 0x80046eb0
ra = 0x8000ae9a

bootstack    = 0x80201000
bootstacktop = 0x80203000
bootstacktop - bootstack = 8192
```

反汇编结果为：

```text
0x80200000 <kern_entry>:    auipc sp,0x3
0x80200004 <kern_entry+4>:  mv    sp,sp
0x80200008 <kern_entry+8>:  j     0x8020000a <kern_init>
```

单步结果：

```text
执行前：
pc = 0x80200000, sp = 0x80046eb0

执行 auipc 后：
pc = 0x80200004, sp = 0x80203000

完成 la 展开指令后：
pc = 0x80200008, sp = 0x80203000

执行 tail 后：
pc = 0x8020000a <kern_init>
sp = 0x80203000
ra = 0x8000ae9a
```

本次链接中，`la` 展开为 `auipc` 和一条显示为 `mv sp,sp` 的指令。第一条已经计算出 `bootstacktop`，第二条没有改变结果。`tail` 展开为直接跳转，执行前后 `ra` 都是 `0x8000ae9a`。

GDB 曾把地址 `0x80203000` 同时标成 `<SBI_CONSOLE_PUTCHAR>`。这是多个 `.data` 符号地址重合造成的符号显示，不表示栈指针指向某个函数；结合 `bootstacktop` 的符号地址和 8192 字节地址差，可以确定这里是内核栈顶。

### 4.3 结论

`la sp, bootstacktop` 为随后执行的 C 函数准备有效的内核栈。`tail kern_init` 把控制权交给不返回的 C 入口，同时不建立多余的返回链。源码、符号地址和单步结果一致。

## 5. 练习 2：使用 GDB 验证启动流程

### 5.1 调试方法

我们重新启动了一个停在复位状态的 QEMU 会话，没有复用练习 1 已经运行到内核入口的会话。主要命令为：

```gdb
info registers pc
x/8i 0x1000
break *0x80000000
continue
info registers pc
x/8i 0x80000000
break *0x80200000
continue
info registers pc sp
x/4i 0x80200000
```

### 5.2 复位地址 `0x1000`

连接 GDB 后，初始 PC 为：

```text
pc = 0x1000
```

反汇编结果：

```text
0x1000: auipc t0,0x0
0x1004: addi  a2,t0,40
0x1008: csrr  a0,mhartid
0x100c: ld    a1,32(t0)
0x1010: ld    t0,24(t0)
0x1014: jr    t0
```

这段 MROM 代码准备 hart ID、设备树等启动参数，从固定位置取出下一阶段入口，然后用 `jr t0` 跳转。它不是 uCore 的代码。

`x/8i 0x1000` 还会把 `0x1018` 之后的内容显示成 `unimp` 等“指令”，但真正的顺序执行在 `0x1014: jr t0` 已经改变了 PC。后续位置存有前面 `ld` 所读取的入口和参数数据，只是被 GDB 按指令格式强制解释，不能把它们写成实际执行的指令。

### 5.3 OpenSBI 入口 `0x80000000`

断点成功命中：

```text
Breakpoint 1, 0x0000000080000000 in ?? ()
pc = 0x80000000
```

入口附近的实际指令为：

```text
0x80000000: add s0,a0,zero
0x80000004: add s1,a1,zero
0x80000008: add s2,a2,zero
0x8000000c: jal 0x80000580
0x80000010: add a6,a0,zero
0x80000014: add a0,s0,zero
0x80000018: add a1,s1,zero
0x8000001c: add a2,s2,zero
```

命中该地址证明控制权到达 OpenSBI 固件入口区域。OpenSBI 运行在 M 模式并负责机器级初始化，这是固件与平台约定；本实验没有逐条跟踪它内部的全部初始化代码，因此不对未观察的细节作额外推断。

### 5.4 内核入口 `0x80200000`

第二个断点同样命中：

```text
Breakpoint 2, kern_entry () at kern/init/entry.S:7
pc = 0x80200000 <kern_entry>
sp = 0x80046eb0

0x80200000 <kern_entry>:    auipc sp,0x3
0x80200004 <kern_entry+4>:  mv    sp,sp
0x80200008 <kern_entry+8>:  j     0x8020000a <kern_init>
0x8020000a <kern_init>:     auipc a0,0x3
```

OpenSBI 的启动输出同时给出了 `Domain0 Next Mode : S-mode`，因此这里是固件向 S 模式内核的移交点。

本实验中的镜像由 QEMU 在虚拟 CPU 开始执行前预装。OpenSBI 初始化后跳到 QEMU 提供的下一阶段入口。我们没有观察到 OpenSBI 在运行时从硬盘逐字节复制内核，所以不把“内核加载”写成 OpenSBI 本次实际执行的磁盘读取过程。

### 5.5 启动链结论

本机观察到的启动链为：

```text
0x1000       QEMU virt 的 MROM/复位跳转代码
    ↓
0x80000000  OpenSBI 固件入口，完成机器级初始化
    ↓
0x80200000  kern_entry，开始执行 uCore
    ↓
设置 sp → kern_init → 处理 .bss → cprintf/SBI 输出 → 死循环
```

三个断点分别标记硬件复位代码、固件和操作系统内核的责任边界。

## 6. 重要知识点与 OS 原理的对应

| 实验知识点 | 对应的 OS 原理 | 关系和差异 |
| --- | --- | --- |
| MROM → OpenSBI → 内核 | 分阶段启动、bootloader | 都是在上一阶段建立最小环境后移交控制权；本实验由 QEMU 预装镜像，没有实现真实磁盘引导 |
| M 模式到 S 模式 | 特权级和隔离 | OpenSBI 管理机器级资源，内核运行在较低的 S 模式；PC 跳转和权限切换是两个相关但不同的问题 |
| `ecall` 调用 SBI | 受控跨特权级调用 | S 模式用 `ecall` 请求 M 模式服务，形式上类似以后 U 模式通过系统调用请求内核服务 |
| `kernel.ld` | 程序地址空间和装载 | 链接脚本决定符号和段预期出现的位置；加载过程负责让内存内容符合这个布局 |
| ELF 与裸 bin | 可执行文件格式 | ELF 保存段表、入口和符号，bin 主要是连续机器码；本实验分别把它们用于调试和启动 |
| `sp` 与内核栈 | ABI、函数调用 | C 函数依赖合法栈；本实验只有启动核的一块静态栈，还没有进程或线程各自的内核栈 |
| 交叉编译器 | 目标 ISA | 编译器运行在 x86 主机上，但输出 RISC-V 指令；QEMU 再模拟这些目标指令的执行 |
| `.bss` 清零 | C 运行环境 | 普通应用由加载器/运行时准备零初始化数据；裸内核需要自己完成相应初始化 |

## 7. 本实验尚未覆盖的 OS 内容

- 中断和异常：当前内核没有建立完整的 trap 入口，也没有处理中断源。
- 虚拟内存：尚未启用页表和地址转换，链接地址可以直接按当前物理内存布局理解。
- 物理页管理：还没有探测、划分和分配可用物理内存。
- 进程、线程与调度：这里只有一条启动执行流，没有上下文切换和调度器。
- 用户态与系统调用：本实验的 `ecall` 是 S 模式请求 SBI 服务，还不是用户程序请求内核服务。
- 同步互斥：没有并发执行实体，也没有锁、信号量或管程。
- 文件系统和设备驱动：启动信息借助 OpenSBI 控制台输出，没有实现通用文件接口或完整设备驱动。

这些内容依赖更完整的内存管理、异常处理和执行环境，不属于这个“能启动并打印一句话”的最小内核。

## 8. AI 协作全过程记录

以下是从需求确认到报告交付的全过程记录。为保持可读性，较长回复按实际结论、命令和输出整理；所有影响方案的提问、测试、失败与修正都予以保留。系统提示、隐藏推理和账号凭据不属于作业交互内容。

### 8.1 明确实验任务

用户最初说明自己不了解课程实验，要求先弄清 Lab 1 到底做什么，再给出方案，确认后才能执行。AI 阅读课程网页、环境文档和本地 `lab1` 源码后，将任务收敛为：搭建 RISC-V 工具环境，编译运行最小内核，用 GDB 回答两道练习，最后根据实际证据写报告。源码搜索没有发现 Lab 1 的 `TODO`、`YOUR CODE` 或待补全练习，课堂记录后来也确认本实验无需写功能代码。

### 8.2 评估环境配置对现有工作的影响

用户询问配置环境是否会影响正在运行的代码。AI 先区分 Windows 主机与 WSL 环境，说明工具链和 QEMU 主要安装在 WSL 中，通常不会改动现有项目；可能影响当前工作的操作是启用虚拟化、重启或占用较多 CPU。之后只有在用户明确回复“可以开始配置”后才继续。

### 8.3 修复并验证 WSL2

WSL2 起初无法正常启动。检查后将 Windows 启动项 `hypervisorlaunchtype` 设为 `Auto`，重启后 Ubuntu 24.04.1 LTS 恢复正常。随后验证 Make、RISC-V GCC/binutils、GDB Multiarch 和 QEMU，并建立兼容链接：

```text
/usr/local/bin/riscv64-unknown-elf-gdb -> /usr/bin/gdb-multiarch
```

最终工具版本就是报告开头所列版本。该阶段没有修改用户正在运行的其他项目代码。

### 8.4 先提交执行方案，再开始实验

用户要求“先把完成 Lab1 的方案给我看看”。AI 将实验拆为环境基线、干净构建、练习 1、练习 2、模块理解、报告和最终验证，并明确不运行仓库中不存在的 `tools/grade.sh`，不编造截图或地址。用户随后提供两位成员信息，要求建立仓库，并规定执行到写报告前停止。

### 8.5 建立 GitHub 仓库

AI 使用已经登录的 GitHub CLI 创建仓库 `felixzyqwx-design/os-2026-labs`，将 `实验课` 作为仓库根目录，使用 `lab1` 分支，并配置作者为邹瑛琦。初始提交为：

```text
38285b1 chore: initialize OS lab repository
```

同时添加 `.gitignore`，避免提交 `bin/`、`obj/` 等构建产物。

### 8.6 发现旧 QEMU 参数不兼容并修正

第一次按网页旧式参数运行时，QEMU 8.2.2 能进入 OpenSBI，但显示：

```text
Domain0 Next Address : 0x0000000000000000
```

内核没有得到正确入口。AI 根据实际输出检查 Makefile，将 `qemu` 和 `debug` 目标从旧式 `-device loader,file=...,addr=0x80200000` 改为 `-kernel $(UCOREIMG)`。修改后下一阶段地址变为 `0x80200000`，并出现内核启动字符串。这个修改解决的是工具版本兼容问题，不是补写内核功能。

### 8.7 干净构建和基础运行验证

执行 `make clean && make` 后，交叉编译、链接和 `objcopy` 都成功。随后用 `readelf` 和 `nm` 核对 ELF64、RISC-V 架构、入口及关键符号，再限时执行 `make qemu`。观察到 OpenSBI 1.3、S 模式下一阶段入口和内核输出。因为内核最后死循环，AI 将超时退出解释为预期行为，并检查没有遗留 QEMU 进程。

### 8.8 练习 1 的单步验证

AI 先从 `mmu.h`、`memlayout.h` 和 `entry.S` 算出栈大小 8192 字节，再用 GDB 在 `kern_entry` 断下。实测 `bootstack` 与 `bootstacktop` 地址差为 8192，单步后 `sp` 变为 `0x80203000`。继续执行到 `kern_init`，`ra` 保持 `0x8000ae9a`。由此确认 `la` 设置的是静态预留栈顶，`tail` 没有建立返回链。

调试中 GDB 把 `0x80203000` 同时显示为另一个数据符号。AI 对照链接符号后说明这是同址符号别名，不是栈指向函数。

### 8.9 练习 2 的启动链验证及一次命令错误

AI 新建调试会话，在 `0x1000`、`0x80000000` 和 `0x80200000` 设置或命中断点。第一次批处理命令中的 `$pc` 被外层 shell 提前展开，导致两段 `x/i $pc` 显示了错误地址。断点命中结果虽然有效，但这部分反汇编没有被采用。

AI 随即退出该 QEMU 会话，从复位状态重开，改用明确地址 `x/8i 0x80000000` 和 `x/4i 0x80200000`。第二次输出正确显示三段代码，形成了本报告练习 2 的证据。最后正常退出 QEMU，并再次检查无残留进程。

### 8.10 在报告前按用户要求停止

完成构建、两道练习和源码分析后，AI 检查 `lab1_report.md` 不存在，然后停止。此时只向用户汇报证据，没有提前写报告。

### 8.11 根据课堂记录重新审校方案

用户补充课堂会议纪要和文字记录，说明老师重视完整 AI 交互过程，不要求花哨模板。AI 重新对照课程网页的实验目的、练习和报告要求，把原先偏传统的报告结构改为“精简技术正文 + 完整 AI 协作记录”。同时确定三个表述边界：

- QEMU 8.2.2 满足课程网页“4.1.0 以上”的条件，但启动参数与旧示例不同；
- QEMU 负责预装本次内核，OpenSBI 负责初始化和最终移交控制权；
- GDB 将 MROM 后的数据按指令显示时，不能把这些内容当成真实执行流。

用户确认仓库可以公开，并授权开始写报告。本报告随后依据已经保存的命令输出、源码和调试结果完成。

## 9. 实际收获与边界

这次实验最有用的部分是把“开机后自动出现一行输出”拆成了可以逐段验证的执行链。遇到旧 QEMU 参数失效时，单看“系统没输出”很难判断问题在哪；OpenSBI 的下一阶段地址和三个 GDB 断点把问题定位到了镜像交付方式，而不是内核 C 代码。

我们现在能够根据源码和寄存器解释入口栈、尾调用、ELF 布局和 SBI 输出，也能区分网页示例与本机行为。实验没有调试 QEMU 宿主程序内部的镜像装载实现，也没有覆盖后续实验中的虚拟内存、中断和进程管理。仓库中没有 `tools/grade.sh`，因此本报告不声称通过了 `make grade`。
