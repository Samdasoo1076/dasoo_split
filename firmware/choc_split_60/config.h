/* Copyright 2026 choc-split-60 contributors
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 2 of the License, or
 * (at your option) any later version.
 */
#pragma once

/* ---- split matrix ------------------------------------------------------- */
#define MATRIX_ROWS 12          /* 6 rows per half */
#define MATRIX_COLS 8           /* 8 columns per half */
#define MATRIX_ROW_PINS { GP2, GP3, GP4, GP5, GP6, GP7 }
#define MATRIX_COL_PINS { GP8, GP9, GP20, GP21, GP22, GP23, GP26, GP27 }
#define DIODE_DIRECTION COL2ROW

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
