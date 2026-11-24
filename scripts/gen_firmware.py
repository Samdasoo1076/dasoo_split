"""Write the QMK ``info.json`` and VIAL ``vial.json`` from the PCB layout.

The physical key table in :mod:`pcbgen.layout` is the single source of truth, so
the firmware metadata can never drift from the board again.

Run:  python3 scripts/gen_firmware.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from pcbgen.layout import keys, matrix_size   # noqa: E402

ROOT = os.path.dirname(HERE)
FW = os.path.join(ROOT, "firmware", "choc_split_60")

# The right half is rebased on its own left edge, so in the combined JSON view
# it starts where a full ANSI board has ``Y`` -- 6.5 u right of ``Tab``.  That
# reproduces the real ANSI stagger across the split seam.
RIGHT_OFFSET = 6.5      # key units between the two halves in the JSON view
X_SHIFT = 2.0           # keep every coordinate positive

ROW_PINS = ["GP2", "GP3", "GP4", "GP5", "GP6"]
COL_PINS = ["GP7", "GP8", "GP9", "GP20", "GP21", "GP22", "GP23", "GP26",
            "GP27"]


def ordered_keys():
    """Every key in LAYOUT order: left half row by row, then the right half."""
    out = []
    for hand in ("left", "right"):
        out.extend(keys(hand))
    return out


def pos(hand, k):
    x = k["xu"] + X_SHIFT + (0.0 if hand == "left" else RIGHT_OFFSET)
    return round(x, 3), k["row"]


def matrix_row(hand, k):
    return k["row"] + (0 if hand == "left" else 5)


def info_json():
    layout = []
    for hand in ("left", "right"):
        for k in keys(hand):
            x, y = pos(hand, k)
            layout.append({"matrix": [matrix_row(hand, k), k["col"]],
                           "x": x, "y": y, "w": k["wu"]})
    ex, ey = pos("left", keys("left")[0])
    doc = {
        "keyboard_name": "choc-split-60",
        "manufacturer": "choc-split-60",
        "url": "https://github.com/Samdasoo1076/dasoo_split",
        "maintainer": "Samdasoo1076",
        "usb": {"device_version": "1.1.0", "pid": "0x6330"},
        "processor": "RP2040",
        "bootloader": "rp2040",
        "diode_direction": "COL2ROW",
        "features": {
            "bootmagic": False,
            "mousekey": False,
            "extrakey": True,
            "console": False,
            "command": False,
            "nkro": True,
            "backlight": False,
            "rgblight": False,
            "audio": False,
        },
        "matrix_pins": {"rows": ROW_PINS, "cols": COL_PINS},
        "encoder": {"rotary": [{"x": ex, "y": ey, "w": 1}]},
        "split": {"enabled": True, "serial": {"driver": "vendor"}},
        "layouts": {"LAYOUT": layout},
    }
    return doc


def vial_json():
    km = []
    for hand in ("left", "right"):
        for k in keys(hand):
            x, y = pos(hand, k)
            km.append([x, y, k["wu"]] if abs(k["wu"] - 1.0) > 1e-9 else [x, y])
    rows = matrix_size("left")[0]
    cols = max(matrix_size("left")[1], matrix_size("right")[1])
    return {
        "name": "choc-split-60",
        "vendorId": "0xFEED",
        "productId": "0x6330",
        "matrix": {"rows": rows * 2, "cols": cols},
        "layouts": {"keymap": [km]},
    }


def matrix_name(hand, k):
    """QMK matrix position of a key, e.g. ``L07`` / ``R88``."""
    row = k["row"] + (0 if hand == "left" else 5)
    return "%s%d%d" % ("L" if hand == "left" else "R", row, k["col"])


def header_c():
    """The ``LAYOUT`` macro, generated from the same key table as the PCB."""
    rows = {}
    arg_rows = []
    for hand in ("left", "right"):
        for k in keys(hand):
            rows.setdefault((hand, k["row"]), {})[k["col"]] = matrix_name(hand, k)
            arg_rows.append(matrix_name(hand, k))
    ncol = max(max(c for c in r) for r in rows.values()) + 1
    nrow = len(rows)
    body = []
    for (hand, r), cols in rows.items():
        cells = [cols.get(c, "KC_NO") for c in range(ncol)]
        body.append("{ %s }" % ", ".join(cells))
    # wrap the argument list, 8 names per line
    chunks = [arg_rows[i:i + 8] for i in range(0, len(arg_rows), 8)]
    arg_lines = []
    for i, chunk in enumerate(chunks):
        text = "    " + ", ".join(chunk)
        if i < len(chunks) - 1:
            text += ","
        arg_lines.append(text)
    body_lines = ["    " + line + ("," if i < len(body) - 1 else "")
                  for i, line in enumerate(body)]
    width = max(len(t) for t in arg_lines + body_lines)

    def cont(lines):
        return " \\\n".join(t.ljust(width) for t in lines)

    out = []
    a = out.append
    a("/* Copyright 2026 choc-split-60 contributors")
    a(" *")
    a(" * This program is free software: you can redistribute it and/or modify")
    a(" * it under the terms of the GNU General Public License as published by")
    a(" * the Free Software Foundation, either version 2 of the License, or")
    a(" * (at your option) any later version.")
    a(" */")
    a("#pragma once")
    a("")
    a('#include "quantum.h"')
    a("")
    a("/* Layout of the two halves.  Each argument is <hand><matrix row><matrix col>.")
    a(" * Generated by scripts/gen_firmware.py from scripts/pcbgen/layout.py, so this")
    a(" * header, the PCB and the VIAL layout can never disagree.")
    a(" *")
    a(" * %d key positions, row by row, left half first; %d rows x %d columns per"
      % (len(arg_rows), nrow // 2, ncol))
    a(" * half (%d x %d in QMK, the right half's rows are 5..9)." % (nrow, ncol))
    a(" *")
    a(" *   row 0 : ENC  Esc 1 2 3 4 5 6       | 7 8 9 0 - = ` BSpc")
    a(" *   row 1 : Home Tab Q W E R T         | Y U I O P [ ] backslash")
    a(" *   row 2 : End  Caps A S D F G        | H J K L ; ' Enter")
    a(" *   row 3 : PgUp LShift Z X C V B      | B N M , . / RShift Up Del")
    a(" *   row 4 : PgDn LCtrl LWin LAlt Space | Space RAlt RCtrl Left Down Right")
    a(" */")
    a("#define LAYOUT(                                                   \\")
    a(cont(arg_lines))
    a(") {                                                           \\")
    a(cont(body_lines))
    a("}")
    return "\n".join(out) + "\n"


def main():
    with open(os.path.join(FW, "info.json"), "w") as f:
        json.dump(info_json(), f, indent=2)
        f.write("\n")
    with open(os.path.join(FW, "keymaps", "vial", "vial.json"), "w") as f:
        json.dump(vial_json(), f, indent=2)
        f.write("\n")
    with open(os.path.join(FW, "choc_split_60.h"), "w") as f:
        f.write(header_c())
    n = len(ordered_keys())
    print("wrote info.json, vial.json and choc_split_60.h for %d key positions" % n)


if __name__ == "__main__":
    main()
