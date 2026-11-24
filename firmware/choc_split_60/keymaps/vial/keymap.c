/* Copyright 2026 choc-split-60 contributors
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 2 of the License, or
 * (at your option) any later version.
 */
#include QMK_KEYBOARD_H

enum layers { _BASE, _FN, _NAV };

/* Layer access lives on the two space bars, since the right half no longer has
 * an RFn key: hold the left space for _FN (F row, numbers, media) and hold the
 * right space for _NAV (Home/PgUp/PgDn/End on the top rows).  Both are
 * layer-taps, tap = plain space.  With TAPPING_TERM 180 / PERMISSIVE_HOLD a
 * quick tap always types a space, even when the next key follows fast.
 *
 * clang-format off */
const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
    [_BASE] = LAYOUT(
        KC_MUTE, KC_GRV,  KC_1,    KC_2,    KC_3,    KC_4,    KC_5,    KC_6,
        KC_HOME, KC_TAB,  KC_Q,    KC_W,    KC_E,    KC_R,    KC_T,
        KC_END,  KC_CAPS, KC_A,    KC_S,    KC_D,    KC_F,    KC_G,
        KC_PGUP, KC_LSFT, KC_Z,    KC_X,    KC_C,    KC_V,    KC_B,
        KC_PGDN, KC_LCTL, KC_LGUI, KC_LALT, LT(_FN, KC_SPC),
        KC_7,    KC_8,    KC_9,    KC_0,    KC_MINS, KC_EQL,  KC_BSPC,
        KC_Y,    KC_U,    KC_I,    KC_O,    KC_P,    KC_LBRC, KC_RBRC, KC_BSLS,
        KC_H,    KC_J,    KC_K,    KC_L,    KC_SCLN, KC_QUOT, KC_ENT,
        KC_B,    KC_N,    KC_M,    KC_COMM, KC_DOT,  KC_SLSH, KC_RSFT, KC_UP,   KC_DEL,
        LT(_NAV, KC_SPC), KC_RALT, KC_RCTL, KC_LEFT, KC_DOWN, KC_RGHT
    ),
    [_FN] = LAYOUT(
        KC_MUTE, KC_ESC,  KC_F1,   KC_F2,     KC_F3,   KC_F4,   KC_F5,   KC_F6,
        KC_HOME, KC_TAB,  KC_1,    KC_2,      KC_3,    KC_4,    KC_5,
        KC_END,  KC_CAPS, KC_6,    KC_7,      KC_8,    KC_9,    KC_0,
        KC_PGUP, KC_LSFT, KC_F7,   KC_F8,     KC_F9,   KC_F10,  KC_F11,
        KC_PGDN, KC_LCTL, KC_LGUI, KC_LALT,   _______,
        KC_F7,   KC_F8,   KC_F9,   KC_F10,    KC_F11,  KC_F12,  KC_DEL,
        KC_PSCR, KC_SCRL, KC_PAUS, KC_INS,    KC_HOME, KC_PGDN, KC_PGUP, KC_END,
        KC_LEFT, KC_DOWN, KC_UP,   KC_RGHT,   KC_MUTE, KC_VOLD, KC_VOLU,
        KC_MPRV, KC_MPLY, KC_MNXT, KC_MSTP,   KC_APP,  KC_RSFT, _______, KC_PGUP, KC_DEL,
        _______, KC_RALT, KC_RCTL, KC_HOME,   KC_PGDN, KC_END
    ),
    [_NAV] = LAYOUT(
        _______, _______, _______, _______, _______, _______, _______, _______,
        _______, _______, _______, _______, _______, _______, _______,
        _______, _______, _______, _______, _______, _______, _______,
        _______, _______, _______, _______, _______, _______, _______,
        _______, _______, _______, _______, _______,
        _______, _______, _______, _______, _______, _______, _______,
        KC_HOME, KC_PGDN, KC_PGUP, KC_END,  _______, _______, _______, _______,
        KC_LEFT, KC_DOWN, KC_UP,   KC_RGHT, _______, _______, _______,
        _______, _______, _______, _______, _______, _______, _______, KC_PGUP, _______,
        _______, _______, _______, KC_HOME, KC_PGDN, KC_END
    ),
};

#ifdef ENCODER_MAP_ENABLE
/* one encoder, two directions per layer: counter clockwise, clockwise */
const uint16_t PROGMEM encoder_map[][NUM_ENCODERS][NUM_DIRECTIONS] = {
    [_BASE] = { { KC_VOLD, KC_VOLU } },
    [_FN]   = { { KC_PGDN, KC_PGUP } },
    [_NAV]  = { { KC_MPRV, KC_MNXT } },
};
#endif
/* clang-format on */
