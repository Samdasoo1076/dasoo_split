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
 * 70 key positions are listed row by row, left half first.  The left half has
 * a 5 key macro column on its far left (rotary encoder + Home/End/PgUp/PgDn),
 * the right half has a four key arrow cluster in its bottom right corner.
 *
 *   row 0 : ENC Home->` 1 2 3 4 5 6        | 7 8 9 0 - = BSpc
 *   row 1 : Home Tab Q W E R T            | Y U I O P [ ] backslash
 *   row 2 : End  Caps A S D F G           | H J K L ; ' Enter
 *   row 3 : PgUp LShift Z X C V B         | N M , . / RShift Up
 *   row 4 : PgDn LCtrl LWin LAlt Space    | Space RAlt RFn RCtrl Left Down Right
 */
#define LAYOUT(                                                        \
    L07, L00, L01, L02, L03, L04, L05, L06,                            \
    L17, L10, L11, L12, L13, L14, L15,                                 \
    L27, L20, L21, L22, L23, L24, L25,                                 \
    L37, L30, L31, L32, L33, L34, L35,                                 \
    L47, L40, L41, L42, L43,                                           \
    R50, R51, R52, R53, R54, R55, R56,                                 \
    R60, R61, R62, R63, R64, R65, R66, R67,                            \
    R70, R71, R72, R73, R74, R75, R76,                                 \
    R80, R81, R82, R83, R84, R85, R86,                                 \
    R90, R91, R92, R93, R94, R95, R96                                  \
) {                                                                    \
    { L07, L00, L01, L02, L03, L04, L05, L06 },                        \
    { L17, L10, L11, L12, L13, L14, L15, KC_NO },                      \
    { L27, L20, L21, L22, L23, L24, L25, KC_NO },                      \
    { L37, L30, L31, L32, L33, L34, L35, KC_NO },                      \
    { L47, L40, L41, L42, L43, KC_NO, KC_NO, KC_NO },                  \
    { R50, R51, R52, R53, R54, R55, R56, KC_NO },                      \
    { R60, R61, R62, R63, R64, R65, R66, R67 },                        \
    { R70, R71, R72, R73, R74, R75, R76, KC_NO },                      \
    { R80, R81, R82, R83, R84, R85, R86, KC_NO },                      \
    { R90, R91, R92, R93, R94, R95, R96, KC_NO }                       \
}
