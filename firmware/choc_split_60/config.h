/* Copyright 2026 choc-split-60 contributors
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 2 of the License, or
 * (at your option) any later version.
 */
#pragma once

/* ---- split matrix ------------------------------------------------------- */
#define MATRIX_ROWS 10          /* 5 rows per half */
#define MATRIX_COLS 8           /* 8 columns per half */
#define MATRIX_ROW_PINS { GP2, GP3, GP4, GP5, GP6 }
#define MATRIX_COL_PINS { GP7, GP8, GP9, GP20, GP21, GP22, GP23, GP26 }
#define DIODE_DIRECTION COL2ROW

/* ---- rotary encoder (left half only) ------------------------------------ */
/* RE1 sits in the left macro column: A/B on GP28/GP29, its push switch is the
 * ordinary matrix key L07 (COL7 / ROW0).  Both halves run the encoder driver;
 * the right half has nothing on those pins (they stay pulled up). */
#define ENCODERS_PAD_A { GP28 }
#define ENCODERS_PAD_B { GP29 }
#define ENCODER_RESOLUTION 4

/* ---- split transport ---------------------------------------------------- */
/* The left half is always the master; plug the USB cable into it. */
#define MASTER_LEFT
#define SERIAL_USART_FULL_DUPLEX
#define SERIAL_USART_TX_PIN GP0
#define SERIAL_USART_RX_PIN GP1

/* ---- housekeeping ------------------------------------------------------- */
#define DEBOUNCE 5
#define LOCKING_RESYNC_ENABLE
#define TAPPING_TERM 180
#define PERMISSIVE_HOLD
