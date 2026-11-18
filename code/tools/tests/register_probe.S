.text
.globl lab4_probe_regs
.type lab4_probe_regs, @function
lab4_probe_regs:
    addi sp, sp, -112
    sd ra, 0(sp)
    sd s0, 8(sp)
    sd s1, 16(sp)
    sd s2, 24(sp)
    sd s3, 32(sp)
    sd s4, 40(sp)
    sd s5, 48(sp)
    sd s6, 56(sp)
    sd s7, 64(sp)
    sd s8, 72(sp)
    sd s9, 80(sp)
    sd s10, 88(sp)
    sd s11, 96(sp)
    sd sp, 104(sp)
    li s0, 1000
    li s1, 1001
    li s2, 1002
    li s3, 1003
    li s4, 1004
    li s5, 1005
    li s6, 1006
    li s7, 1007
    li s8, 1008
    li s9, 1009
    li s10, 1010
    li s11, 1011
    call schedule
    li a0, 1
    ld t0, 104(sp)
    bne sp, t0, 1f
    li t0, 1000
    bne s0, t0, 1f
    li t0, 1001
    bne s1, t0, 1f
    li t0, 1002
    bne s2, t0, 1f
    li t0, 1003
    bne s3, t0, 1f
    li t0, 1004
    bne s4, t0, 1f
    li t0, 1005
    bne s5, t0, 1f
    li t0, 1006
    bne s6, t0, 1f
    li t0, 1007
    bne s7, t0, 1f
    li t0, 1008
    bne s8, t0, 1f
    li t0, 1009
    bne s9, t0, 1f
    li t0, 1010
    bne s10, t0, 1f
    li t0, 1011
    bne s11, t0, 1f
    li a0, 0
1:  ld ra, 0(sp)
    ld s0, 8(sp)
    ld s1, 16(sp)
    ld s2, 24(sp)
    ld s3, 32(sp)
    ld s4, 40(sp)
    ld s5, 48(sp)
    ld s6, 56(sp)
    ld s7, 64(sp)
    ld s8, 72(sp)
    ld s9, 80(sp)
    ld s10, 88(sp)
    ld s11, 96(sp)
    addi sp, sp, 112
    ret
.size lab4_probe_regs, .-lab4_probe_regs
.globl lab4_probe_exceptions
.type lab4_probe_exceptions, @function
lab4_probe_exceptions:
    li a0, 0
    c.ebreak
    addi a0, a0, 1
    .4byte 0x00100073
    addi a0, a0, 1
    .2byte 0x0000
    addi a0, a0, 1
    .4byte 0x0000007b
    addi a0, a0, 1
    ret
.size lab4_probe_exceptions, .-lab4_probe_exceptions
.globl lab4_fault_store, lab4_store_resume
lab4_fault_store:
    sd zero, 0(a0)
lab4_store_resume:
    ret
.globl lab4_fault_load, lab4_load_resume
lab4_fault_load:
    ld a0, 0(a0)
lab4_load_resume:
    ret
.globl lab4_fault_exec, lab4_exec_resume
lab4_fault_exec:
    addi sp, sp, -16
    sd ra, 0(sp)
    jalr a0
lab4_exec_resume:
    ld ra, 0(sp)
    addi sp, sp, 16
    ret
