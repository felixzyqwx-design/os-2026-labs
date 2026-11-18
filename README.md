# Lab 4：进程管理

邹瑛琦（2412744）、丁子昂（2411130）

以2026课程官网 `lab4.zip` 中的 `lab4_new` 为骨架，完成映射维护、内核线程创建与调度。正式报告和提示词分别见 [report.md](report/report.md)、[prompt.md](report/prompt.md)。

```text
code/                 内核源码与验证入口
report/report.md      实验报告
report/prompt.md      关键实现、测试提示词提炼稿
report/images/        日志摘录排版图
report/evidence/      精简原始摘录与版本/结果记录
report/scripts/       材料检查与图片重建脚本
```

在 WSL Ubuntu 中进入 `code/`：

```sh
make
make qemu
make grade
```

本轮官方评分30/30。`make qemu` 在init输出后会到达原骨架 `do_exit` 的占位panic；本实验未实现完整退出回收。

补充验证、固定地址栈的独立变体、两终端GDB入口见 [验证说明](code/tools/tests/README.md)。测试注入临时副本，输出目录必须尚不存在。官方评分默认使用 `/tmp/lab4_grade`，运行前确认该目录未被其他任务占用。

从实验根目录检查报告链接、图片、证据与源码版本：

```sh
python3 report/scripts/verify_materials.py
```

该检查按源码散列核对测试版本。重新构建的 ELF 会包含本机编译目录，通常与历史调试文件散列不同；如需核对记录中的原始 ELF，可加 `--check-recorded-elf`。

来源：[2026指导书](http://oslab.mobisys.top/lab2026/_book/lab4/lab4.html)、[官方包](http://oslab.mobisys.top/lab2026/lab4.zip)，获取于2026-11-17。官方包SHA-256及本轮源码散列见 [results.json](report/evidence/results.json)。网页与官方压缩包不包含在实验提交目录中。
