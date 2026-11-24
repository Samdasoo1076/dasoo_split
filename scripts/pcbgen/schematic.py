"""KiCad schematic writer for the choc-split-60 halves (v7 format)."""
import random as _random

_RNG = _random.Random(20260618)


def u():
    h = "%032x" % _RNG.getrandbits(128)
    return "%s-%s-4%s-a%s-%s" % (h[0:8], h[8:12], h[13:16], h[17:20], h[20:32])


def num(v):
    s = "%.4f" % float(v)
    s = s.rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


LIB_SW = '''    (symbol "choc60:SW_Push" (pin_numbers hide) (pin_names (offset 1.016) hide) (in_bom yes) (on_board yes)
      (property "Reference" "SW" (at 0 3.81 0)
        (effects (font (size 1.27 1.27))))
      (property "Value" "SW_Push" (at 0 -2.54 0)
        (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide))
      (symbol "SW_Push_0_1"
        (circle (center -2.032 0) (radius 0.508)
          (stroke (width 0) (type default)) (fill (type none)))
        (circle (center 2.032 0) (radius 0.508)
          (stroke (width 0) (type default)) (fill (type none)))
        (polyline (pts (xy -2.54 1.27) (xy 2.54 1.27))
          (stroke (width 0) (type default)) (fill (type none)))
        (polyline (pts (xy 0 1.27) (xy 0 3.048))
          (stroke (width 0) (type default)) (fill (type none)))
      )
      (symbol "SW_Push_1_1"
        (pin passive line (at -5.08 0 0) (length 2.54)
          (name "1" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 5.08 0 180) (length 2.54)
          (name "2" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27)))))
      )
    )'''

LIB_D = '''    (symbol "choc60:D" (pin_numbers hide) (pin_names (offset 1.016) hide) (in_bom yes) (on_board yes)
      (property "Reference" "D" (at 0 2.54 0)
        (effects (font (size 1.27 1.27))))
      (property "Value" "1N4148W" (at 0 -2.54 0)
        (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide))
      (symbol "D_0_1"
        (polyline (pts (xy -1.27 1.27) (xy -1.27 -1.27))
          (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy 1.27 1.27) (xy 1.27 -1.27) (xy -1.27 0) (xy 1.27 1.27))
          (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy -3.81 0) (xy -1.27 0))
          (stroke (width 0) (type default)) (fill (type none)))
        (polyline (pts (xy 1.27 0) (xy 3.81 0))
          (stroke (width 0) (type default)) (fill (type none)))
      )
      (symbol "D_1_1"
        (pin passive line (at -3.81 0 0) (length 2.54)
          (name "K" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 3.81 0 180) (length 2.54)
          (name "A" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27)))))
      )
    )'''

LIB_TRRS = '''    (symbol "choc60:TRRS" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
      (property "Reference" "J" (at 0 8.89 0)
        (effects (font (size 1.27 1.27))))
      (property "Value" "PJ-320A" (at 0 -8.89 0)
        (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide))
      (symbol "TRRS_0_1"
        (rectangle (start -5.08 6.35) (end 5.08 -6.35)
          (stroke (width 0.254) (type default)) (fill (type background)))
        (text "TRRS" (at 0 4.445 0)
          (effects (font (size 1.27 1.27))))
      )
      (symbol "TRRS_1_1"
        (pin passive line (at 7.62 3.81 180) (length 2.54)
          (name "SLEEVE" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 7.62 1.27 180) (length 2.54)
          (name "TIP" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 7.62 -1.27 180) (length 2.54)
          (name "RING1" (effects (font (size 1.27 1.27))))
          (number "3" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 7.62 -3.81 180) (length 2.54)
          (name "RING2" (effects (font (size 1.27 1.27))))
          (number "4" (effects (font (size 1.27 1.27)))))
      )
    )'''

LIB_ENC = '''    (symbol "choc60:RotaryEncoder_SW" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
      (property "Reference" "RE" (at 0 8.89 0)
        (effects (font (size 1.27 1.27))))
      (property "Value" "EC11" (at 0 -8.89 0)
        (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide))
      (symbol "RotaryEncoder_SW_0_1"
        (rectangle (start -7.62 6.35) (end 7.62 -6.35)
          (stroke (width 0.254) (type default)) (fill (type background)))
        (text "ROTARY" (at 0 3.175 0)
          (effects (font (size 1.27 1.27))))
        (text "+ SW" (at 0 -0.635 0)
          (effects (font (size 1.27 1.27))))
      )
      (symbol "RotaryEncoder_SW_1_1"
        (pin passive line (at -10.16 2.54 0) (length 2.54)
          (name "A" (effects (font (size 1.016 1.016))))
          (number "A" (effects (font (size 1.016 1.016)))))
        (pin passive line (at -10.16 0 0) (length 2.54)
          (name "C" (effects (font (size 1.016 1.016))))
          (number "C" (effects (font (size 1.016 1.016)))))
        (pin passive line (at -10.16 -2.54 0) (length 2.54)
          (name "B" (effects (font (size 1.016 1.016))))
          (number "B" (effects (font (size 1.016 1.016)))))
        (pin passive line (at 10.16 2.54 180) (length 2.54)
          (name "S1" (effects (font (size 1.016 1.016))))
          (number "S1" (effects (font (size 1.016 1.016)))))
        (pin passive line (at 10.16 -2.54 180) (length 2.54)
          (name "S2" (effects (font (size 1.016 1.016))))
          (number "S2" (effects (font (size 1.016 1.016)))))
      )
    )'''

MCU_NAMES = [
    ("1", "GP0"), ("2", "GP1"), ("3", "GND"), ("4", "GND"),
    ("5", "GP2"), ("6", "GP3"), ("7", "GP4"), ("8", "GP5"),
    ("9", "GP6"), ("10", "GP7"), ("11", "GP8"), ("12", "GP9"),
    ("13", "RAW"), ("14", "GND"), ("15", "RST"), ("16", "VCC"),
    ("17", "GP29"), ("18", "GP28"), ("19", "GP27"), ("20", "GP26"),
    ("21", "GP22"), ("22", "GP20"), ("23", "GP23"), ("24", "GP21"),
]


def mcu_pin_y(number):
    """Local symbol y of a pin (canvas y = symbol_y - local_y)."""
    n = int(number)
    if n <= 12:
        return 13.97 - 2.54 * (n - 1)
    return 13.97 - 2.54 * (n - 13)


def lib_mcu():
    o = []
    o.append('    (symbol "choc60:ProMicro_RP2040" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)')
    o.append('      (property "Reference" "U" (at -10.16 21.59 0)\n        (effects (font (size 1.27 1.27))))')
    o.append('      (property "Value" "RP2040 Pro Micro" (at 0 21.59 0)\n        (effects (font (size 1.27 1.27))))')
    o.append('      (property "Footprint" "" (at 0 0 0)\n        (effects (font (size 1.27 1.27)) hide))')
    o.append('      (property "Datasheet" "" (at 0 0 0)\n        (effects (font (size 1.27 1.27)) hide))')
    o.append('      (symbol "ProMicro_RP2040_0_1"')
    o.append('        (rectangle (start -10.16 17.78) (end 10.16 -17.78)')
    o.append('          (stroke (width 0.254) (type default)) (fill (type background)))')
    o.append('        (text "USB" (at 0 16.51 0) (effects (font (size 1.27 1.27))))')
    o.append('      )')
    o.append('      (symbol "ProMicro_RP2040_1_1"')
    for num_, name in MCU_NAMES:
        y = mcu_pin_y(num_)
        if int(num_) <= 12:
            o.append('        (pin passive line (at -12.7 %s 0) (length 2.54)' % num(y))
        else:
            o.append('        (pin passive line (at 12.7 %s 180) (length 2.54)' % num(y))
        o.append('          (name "%s" (effects (font (size 1.016 1.016))))' % name)
        o.append('          (number "%s" (effects (font (size 1.016 1.016)))))' % num_)
    o.append('      )')
    o.append('    )')
    return "\n".join(o)


def label(name, x, y, angle=0, justify="left"):
    return ('  (label "%s" (at %s %s %s)\n'
            '    (effects (font (size 1.27 1.27)) (justify %s bottom))\n'
            '    (uuid "%s")\n  )' % (name, num(x), num(y), angle, justify, u()))


def wire(a, b):
    return ('  (wire (pts (xy %s %s) (xy %s %s))\n'
            '    (stroke (width 0) (type default))\n    (uuid "%s")\n  )'
            % (num(a[0]), num(a[1]), num(b[0]), num(b[1]), u()))


def sym(lib, ref, value, x, y, pins, project, root, footprint="", angle=0, mirror=None):
    o = []
    o.append('  (symbol (lib_id "%s") (at %s %s %s) (unit 1)' % (lib, num(x), num(y), num(angle)))
    o.append('    (in_bom yes) (on_board yes) (dnp no) (fields_autoplaced)')
    o.append('    (uuid "%s")' % u())
    o.append('    (property "Reference" "%s" (at %s %s 0)' % (ref, num(x), num(y - 5.08)))
    o.append('      (effects (font (size 1.27 1.27))))')
    o.append('    (property "Value" "%s" (at %s %s 0)' % (value, num(x), num(y + 5.08)))
    o.append('      (effects (font (size 1.27 1.27))))')
    o.append('    (property "Footprint" "%s" (at %s %s 0)' % (footprint, num(x), num(y)))
    o.append('      (effects (font (size 1.27 1.27)) hide))')
    o.append('    (property "Datasheet" "" (at %s %s 0)' % (num(x), num(y)))
    o.append('      (effects (font (size 1.27 1.27)) hide))')
    for p in pins:
        o.append('    (pin "%s" (uuid "%s"))' % (p, u()))
    o.append('    (instances (project "%s" (path "/%s" (reference "%s") (unit 1))))'
             % (project, root, ref))
    o.append('  )')
    return "\n".join(o)


def write_schematic(board, path, project=None, root=None):
    project = project or ("choc-split-60-%s" % board.hand)
    root = root or u()
    o = []
    o.append('(kicad_sch (version 20230121) (generator eeschema)')
    o.append('  (uuid "%s")' % root)
    o.append('  (paper "A3")')
    o.append('  (lib_symbols')
    o.append(LIB_SW)
    o.append(LIB_D)
    o.append(lib_mcu())
    o.append(LIB_TRRS)
    o.append(LIB_ENC)
    o.append('  )')
    body = []
    grid = [k for k in board.keys if k["kind"] != "encoder"]
    for i, k in enumerate(grid):
        col_i = i % 8
        row_i = i // 8
        x = 30.0 + 34.0 * col_i
        y = 28.0 + 24.0 * row_i
        # switch
        body.append(sym("choc60:SW_Push", k["ref"], "%s (%s)" % (k["label"], "%.2fu" % k["wu"]),
                        x, y, ["1", "2"], project, root,
                        footprint="choc60:%s" % k["sw"].name.replace("choc60", "")))
        body.append(wire((x - 5.08, y), (x - 7.62, y)))
        body.append(label(k["col_net"], x - 7.62, y, 0, "left"))
        body.append(wire((x + 5.08, y), (x + 7.62, y)))
        body.append(label(k["knet"], x + 7.62, y, 0, "right"))
        # diode
        dy = y + 11.0
        body.append(sym("choc60:D", k["dref"], "1N4148W", x, dy, ["1", "2"], project, root,
                        footprint="choc60:D_SOD-123"))
        body.append(wire((x - 3.81, dy), (x - 6.35, dy)))
        body.append(label(k["row_net"], x - 6.35, dy, 0, "left"))
        body.append(wire((x + 3.81, dy), (x + 6.35, dy)))
        body.append(label(k["knet"], x + 6.35, dy, 0, "right"))
    # controller
    mx, my = 320.0, 60.0
    body.append(sym("choc60:ProMicro_RP2040", "U1", "RP2040 Pro Micro", mx, my,
                    [str(i) for i in range(1, 25)], project, root,
                    footprint="choc60:ProMicro_RP2040"))
    for num_, name in MCU_NAMES:
        y = my - mcu_pin_y(num_)
        net = _mcu_net(board, name)
        left = int(num_) <= 12
        px_ = mx - 12.7 if left else mx + 12.7
        if net is None:
            body.append('  (no_connect (at %s %s) (uuid "%s"))' % (num(px_), num(y), u()))
            continue
        if left:
            body.append(wire((px_, y), (mx - 17.78, y)))
            body.append(label(net, mx - 17.78, y, 0, "right"))
        else:
            body.append(wire((px_, y), (mx + 17.78, y)))
            body.append(label(net, mx + 17.78, y, 0, "left"))
    # trrs
    jx, jy = 330.0, 150.0
    body.append(sym("choc60:TRRS", "J1", "PJ-320A", jx, jy, ["1", "2", "3", "4"], project, root,
                    footprint="choc60:TRRS_PJ-320A"))
    trrs = {"SLEEVE": "RX" if board.hand == "left" else "TX",
            "TIP": "VCC", "RING1": "GND",
            "RING2": "TX" if board.hand == "left" else "RX"}
    for pnum, pname, yy in (("1", "SLEEVE", 3.81), ("2", "TIP", 1.27),
                            ("3", "RING1", -1.27), ("4", "RING2", -3.81)):
        body.append(wire((jx + 7.62, jy - yy), (jx + 12.7, jy - yy)))
        body.append(label(trrs[pname], jx + 12.7, jy - yy, 0, "left"))
    # reset switch
    rx, ry = 250.0, 248.0
    body.append(sym("choc60:SW_Push", "SW_RST", "Reset", rx, ry, ["1", "2"], project, root,
                    footprint="choc60:SW_Reset_6mm"))
    body.append(wire((rx - 5.08, ry), (rx - 7.62, ry)))
    body.append(label("RST", rx - 7.62, ry, 0, "left"))
    body.append(wire((rx + 5.08, ry), (rx + 7.62, ry)))
    body.append(label("GND", rx + 7.62, ry, 0, "right"))
    # rotary encoder and its matrix diode (left half only)
    if any(k["kind"] == "encoder" for k in board.keys):
        ex, ey = 60.0, 248.0
        body.append(sym("choc60:RotaryEncoder_SW", "RE1", "EC11 rotary encoder", ex, ey,
                        ["A", "C", "B", "S1", "S2"], project, root,
                        footprint="choc60:RotaryEncoder_EC11"))
        for pname, py_, net in (("A", 2.54, "ENC_A"), ("C", 0.0, "GND"),
                                ("B", -2.54, "ENC_B")):
            body.append(wire((ex - 10.16, ey - py_), (ex - 15.24, ey - py_)))
            body.append(label(net, ex - 15.24, ey - py_, 0, "right"))
        for pname, py_, net in (("S1", 2.54, "COL7"), ("S2", -2.54, "K_ENC")):
            body.append(wire((ex + 10.16, ey - py_), (ex + 15.24, ey - py_)))
            body.append(label(net, ex + 15.24, ey - py_, 0, "left"))
        dx, dy = 150.0, 252.0
        body.append(sym("choc60:D", "D_ENC", "1N4148W", dx, dy, ["1", "2"], project, root,
                        footprint="choc60:D_SOD-123"))
        body.append(wire((dx - 3.81, dy), (dx - 6.35, dy)))
        body.append(label("ROW0", dx - 6.35, dy, 0, "left"))
        body.append(wire((dx + 3.81, dy), (dx + 6.35, dy)))
        body.append(label("K_ENC", dx + 6.35, dy, 0, "right"))
    # notes
    o.extend(body)
    nsw = sum(1 for k in board.keys if k["kind"] == "switch")
    enc = " + 1 rotary encoder" if any(k["kind"] == "encoder" for k in board.keys) else ""
    o.append('  (text "choc-split-60 %s - row staggered split, %d Choc v1 hot swap keys%s,'
             ' RP2040 Pro Micro, COL2ROW" (at %s 282 0)'
             % (board.hand, nsw, enc, num(30)))
    o.append('    (effects (font (size 2 2)) (justify left bottom))')
    o.append('    (uuid "%s")' % u())
    o.append('  )')
    o.append('  (sheet_instances (path "/" (page "1")))')
    o.append(')')
    with open(path, "w") as f:
        f.write("\n".join(o) + "\n")
    return root


def _mcu_net(board, name):
    for p in board.mcu.pads:
        if p.name == name:
            return p.net
    return None
