    .text
    .align 2
    .global probe_registers
probe_registers:
    addi sp, sp, -640
    sd x1, 0(sp)
    sd x3, 8(sp)
    sd x4, 16(sp)
    sd x8, 24(sp)
    sd x9, 32(sp)
    sd x18, 40(sp)
    sd x19, 48(sp)
    sd x20, 56(sp)
    sd x21, 64(sp)
    sd x22, 72(sp)
    sd x23, 80(sp)
    sd x24, 88(sp)
    sd x25, 96(sp)
    sd x26, 104(sp)
    sd x27, 112(sp)
    li x1, 257
    li x5, 261
    li x6, 262
    li x7, 263
    li x8, 264
    li x9, 265
    li x10, 266
    li x11, 267
    li x12, 268
    li x13, 269
    li x14, 270
    li x15, 271
    li x16, 272
    li x17, 273
    li x18, 274
    li x19, 275
    li x20, 276
    li x21, 277
    li x22, 278
    li x23, 279
    li x24, 280
    li x25, 281
    li x26, 282
    li x27, 283
    li x28, 284
    li x29, 285
    li x30, 286
    li x31, 287
    .2byte 0x9002
    sd x1, 264(sp)
    sd x2, 272(sp)
    sd x3, 280(sp)
    sd x4, 288(sp)
    sd x5, 296(sp)
    sd x6, 304(sp)
    sd x7, 312(sp)
    sd x8, 320(sp)
    sd x9, 328(sp)
    sd x10, 336(sp)
    sd x11, 344(sp)
    sd x12, 352(sp)
    sd x13, 360(sp)
    sd x14, 368(sp)
    sd x15, 376(sp)
    sd x16, 384(sp)
    sd x17, 392(sp)
    sd x18, 400(sp)
    sd x19, 408(sp)
    sd x20, 416(sp)
    sd x21, 424(sp)
    sd x22, 432(sp)
    sd x23, 440(sp)
    sd x24, 448(sp)
    sd x25, 456(sp)
    sd x26, 464(sp)
    sd x27, 472(sp)
    sd x28, 480(sp)
    sd x29, 488(sp)
    sd x30, 496(sp)
    sd x31, 504(sp)
    li t0, 257
    ld t1, 264(sp)
    bne t0, t1, .Lprobe_fail
    mv t0, sp
    ld t1, 272(sp)
    bne t0, t1, .Lprobe_fail
    ld t0, 8(sp)
    ld t1, 280(sp)
    bne t0, t1, .Lprobe_fail
    ld t0, 16(sp)
    ld t1, 288(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 261
    ld t1, 296(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 262
    ld t1, 304(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 263
    ld t1, 312(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 264
    ld t1, 320(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 265
    ld t1, 328(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 266
    ld t1, 336(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 267
    ld t1, 344(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 268
    ld t1, 352(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 269
    ld t1, 360(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 270
    ld t1, 368(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 271
    ld t1, 376(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 272
    ld t1, 384(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 273
    ld t1, 392(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 274
    ld t1, 400(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 275
    ld t1, 408(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 276
    ld t1, 416(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 277
    ld t1, 424(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 278
    ld t1, 432(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 279
    ld t1, 440(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 280
    ld t1, 448(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 281
    ld t1, 456(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 282
    ld t1, 464(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 283
    ld t1, 472(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 284
    ld t1, 480(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 285
    ld t1, 488(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 286
    ld t1, 496(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 287
    ld t1, 504(sp)
    bne t0, t1, .Lprobe_fail
    li x1, 257
    li x5, 261
    li x6, 262
    li x7, 263
    li x8, 264
    li x9, 265
    li x10, 266
    li x11, 267
    li x12, 268
    li x13, 269
    li x14, 270
    li x15, 271
    li x16, 272
    li x17, 273
    li x18, 274
    li x19, 275
    li x20, 276
    li x21, 277
    li x22, 278
    li x23, 279
    li x24, 280
    li x25, 281
    li x26, 282
    li x27, 283
    li x28, 284
    li x29, 285
    li x30, 286
    li x31, 287
    .word 0x00100073
    sd x1, 264(sp)
    sd x2, 272(sp)
    sd x3, 280(sp)
    sd x4, 288(sp)
    sd x5, 296(sp)
    sd x6, 304(sp)
    sd x7, 312(sp)
    sd x8, 320(sp)
    sd x9, 328(sp)
    sd x10, 336(sp)
    sd x11, 344(sp)
    sd x12, 352(sp)
    sd x13, 360(sp)
    sd x14, 368(sp)
    sd x15, 376(sp)
    sd x16, 384(sp)
    sd x17, 392(sp)
    sd x18, 400(sp)
    sd x19, 408(sp)
    sd x20, 416(sp)
    sd x21, 424(sp)
    sd x22, 432(sp)
    sd x23, 440(sp)
    sd x24, 448(sp)
    sd x25, 456(sp)
    sd x26, 464(sp)
    sd x27, 472(sp)
    sd x28, 480(sp)
    sd x29, 488(sp)
    sd x30, 496(sp)
    sd x31, 504(sp)
    li t0, 257
    ld t1, 264(sp)
    bne t0, t1, .Lprobe_fail
    mv t0, sp
    ld t1, 272(sp)
    bne t0, t1, .Lprobe_fail
    ld t0, 8(sp)
    ld t1, 280(sp)
    bne t0, t1, .Lprobe_fail
    ld t0, 16(sp)
    ld t1, 288(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 261
    ld t1, 296(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 262
    ld t1, 304(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 263
    ld t1, 312(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 264
    ld t1, 320(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 265
    ld t1, 328(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 266
    ld t1, 336(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 267
    ld t1, 344(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 268
    ld t1, 352(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 269
    ld t1, 360(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 270
    ld t1, 368(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 271
    ld t1, 376(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 272
    ld t1, 384(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 273
    ld t1, 392(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 274
    ld t1, 400(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 275
    ld t1, 408(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 276
    ld t1, 416(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 277
    ld t1, 424(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 278
    ld t1, 432(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 279
    ld t1, 440(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 280
    ld t1, 448(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 281
    ld t1, 456(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 282
    ld t1, 464(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 283
    ld t1, 472(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 284
    ld t1, 480(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 285
    ld t1, 488(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 286
    ld t1, 496(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 287
    ld t1, 504(sp)
    bne t0, t1, .Lprobe_fail
    li x1, 257
    li x5, 261
    li x6, 262
    li x7, 263
    li x8, 264
    li x9, 265
    li x10, 266
    li x11, 267
    li x12, 268
    li x13, 269
    li x14, 270
    li x15, 271
    li x16, 272
    li x17, 273
    li x18, 274
    li x19, 275
    li x20, 276
    li x21, 277
    li x22, 278
    li x23, 279
    li x24, 280
    li x25, 281
    li x26, 282
    li x27, 283
    li x28, 284
    li x29, 285
    li x30, 286
    li x31, 287
    .2byte 0x0000
    sd x1, 264(sp)
    sd x2, 272(sp)
    sd x3, 280(sp)
    sd x4, 288(sp)
    sd x5, 296(sp)
    sd x6, 304(sp)
    sd x7, 312(sp)
    sd x8, 320(sp)
    sd x9, 328(sp)
    sd x10, 336(sp)
    sd x11, 344(sp)
    sd x12, 352(sp)
    sd x13, 360(sp)
    sd x14, 368(sp)
    sd x15, 376(sp)
    sd x16, 384(sp)
    sd x17, 392(sp)
    sd x18, 400(sp)
    sd x19, 408(sp)
    sd x20, 416(sp)
    sd x21, 424(sp)
    sd x22, 432(sp)
    sd x23, 440(sp)
    sd x24, 448(sp)
    sd x25, 456(sp)
    sd x26, 464(sp)
    sd x27, 472(sp)
    sd x28, 480(sp)
    sd x29, 488(sp)
    sd x30, 496(sp)
    sd x31, 504(sp)
    li t0, 257
    ld t1, 264(sp)
    bne t0, t1, .Lprobe_fail
    mv t0, sp
    ld t1, 272(sp)
    bne t0, t1, .Lprobe_fail
    ld t0, 8(sp)
    ld t1, 280(sp)
    bne t0, t1, .Lprobe_fail
    ld t0, 16(sp)
    ld t1, 288(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 261
    ld t1, 296(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 262
    ld t1, 304(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 263
    ld t1, 312(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 264
    ld t1, 320(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 265
    ld t1, 328(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 266
    ld t1, 336(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 267
    ld t1, 344(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 268
    ld t1, 352(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 269
    ld t1, 360(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 270
    ld t1, 368(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 271
    ld t1, 376(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 272
    ld t1, 384(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 273
    ld t1, 392(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 274
    ld t1, 400(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 275
    ld t1, 408(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 276
    ld t1, 416(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 277
    ld t1, 424(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 278
    ld t1, 432(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 279
    ld t1, 440(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 280
    ld t1, 448(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 281
    ld t1, 456(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 282
    ld t1, 464(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 283
    ld t1, 472(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 284
    ld t1, 480(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 285
    ld t1, 488(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 286
    ld t1, 496(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 287
    ld t1, 504(sp)
    bne t0, t1, .Lprobe_fail
    li x1, 257
    li x5, 261
    li x6, 262
    li x7, 263
    li x8, 264
    li x9, 265
    li x10, 266
    li x11, 267
    li x12, 268
    li x13, 269
    li x14, 270
    li x15, 271
    li x16, 272
    li x17, 273
    li x18, 274
    li x19, 275
    li x20, 276
    li x21, 277
    li x22, 278
    li x23, 279
    li x24, 280
    li x25, 281
    li x26, 282
    li x27, 283
    li x28, 284
    li x29, 285
    li x30, 286
    li x31, 287
    .word 0x0000007b
    sd x1, 264(sp)
    sd x2, 272(sp)
    sd x3, 280(sp)
    sd x4, 288(sp)
    sd x5, 296(sp)
    sd x6, 304(sp)
    sd x7, 312(sp)
    sd x8, 320(sp)
    sd x9, 328(sp)
    sd x10, 336(sp)
    sd x11, 344(sp)
    sd x12, 352(sp)
    sd x13, 360(sp)
    sd x14, 368(sp)
    sd x15, 376(sp)
    sd x16, 384(sp)
    sd x17, 392(sp)
    sd x18, 400(sp)
    sd x19, 408(sp)
    sd x20, 416(sp)
    sd x21, 424(sp)
    sd x22, 432(sp)
    sd x23, 440(sp)
    sd x24, 448(sp)
    sd x25, 456(sp)
    sd x26, 464(sp)
    sd x27, 472(sp)
    sd x28, 480(sp)
    sd x29, 488(sp)
    sd x30, 496(sp)
    sd x31, 504(sp)
    li t0, 257
    ld t1, 264(sp)
    bne t0, t1, .Lprobe_fail
    mv t0, sp
    ld t1, 272(sp)
    bne t0, t1, .Lprobe_fail
    ld t0, 8(sp)
    ld t1, 280(sp)
    bne t0, t1, .Lprobe_fail
    ld t0, 16(sp)
    ld t1, 288(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 261
    ld t1, 296(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 262
    ld t1, 304(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 263
    ld t1, 312(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 264
    ld t1, 320(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 265
    ld t1, 328(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 266
    ld t1, 336(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 267
    ld t1, 344(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 268
    ld t1, 352(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 269
    ld t1, 360(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 270
    ld t1, 368(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 271
    ld t1, 376(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 272
    ld t1, 384(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 273
    ld t1, 392(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 274
    ld t1, 400(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 275
    ld t1, 408(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 276
    ld t1, 416(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 277
    ld t1, 424(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 278
    ld t1, 432(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 279
    ld t1, 440(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 280
    ld t1, 448(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 281
    ld t1, 456(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 282
    ld t1, 464(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 283
    ld t1, 472(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 284
    ld t1, 480(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 285
    ld t1, 488(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 286
    ld t1, 496(sp)
    bne t0, t1, .Lprobe_fail
    li t0, 287
    ld t1, 504(sp)
    bne t0, t1, .Lprobe_fail
    li a0, 0
    j .Lprobe_restore
.Lprobe_fail:
    li a0, 1
.Lprobe_restore:
    ld x1, 0(sp)
    ld x3, 8(sp)
    ld x4, 16(sp)
    ld x8, 24(sp)
    ld x9, 32(sp)
    ld x18, 40(sp)
    ld x19, 48(sp)
    ld x20, 56(sp)
    ld x21, 64(sp)
    ld x22, 72(sp)
    ld x23, 80(sp)
    ld x24, 88(sp)
    ld x25, 96(sp)
    ld x26, 104(sp)
    ld x27, 112(sp)
    addi sp, sp, 640
    ret
