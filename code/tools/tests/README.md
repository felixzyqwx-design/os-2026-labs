# Lab4 补充验证入口

在 WSL Ubuntu 中进入本实验 `code/` 目录。运行器会复制源码到指定的新目录；探针、故障注入和固定栈变体只写入副本。

```sh
python3 tools/tests/run_lab4.py --segments --output /tmp/lab4-extra-run1
python3 tools/tests/run_lab4.py --segments --memory 64M --output /tmp/lab4-extra-64m-run1
python3 tools/tests/run_lab4.py --segments --fixed-stack --output /tmp/lab4-fixed-run1
python3 tools/tests/debug_lab4.py --output /tmp/lab4-debug-run1
```

输出目录必须尚不存在；需要重跑时换一个目录名。`summary.json` 记录实际结果与源散列，不能把单独一条 PASS 或进程退出0当整体通过。

官方评分：`make grade`，预期30/30。其默认临时目录为 `/tmp/lab4_grade`；开始前确认目录未被他人占用。评分包含原骨架的三个分项，未覆盖本目录的全部补充行为。

两终端调试（本轮已实际演练对应入口）：

1. 终端一在 code 下执行 `make debug`。
2. 终端二在同一 code 下执行 `make gdb`；连接的是本次 `bin/kernel` 和端口1234。先确认没有其他调试器占用端口。
3. `hbreak kern_init`、`continue`；之后依次在 proc_init、schedule、proc_run、switch_to、forkret、forkrets、__trapret、kernel_thread_entry、init_main 设断点观察。
4. 在 sret 前，在目标入口设断点后 continue；不通过手改寄存器替代实际运行。

自动GDB运行器执行同样的Makefile调试入口，保存命令文件与完整输出。结束时只处理它自己启动的进程组；手工演练在终端一使用 QEMU 的 Ctrl-a x 退出。

默认 `make qemu` 会输出init内容，然后进入骨架 `do_exit` 占位 panic；本实验未实现完整退出回收。补充探针以明确成功标记后SBI关机结束。
