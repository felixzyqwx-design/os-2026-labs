# Lab 1 AI 协作过程

本文件按阶段整理提问、AI 回答、操作、测试及修正。关键提示词的结构化版本见 [prompt.md](prompt.md)，技术结果见 [report.md](report.md)。

## 1. 明确实验任务

学生最初说明自己不了解课程实验，要求先弄清 Lab 1 到底做什么，再给出方案，确认后才能执行。AI 阅读课程网页、环境文档和本地 `lab1` 源码后，将任务整理为：搭建 RISC-V 工具环境，编译运行最小内核，用 GDB 回答两道练习，最后根据实际证据写报告。

源码搜索没有发现 Lab 1 的 `TODO`、`YOUR CODE` 或待补全练习。随后补充的课堂记录确认本实验的重点是启动调试与理解。

## 2. 评估环境配置的影响

学生询问配置环境是否会影响正在运行的代码。AI 说明工具链和 QEMU 主要安装在 WSL 中，分析了启用虚拟化、重启和资源占用的影响。学生回复“可以开始配置”后继续。

WSL2 起初无法正常启动。检查后将 Windows 启动项 `hypervisorlaunchtype` 设为 `Auto`，重启后 Ubuntu 24.04.1 LTS 恢复正常。随后验证 Make、RISC-V GCC/binutils、GDB Multiarch 和 QEMU，并建立兼容链接：

```text
/usr/local/bin/riscv64-unknown-elf-gdb -> /usr/bin/gdb-multiarch
```

## 3. 方案审查与阶段停止点

学生要求“先把完成 Lab1 的方案给我看看”。AI 将实验拆为环境基线、干净构建、练习 1、练习 2、模块理解、报告和最终验证。学生提供两位组员的信息，要求建立仓库，并规定执行到写报告前停止。

原执行方案记录在本地 `.codex/plans/2026-09-23-lab1-completion.md`。方案用源码、符号地址和寄存器变化作为检查点。

## 4. 建立仓库

AI 使用已经登录的 GitHub CLI 创建 `felixzyqwx-design/os-2026-labs`，以 `实验课` 为本地仓库根目录，使用 `lab1` 分支，配置作者为邹瑛琦。

```text
38285b1 chore: initialize OS lab repository
```

添加 `.gitignore`，排除 `bin/`、`obj/` 等构建产物。学生后来授权将仓库改为公开。

## 5. QEMU 参数兼容问题

第一次使用指导书旧式参数时，QEMU 8.2.2 能启动 OpenSBI，但显示：

```text
Domain0 Next Address : 0x0000000000000000
```

AI 检查 Makefile，将 `qemu` 和 `debug` 目标从 `-device loader,file=...,addr=0x80200000` 改为 `-kernel $(UCOREIMG)`。重跑后下一跳地址变为 `0x80200000`，启动字符串出现。

这次检查区分了镜像是否预装到内存，以及固件是否获得正确下一阶段入口。

## 6. 构建与练习 1

执行 `make clean && make` 后，编译、链接和 `objcopy` 成功。`readelf` 和 `nm` 给出了 ELF64、RISC-V 架构、入口及关键符号。随后限时运行 QEMU，观察到 OpenSBI 1.3、S 模式下一跳入口和内核输出。

AI 从 `mmu.h`、`memlayout.h` 和 `entry.S` 算出栈大小为 8192 字节，再用 GDB 在 `kern_entry` 断下。`bootstack` 与 `bootstacktop` 地址差为 8192，单步后 `sp` 变为 `0x80203000`；到达 `kern_init` 时，`ra` 保持 `0x8000ae9a`。

GDB 把栈顶地址同时显示为数据符号 `SBI_CONSOLE_PUTCHAR`。对照链接符号后，AI 确认这是同址符号显示，栈和该数据分居边界两侧。

## 7. 练习 2 与命令转义错误

新调试会话从 `0x1000` 开始，随后命中 `0x80000000` 和 `0x80200000`。第一次批处理中的 `$pc` 被外层 shell 提前展开，导致两段 `x/i $pc` 显示错误地址。

AI 退出该会话，从复位状态重新运行，改用 `x/8i 0x80000000` 和 `x/4i 0x80200000`。第二次输出正确显示三个启动阶段。退出后检查了 QEMU 进程。

## 8. 报告前停止与课程要求复核

构建、两道练习和源码分析完成后，AI 检查 `lab1_report.md` 尚未创建，向学生汇报证据，按约定停止。

学生补充课堂会议纪要和文字记录，说明老师要求提交 AI 交互过程，包括提问、回答、测试和修正。AI 对照网页报告要求，确定正文应覆盖整体逻辑线、核心模块、全部练习、知识点与 OS 原理的关系及未覆盖内容，并附协作记录。

复核中澄清了 QEMU 预装镜像和 OpenSBI 移交控制权的关系，也区分了 MROM 指令与被强制反汇编的入口地址数据。学生授权开始写报告后完成首版。

```text
4ca1406 docs(lab1): add verified experiment report
```

## 9. 交付目录整改与提示词整理

老师要求分支使用 `labx`，根目录含 `code/` 与 `report/`，后者含 `report.md`、`prompt.md` 和 `images/`。学生要求提示词文件筛选关键内容，允许忠于原意地整理口语表达。

AI 通过 Git 重命名整理目录，将报告改为 `report/report.md`，汇总 8 条关键提示词。2026 年 9 月 30 日重新运行构建、QEMU 和 GDB，再将输出排版为四张图片。

首次图中 GDB 制表符显示异常，清理显示控制字符后重新渲染。最终 QEMU 校验中的第一条包装命令又被 PowerShell 提前解释了 Bash 的 `$()`，没有启动 QEMU；去掉命令替换后从干净构建重新运行，得到正确的下一跳地址、模式和内核输出。

检查目录、图片链接、构建及后台进程后提交并推送：

```text
89b10a3 docs(lab1): align deliverables with submission format
```

## 10. 协作复测与入口布局修正

小组协作中的兼容性检查包含 2026 年 10 月 7 日 Windows 复测，使用 SiFive GCC 10.2.0、GDB 10.1、QEMU 5.1.0。原代码的 `kern_init` 在 `0x80200000`，入口 `kern_entry` 在 `0x80200032`，只有 OpenSBI 输出。

入口改用 `.text.kern_entry`，链接脚本优先放置并保留该节，复测后入口和启动结果正确。修改于 10 月 9 日提交并合并：

```text
bf74a00 fix(lab1): place kernel entry at image start
462722f Merge pull request #1 from felixzyqwx-design/fix/lab1-entry-layout
```

## 11. 本轮审查与指导书迁移

学生要求客观审查代码改动，吸收有价值的部分，优化报告，删除只为防止质疑而存在的句子。

AI 获取远端分支后发现 PR 已合并，以快进方式同步本地 `lab1`。新指导书位于 `http://oslab.mobisys.top/lab2026/_book/`；网页工具连接失败，本机通过 `curl --noproxy '*'` 直连取得练习、链接脚本、SBI、构建、GDB 和报告要求页面。

AI 用 humanizer-zh 调整正文表达，将协作记录迁至本文件，减少技术正文中的重复声明。

## 12. 链接顺序对照实验

AI 在同一套编译器和库目标文件下，交换 `entry.o` 与 `init.o` 顺序。旧布局在 C 入口目标文件在前时复现了 `kern_entry=0x80200032`，且没有内核输出；当前布局仍从 `0x80200000` 启动，镜像与正常顺序逐字节相同。

详细命令和结果保存在 [链接实验记录](evidence/2026-10-09-entry-layout.txt)。这项实验验证了入口布局修正。

## 13. SBI 取证失败与修正

AI 增加了 SBI 输出检查。第一轮在 `ecall` 前断下，执行 `si` 后停在 `0x8020048e`，已经越过固件服务并返回，`mepc` 也被推进到了下一条指令。预期检查异常入口的两个断言失败。

这轮同时暴露了脚本问题：GDB 的多条 `-ex` 命令在 Python 断言报错后仍继续执行，进程返回码为 0，随后还打印了预设的 PASS 行。AI 读取完整输出发现错误，保留了 [第一次原始记录](evidence/2026-10-09-gdb-attempt-1.txt)，其中该 PASS 行对应的检查并未通过。

随后从全新会话重跑：在输出 `ecall` 处读取 `mtvec`，改在异常入口设断点并继续执行。得到 `pc=0x80000428`、`mcause=9`、`mepc=0x8020048a`、`MPP=1`。脚本也改为检查 GDB 输出中的断言异常以及完成标记。

第二轮的构建、QEMU、链接顺序和 GDB 检查通过。将终端 NUL 字节改为可见的 `\x00` 记录后，完整复测再次通过；结束后脚本关闭了自己启动的全部 QEMU 进程。验证脚本保存在 [scripts/verify_lab1.py](scripts/verify_lab1.py)，成功取证见 [GDB 记录](evidence/2026-10-09-gdb.txt)。

## 14. 最终验证

使用 Makefile 的实际 `make debug` 与 `make gdb` 目标验证调试流程。复位 PC、OpenSBI 断点、内核入口及三次单步后的栈顶检查通过，`detach` 后内核打印了启动字符串，随后退出 QEMU。

六张结果图从最终日志生成并逐张检查。文档的本地链接、代码块和提示词数量检查完成，关键提示词共 8 条。
