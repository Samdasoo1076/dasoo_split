/* Copyright 2026 choc-split-60 contributors
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 2 of the License, or
 * (at your option) any later version.
 */
#pragma once

#include "quantum.h"

/* Layout of the two halves.  Each argument is <hand><matrix row><matrix col>.
 *
 * The 65 keys are listed row by row, left half first:
 *
 *   row 0 : ` 1 2 3 4 5 6         | 7 8 9 0 - = BSpc
 *   row 1 : Tab Q W E R T         | Y U I O P [ ] backslash
 *   row 2 : Caps A S D F G        | H J K L ; ' Enter
 *   row 3 : LShift Z X C V B      | N M , . / RShift
 *   row 4 : LCtrl LWin LAlt Space | Space RAlt RFn RCtrl
 *   row 5 : Thumb1 Thumb2         | Thumb1 Thumb2
 */
#define LAYOUT(                                                        \
    L00, L01, L02, L03, L04, L05, L06,                                 \
    L10, L11, L12, L13, L14, L15,                                      \
    L20, L21, L22, L23, L24, L25,                                      \
    L30, L31, L32, L33, L34, L35,                                      \
    L40, L41, L42, L43,                                                \
    L54, L55,                                                          \
    R00, R01, R02, R03, R04, R05, R06,                                 \
    R10, R11, R12, R13, R14, R15, R16, R17,                            \
    R20, R21, R22, R23, R24, R25, R26,                                 \
    R30, R31, R32, R33, R34, R35,                                      \
    R40, R41, R42, R43,                                                \
    R51, R52                                                           \
) {                                                                    \
    { L00, L01, L02, L03, L04, L05, L06, KC_NO },                      \
    { L10, L11, L12, L13, L14, L15, KC_NO, KC_NO },                    \
    { L20, L21, L22, L23, L24, L25, KC_NO, KC_NO },                    \
    { L30, L31, L32, L33, L34, L35, KC_NO, KC_NO },                    \
    { L40, L41, L42, L43, KC_NO, KC_NO, KC_NO, KC_NO },                \
    { KC_NO, KC_NO, KC_NO, KC_NO, L54, L55, KC_NO, KC_NO },            \
    { R00, R01, R02, R03, R04, R05, R06, KC_NO },                      \
    { R10, R11, R12, R13, R14, R15, R16, R17 },                        \
    { R20, R21, R22, R23, R24, R25, R26, KC_NO },                      \
    { R30, R31, R32, R33, R34, R35, KC_NO, KC_NO },                    \
    { R40, R41, R42, R43, KC_NO, KC_NO, KC_NO, KC_NO },                \
    { KC_NO, R51, R52, KC_NO, KC_NO, KC_NO, KC_NO, KC_NO }             \
}
