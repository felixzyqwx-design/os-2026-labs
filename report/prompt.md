# Lab 3 关键实验提示词

以下为提炼稿，依据 2026-11-04 的实验需求分析、实际实现与验证过程整理，保留原意，不作为逐字聊天记录。P1 对应 Lab 2 必要继承；P2/P3、P4/P5 分别为两个模块的实现稿与测试稿；P6/P7 用于调试、思考和验收。具体 spec 与结果见 [实验报告](report.md)。

<a id="p1"></a>
## P1. Lab 2 必要继承

来源：当前练习的实验依赖段、已有 Lab 2 源码和本次继承范围。

```text
以当前官网下载的 Lab 3 骨架为主体，继承已经实现的 page_init 和 Best-Fit，
并保留 First-Fit 两处尾插 break 修复。根据 DTB 取得物理内存范围，按现有
映射上限裁剪；保留 OpenSBI、内核和 Page 描述符占用，只释放之后的完整页。

不要整份覆盖 Lab 3 的 pmm.c 或 memlayout.h，保留 alloc/free/nr_free 的
中断保护、Page 布局及 atomic.h 位操作，保留官方分配器检查函数。
默认 Best-Fit，支持 PMM=first_fit，并让编译参数改变时正确重建。
核对入口节、过渡映射、完整 sp 和本机 QEMU 装载方式，记录必要调整。
```

<a id="p2"></a>
## P2. 模块一实现

来源：当前“功能模块一”，以及 SAVE_ALL、trapframe 和 ABI 的实际约束。

```text
阅读 kern/trap/trapentry.S 和 trap.h，再补 RESTORE_ALL 与 __alltraps。
RV64 frame 是 36×8=288 字节；原 sp 位于槽 2，sstatus/sepc 位于槽 32/33。

RESTORE_ALL 先恢复返回 CSR 和通用寄存器，最后从槽 2 恢复原 sp，
避免提前改变 frame 基址。x0 不需恢复，scause/stval 保留为诊断信息。
__alltraps 保存后用 a0 传当前 frame 地址，按 ABI 调 trap，
返回时保留 frame，再经过 __trapret 和 sret 返回。

不得修改 SAVE_ALL、struct trapframe 或 trap 的签名；按保存的状态恢复，
不要强制改变来源特权级。保留 lab3 注释并填写两位组员学号。
```

<a id="p3"></a>
## P3. 模块一测试

来源：模块一接口约束和本次独立验证设计。

```text
为模块一设计独立测试，在临时副本注入，保持正常启动代码不变。
汇编探针要遵守 ABI，设置寄存器哨兵，验证 Trap 后寄存器、原 sp、ra 和
续执行位置。覆盖 16/32 位断点及非法编码，保留 gp/tp 的调用环境。

先用测试专用处理函数隔离汇编入口和恢复，再接入真实处理函数。
GDB 在 __alltraps、trap、__trapret 和 sret 前后观察，核对 a0、
frame 288 字节和 16 字节对齐、32 个 GPR 槽、CSR 及返回权限。
检查日志、超时、断言和退出状态；不能只根据打印的 PASS 判定通过。
```

<a id="p4"></a>
## P4. 模块二实现

来源：当前“功能模块二”以及 clock.h、riscv.h、sbi.h 的接口。

```text
在 trap.c 指定区域补 interrupt_handler 和 exception_handler，
保持签名、既有 trap/dispatch/print/idt 函数不变。

中断按 scause 去掉最高标志位后分类。S 态时钟每次重新预约下一次事件，
ticks 仅加一，每 100 次输出一次。累计输出达到 SHUTDOWN_AFTER 后通过
SBI 关机。课程未给具体数值，使用可覆盖默认值 10，并拒绝非正值。
已知其他中断输出对应类型，未知原因输出原因码和完整 frame。

断点和非法指令分别输出 Breakpoint at、Illegal instruction at 及
RV64 地址。读取首半字，在本实验的 16/32 位编码范围内判断长度，
epc 分别加 2 或 4，返回后继续执行。其他异常输出 frame，保持 epc。
```

<a id="p5"></a>
## P5. 模块二测试

来源：模块二行为边界、原评分脚本及其未覆盖的要求。

```text
保持官方评分断言、分值和匹配条件，额外验证以下内容：
1. 真实执行 c.ebreak、32 位 ebreak、16 位与 32 位非法编码，
   检查输出、epc 增量和后续执行，不重复触发。
2. 合成 frame 检查 99/100/101/199/200 计数边界、其他已知中断、
   未知原因和其他异常；中断及兜底不能错误移动 epc。
3. 正常启动持续收时钟，恰好输出十行 100 ticks 后正常关机；
   调整阈值后也检查输出次数和退出状态。
4. 记录真实客体 Trap 与合成 frame 检查各自证明的内容。
若官方脚本不能启动，先定位客体是否进入内核；只作有证据支持的启动调整。
```

<a id="p6"></a>
## P6. 源码调试、同步与思考

来源：中断入口、中断开关正文及本次调试需求。

```text
沿用已有 QEMU/GDB，观察 __alltraps→trap→__trapret→sret。
记录 frame、a0、sp、sepc/scause/sstatus；比较恢复前后 GPR、返回 PC、
SIE/SPIE/SPP 和实际特权级。跨 sret 时在预期返回 PC 设临时断点。

在内核中验证原 SIE 开/关、嵌套保存恢复及内存分配回收守恒；
分别运行 Best-Fit 和 First-Fit。用主机回归检查 First-Fit 尾插链表，
明确主机测试替身不能代替 RV64 原子操作验证。

结合当前正文回答：stvec 低两位编码模式如何保持旧合法地址的含义；
do-while(0) 怎样把宏包装成单语句。解释宏结构、屏蔽本 hart 中断与
AMO 原子修改分别负责什么。
```

<a id="p7"></a>
## P7. 最终逐项验收

来源：当前指导书全章、报告要求和逐题覆盖约定。

```text
重新核对当前指导书的全部模块、正文思考、Challenge 与报告要求。
把每一项对应到代码或回答、测试判据、实际证据和报告位置。
课程取消的旧题保留范围记录；不能用官方评分满分代替未评分内容验收。

检查原始日志中的失败、定位、修正和复测，再核对图片与证据来源。
报告分别说明整体逻辑、核心模块、spec/prompt、实际问题、OS 原理联系
及尚未实现的原理内容。区分静态检查、主机模型、QEMU 内核运行与 GDB。
```
