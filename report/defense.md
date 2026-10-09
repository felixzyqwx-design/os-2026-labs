# Lab 1 答辩准备

成员：邹瑛琦（2412744）、丁子昂（2411130）。本手册根据当前 `lab1` 代码、2026 年 10 月 9 日复测和[课程 Lab 1](http://oslab.mobisys.top/lab2026/_book/lab1/lab1.html)整理。

## 1. 先掌握这段解释

> 我们这次运行的是一个最小 RISC-V 内核。源文件交叉编译后，由链接脚本安排到 `0x80200000`，再生成裸镜像。QEMU 预装镜像，CPU 从 `0x1000` 的复位代码进入 `0x80000000` 的 OpenSBI，固件再把控制权交给 S 模式的内核。内核入口先设置 8192 字节的栈，再尾调用 C 入口，最后通过 SBI 打印启动字符串。我们用 GDB 看到了三个启动阶段，也验证了栈指针和返回地址的变化。

先对照源码讲一遍，再脱离文字讲一遍。能解释每个箭头发生了什么，就能展开回答大部分问题。

几个常用词可以先这样理解：`pc` 是指令位置，`sp` 是当前栈顶，`ra` 是返回地址；hart 是一个硬件执行线程，本实验只启用一个；设备树描述硬件地址和配置；ABI 约定函数如何传参、使用栈和寄存器；`mcause`、`mepc` 等 CSR 保存处理器的控制与异常状态。

## 2. 约五分钟的现场展示

### 准备终端和文件

在两个终端进入 Ubuntu。Windows PowerShell 可运行：

```powershell
wsl.exe -d Ubuntu
```

两个 Ubuntu 终端都进入：

```bash
cd '/mnt/d/Felix/Desktop/大学复习/大三上/专业课/操作系统/实验课/code'
```

在 VS Code 打开 `entry.S`、`init.c`、`kernel.ld` 和 `sbi.c`。显示报告中的结果图作为对照。

### 第一段：构建与启动，约一分钟

终端 A：

```bash
make clean
make
riscv64-unknown-elf-readelf -h bin/kernel
riscv64-unknown-elf-nm -n bin/kernel
make qemu
```

指出 ELF64、RISC-V 和入口 `0x80200000`，展示 OpenSBI 的下一跳地址、S 模式及 `(THU.CST) os is loading ...`。

可以这样解释：

> 编译生成了用于调试的 ELF 和用于启动的裸镜像。OpenSBI 的下一跳地址对应内核入口，最后这行字符串来自 `kern_init`。

按 `Ctrl+A`，松开后按 `X`，结束这一轮 QEMU。

### 第二段：启动链，约一分半钟

终端 A 运行 `make debug`，它会停住虚拟 CPU。终端 B 运行 `make gdb`，随后在 GDB 输入：

```gdb
set pagination off
info registers pc
x/6i 0x1000
x/2gx 0x1018
break *0x80000000
continue
info registers pc
break *kern_entry
continue
info registers pc sp ra
```

边操作边解释：初始 PC 为 `0x1000`；六条复位指令准备启动参数并跳转；第一个断点进入 OpenSBI；第二个断点到达内核入口，此时还没有执行内核的 `la`。

### 第三段：入口栈和尾调用，约一分钟

继续在同一 GDB 会话输入：

```gdb
p/x (unsigned long)&bootstack
p/x (unsigned long)&bootstacktop
p/d (unsigned long)&bootstacktop - (unsigned long)&bootstack
disassemble /r kern_entry
si
info registers pc sp ra
si
info registers pc sp ra
si
info registers pc sp ra
```

当前构建的入口有三条机器指令。说明 `sp` 变为 `0x80203000`，栈大小为 8192，最后 PC 到 `kern_init` 而 `ra` 保持原值。

> `la` 准备 C 函数需要的栈，`tail` 跳到不返回的 C 入口。这里没有建立新的返回地址。

### 第四段：展示入口布局修正，约一分钟

打开 `entry.S` 和 `kernel.ld`，指出 `.text.kern_entry` 及第一条 `KEEP` 规则，再展示[链接顺序对照图](images/05-entry-layout.png)。

> ELF 的入口字段与入口在镜像中的位置是两件事。旧布局把 C 入口目标文件放在前面时，裸镜像从 `kern_init` 开始，跳过了栈初始化。我们把入口放进专用节并优先链接，交换顺序后仍正常启动。

最后在 GDB 中执行 `detach`、`quit`。终端 A 按 `Ctrl+A`，松开后按 `X` 退出 QEMU。

## 3. 时间充足时再展示 SBI 陷入

在 `kern_init` 停住后执行：

```gdb
disassemble /r sbi_console_putchar
```

从反汇编找到 `ecall` 地址，当前镜像为 `0x8020048a`：

```gdb
break *0x8020048a
continue
info registers pc a0 a7
p/x $mtvec
break *($mtvec & ~3)
continue
info registers pc mcause mepc mstatus
```

先展示 `a0=0x28`（字符 `(`）、`a7=1`（legacy SBI 字符输出），再展示陷入时 `mcause=9`、`mepc` 指向该 `ecall`、`MPP=1`。异常入口地址由当次 `mtvec` 读取，不需要背固件内部地址。

本机对 `ecall` 直接执行 `si` 时，GDB 会停在服务返回后的下一条内核指令。设置异常入口断点可以停在固件处理请求之前。

## 4. 源码定位表

| 被问到什么 | 打开哪里 | 解释重点 |
| --- | --- | --- |
| 第一条内核指令 | [entry.S](../code/kern/init/entry.S) | `kern_entry`、`la`、`tail` |
| 内核栈怎么来的 | [entry.S](../code/kern/init/entry.S)、[memlayout.h](../code/kern/mm/memlayout.h)、[mmu.h](../code/kern/mm/mmu.h) | `.space`、两页、栈向下增长 |
| 为何链接到这个地址 | [kernel.ld](../code/tools/kernel.ld) | `BASE_ADDRESS`、`.`、`ENTRY`、入口节顺序 |
| C 入口做什么 | [init.c](../code/kern/init/init.c) | `memset`、`cprintf`、循环、`noreturn` |
| 格式化输出怎么实现 | [stdio.c](../code/kern/libs/stdio.c)、[printfmt.c](../code/libs/printfmt.c) | 可变参数、格式解析、字符回调 |
| 怎样调用固件 | [console.c](../code/kern/driver/console.c)、[sbi.c](../code/libs/sbi.c) | 字符输出、`a7`、`a0`、`ecall` |
| 构建和调试参数 | [Makefile](../code/Makefile) | 编译、链接、`objcopy`、`-kernel`、`-s -S` |

## 5. 两道练习与常见追问

### 1）`la sp, bootstacktop` 做什么，为什么必须先做？

把静态内核栈的上界地址装入 `sp`。C 函数会使用栈保存现场和局部数据，进入 C 前要准备有效栈。我们单步后得到 `sp=0x80203000`，与 `bootstacktop` 相同。

### 2）`tail kern_init` 和普通 `call` 有什么不同？

普通 `call` 会保存新的返回地址，`tail` 跳转但不建立新的返回链。本机 `tail` 被链接器松弛为两字节跳转，执行前后 `ra` 一样。`kern_init` 声明了 `noreturn` 并最终循环，入口不需要等它返回。

### 3）`la`、`tail` 各是一条真实机器指令吗？

它们是伪指令，展开由汇编器和链接器决定。本机 `la` 对应 `auipc` 加 `addi`，后者被显示为 `mv`；`tail` 松弛成压缩跳转。可以用 `disassemble /r kern_entry` 查看实际编码。

### 4）为什么栈顶地址比栈底大？两页如何计算？

RISC-V ABI 的栈向低地址增长。初始 `sp` 是栈区上界，函数分配栈帧时减小 `sp`。`PGSIZE=4096`、`KSTACKPAGE=2`，相乘为 8192；地址相减也得到 `0x2000`。

### 5）设置 `sp` 前的 `0x80046eb0` 是什么？

这是固件移交时留下的栈指针。内核随后设置自己的静态栈。这个旧值随固件实现变化，实验重点是设置后 `sp` 与内核栈顶相等。

### 6）CPU 加电后从哪里执行，最初几条指令做什么？

本实验 QEMU `virt` 从 `0x1000` 开始，六条复位指令准备 hart ID、设备树和启动信息，取出下一跳地址，跳到 `0x80000000` 的 OpenSBI。

### 7）`0x1000` 的代码就是 OpenSBI 吗？

这里是 QEMU 提供的 MROM 复位跳转代码；OpenSBI 镜像入口是 `0x80000000`。两者分别是启动链的前两个阶段。

### 8）三个地址是 RISC-V 的统一规定吗？

本实验的复位地址由 QEMU 机器实现选择，固件和内核地址由平台布局与启动配置约定。换机器或启动配置可以不同。我们的证据是本次 PC、入口符号和固件输出。

### 9）内核由谁加载？为什么 `watch *0x80200000` 可能没停住？

这套配置由 QEMU 在虚拟 CPU 执行前预装内核。初始 PC 在 `0x1000` 时已经能读到内核指令，GDB 的写观察点设置得更晚。观察移交可在内核入口下执行断点。

### 10）为什么要先有固件，不能直接执行操作系统？

CPU 需要一个已知的起始执行位置，而复杂设备的使用又依赖初始化代码。复位代码和固件先建立这些条件，再把控制权交给内核。真实电脑常见 UEFI、引导程序和内核这样的分阶段启动。

## 6. 链接与 C 入口问答

### 11）`ENTRY(kern_entry)` 为什么没有自动把入口放在最前面？

它设置 ELF 头的入口字段。内容放在哪里由 `SECTIONS` 中的输入节规则决定。裸镜像去掉了 ELF 头，固件按约定从镜像起始地址执行，所以还要安排入口在开头。

### 12）我们修正了什么？怎么验证的？

我们为入口使用 `.text.kern_entry`，在链接脚本中先收集该节，再交换两个入口目标文件的顺序进行验证：旧布局入口移到 `0x80200032`，没有内核输出；新布局仍从 `0x80200000` 正常启动，生成镜像也与正常顺序一致。

### 13）`KEEP` 本身会把入口放在最前面吗？

最前面的位置由规则书写顺序决定。`KEEP` 负责显式保护匹配的输入节不被 `--gc-sections` 回收。当前入口也会作为节回收的根保留，专用节和优先放置是此次布局修正的直接原因。

### 14）`.text.kern_entry` 最后还是独立的一节吗？

它是输入目标文件中的节，被链接脚本合并到 ELF 的输出 `.text` 节开头。用 `readelf -SW obj/kern/init/entry.o` 和 `readelf -SW bin/kernel` 可以比较输入与输出。

### 15）`. = ALIGN(0x1000)` 是对齐到什么？

对齐到 4096 字节的整数倍。`.` 是链接脚本的位置计数器。汇编里的 `.align 12` 则按 `2^12` 对齐，两处语法的参数含义要分别理解。

### 16）ELF 和裸 bin 有什么区别？

ELF 有入口、程序头、节表、符号和调试信息；裸 bin 主要是按地址展开的可装载内容。GDB 使用 `bin/kernel` 解析符号，当前 QEMU 使用 `bin/ucore.img` 启动。裸镜像的装载和执行位置由启动配置给出。

### 17）section 和 segment 有什么区别？

section 便于编译、链接组织代码和数据；segment 供 ELF 加载器映射内存。一个可加载 segment 可以包含多个 section。本机只读执行段含 `.text/.rodata`，可读写段含 `.data/.sdata`。

### 18）`.bss` 是什么，为什么要清零？

未初始化或零初始化的静态数据通常放在 `.bss`，C 要求它们在程序开始时为零。裸内核用 `edata` 和 `end` 定位范围，调用 `memset` 初始化。本机这两个地址相同，所以这次长度为 0。

若追问“新增全局变量是否一定增加 `.bss`”：需要看变量是否被保留。本项目启用 `--gc-sections`，没有被使用的变量可能被回收。

### 19）能直接从 `kern_init` 启动吗？

启动约定要先建立内核自己的运行环境。直接从 C 入口开始会跳过设置内核栈，转而依赖固件遗留状态。链接顺序实验已显示这套镜像因此没有输出。

### 20）`noreturn` 做了什么？循环算运行失败吗？

`noreturn` 告知编译器函数不会返回，本身不会自动停止函数。实际不返回来自末尾 `while (1)`。启动字符串出现后，循环是当前最小内核的预期状态。

## 7. SBI、特权级与工具问答

### 21）为什么不能直接调用宿主机的 `printf`？

宿主程序的标准库依赖宿主操作系统，内核运行在模拟的 RISC-V 机器上。这里使用项目自己的格式化函数，通过 OpenSBI 控制台逐字符输出。`-nostdinc` 和项目的 `-I` 路径让头文件来自本项目。

### 22）输出字符串的函数链是什么？

`cprintf → vcprintf → vprintfmt → cputch → cons_putc → sbi_console_putchar → sbi_call → ecall`。前面处理格式，后面输出字符；编译器可能内联部分封装，机器反汇编里的函数边界可能较少。

### 23）`ecall` 和 `call` 差在哪里？

`call` 是函数调用伪指令；`ecall` 触发环境调用异常。本实验内核在 S 模式，固件在 M 模式，使用异常入口请求固件服务。我们在 `mtvec` 入口看到了 `mcause=9`、`mepc` 指向 `ecall`，`MPP=1`。

### 24）服务号和参数放在哪里？

这份代码用 legacy SBI 接口。控制台输出服务号 1 放入 `a7/x17`，字符放入 `a0/x10`，其余传入参数放入 `a1-a2`，返回值从 `a0` 取出。现代 SBI 的扩展调用还区分扩展号与函数号，解释本实验时要对应实际代码。

### 25）为什么异常处理后不再执行同一条 `ecall`？

环境调用的陷入地址记录在 `mepc`。处理后固件把返回位置推进到下一条指令，再通过 `mret` 返回，避免再次执行同一个请求。

### 26）M、S、U 分别对应什么？

本实验中 M 对应机器级固件，S 对应内核，U 用于以后运行的用户程序。当前内核没有用户态程序。地址改变与特权级改变是不同状态变化，OpenSBI 移交时要同时准备入口和模式。

### 27）`make debug` 的 `-s -S` 分别有什么用？

`-s` 在默认 TCP 1234 端口开放 GDB 服务，`-S` 在启动时暂停 CPU。只有 `-s` 时，程序可能在 GDB 连接前就跑过了我们想看的位置。

### 28）GDB 调的是 QEMU 自己的 C 代码吗？

`make gdb` 加载内核 ELF，并连接 QEMU 的 gdbstub，检查的是模拟 RISC-V CPU 的寄存器和客户内存。调试 QEMU 宿主实现则需要加载 QEMU 可执行文件的调试符号，并使用另一套调试连接。

### 29）`si`、`step`、`continue`、`x/i` 分别是什么？

`si` 按机器指令执行；`step` 按源码级步骤执行；`continue` 运行到下一个停止事件；`x/i` 只查看反汇编，不执行它。对 `-O2` 构建，源码行与机器指令可能并非一一对应。

### 30）为何需要交叉编译？

编译器在 x86 主机上运行，目标却是 RISC-V 机器指令。`riscv64-unknown-elf-` 工具链生成目标 ELF；QEMU 模拟目标机器运行它，GDB 用相应架构解释寄存器和指令。

### 31）为什么 `bt` 不一定显示完整启动链？

固件、内核入口和 C 函数之间存在特权级移交、栈切换及尾调用，未必形成普通的连续调用栈。启动链用 PC、断点和单步验证，`bt` 更适合已有正常调用帧的 C 函数。

### 32）本实验还没做哪些 OS 功能？

页表、物理页分配、完整中断异常处理、进程调度、用户态、同步和文件系统。当前静态栈也还不是“每个进程各有一个内核栈”的机制。

## 8. 展示异常时的排查顺序

| 现象 | 下一步检查 |
| --- | --- |
| 只有 OpenSBI 输出 | 看 `Next Address`，再用 `nm` 检查 `kern_entry` 是否为 `0x80200000`，反汇编镜像开头 |
| GDB 连接被拒绝 | 看终端 A 是否运行 `make debug`，是否先退出了上一轮 QEMU |
| 连接后 PC 已到内核循环 | 退出该轮，从带 `-S` 的新会话开始 |
| `sp` 显示 `<SBI_CONSOLE_PUTCHAR>` | 比较 `bootstacktop` 符号地址和数值，这是同址数据符号显示 |
| 固件 `ra` 或设备树地址与报告不同 | 比较启动链和内核栈结果，记录当前工具版本 |

如果现场环境无法继续运行，可以用[报告](report.md)中的结果图和 [GDB 原始记录](evidence/2026-10-09-gdb.txt)解释已取得的实验结果，并说明当前停在哪一步。

## 9. 两个人怎么练

第一轮邹瑛琦操作构建和启动链，丁子昂解释栈、链接修正与 SBI。第二轮交换：两个人都独立完成全部展示。

最后互相随机问十题，先说结论，再指出代码或现场证据。优先练习第 1、2、6、9、11、12、18、22、23、27 题。验收现场按课堂要求独立回答。

## 对应指导书

- [练习](http://oslab.mobisys.top/lab2026/_book/lab1/lab1_2_1_exercise.html)：入口操作、复位地址与启动追踪。
- [OpenSBI、bin、ELF](http://oslab.mobisys.top/lab2026/_book/lab1/lab1_3_1_layout.html)：固件、特权级、装载。
- [链接脚本](http://oslab.mobisys.top/lab2026/_book/lab1/lab1_3_2_linkerscript.html)：布局、入口、栈。
- [SBI 到 stdio](http://oslab.mobisys.top/lab2026/_book/lab1/lab1_3_3_sbi_io.html)：服务号、参数寄存器、输出封装。
- [GDB](http://oslab.mobisys.top/lab2026/_book/lab1/lab1_4_gdb.html)：连接、断点和寄存器。
- [OpenSBI 1.3 环境调用处理](https://github.com/riscv-software-src/opensbi/blob/v1.3/lib/sbi/sbi_ecall.c)：处理后推进 `mepc`。
