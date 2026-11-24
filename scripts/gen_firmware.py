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
COL_PINS = ["GP7", "GP8", "GP9", "GP20", "GP21", "GP22", "GP23", "GP26"]


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
    rows, cols = matrix_size("left")
    return {
        "name": "choc-split-60",
        "vendorId": "0xFEED",
        "productId": "0x6330",
        "matrix": {"rows": rows * 2, "cols": cols},
        "layouts": {"keymap": [km]},
    }


def main():
    with open(os.path.join(FW, "info.json"), "w") as f:
        json.dump(info_json(), f, indent=2)
        f.write("\n")
    with open(os.path.join(FW, "keymaps", "vial", "vial.json"), "w") as f:
        json.dump(vial_json(), f, indent=2)
        f.write("\n")
    n = len(ordered_keys())
    print("wrote info.json and vial.json for %d key positions" % n)


if __name__ == "__main__":
    main()
