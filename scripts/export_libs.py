"""Export the choc60 footprints as a .pretty library next to the projects."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from pcbgen import parts                    # noqa: E402
from pcbgen.build import num, u             # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "libs", "choc60.pretty")


def mod_text(name, spec):
    o = []
    a = o.append
    a('(footprint "%s"' % name)
    a('  (version 20241229)')
    a('  (generator "pcbnew")')
    a('  (layer "F.Cu")')
    a('  (descr "%s")' % spec.get("descr", ""))
    a('  (tags "%s")' % spec.get("tags", ""))
    if spec.get("attr"):
        a('  (attr %s)' % spec["attr"])
    a('  (fp_text reference "REF**" (at 0 -10.2) (layer "F.SilkS")')
    a('    (effects (font (size 1 1) (thickness 0.15))))')
    a('  (fp_text value "%s" (at 0 10.2) (layer "F.Fab")' % name)
    a('    (effects (font (size 1 1) (thickness 0.15))))')
    for g in spec["graphics"]:
        layer, width = g[3], g[4]
        if g[0] == "line":
            (x1, y1), (x2, y2) = g[1], g[2]
            a('  (fp_line (start %s %s) (end %s %s)' % (num(x1), num(y1), num(x2), num(y2)))
            a('    (stroke (width %s) (type solid)) (layer "%s") (uuid "%s"))'
              % (num(width), layer, u()))
        elif g[0] == "circle":
            (cx, cy), r = g[1], g[2][1]
            a('  (fp_circle (center %s %s) (end %s %s)' % (num(cx), num(cy), num(cx + r), num(cy)))
            a('    (stroke (width %s) (type solid)) (fill no) (layer "%s") (uuid "%s"))'
              % (num(width), layer, u()))
    for p in spec["pads"]:
        layers = " ".join('"%s"' % l for l in p.get("layers", ["F.Cu"]))
        a('  (pad "%s" %s %s (at %s %s) (size %s %s)'
          % (p.get("num", ""), p["kind"], p["shape"], num(p["lx"]), num(p["ly"]),
             num(p["w"]), num(p.get("h", p["w"]))))
        if p["kind"] != "smd":
            dr = p.get("drill", (0, 0))
            if dr[0] == dr[1]:
                a('    (drill %s)' % num(dr[0]))
            else:
                a('    (drill oval %s %s)' % (num(dr[0]), num(dr[1])))
        a('    (layers %s)' % layers)
        if p["shape"] == "roundrect":
            a('    (roundrect_rratio %s)' % num(p.get("rratio", 0.1)))
        a('    (uuid "%s"))' % u())
    a('  (embedded_fonts no)')
    a(')')
    return "\n".join(o) + "\n"


def main():
    os.makedirs(OUT, exist_ok=True)
    specs = []
    for w in (1.0, 1.25, 1.5, 1.75, 2.0, 2.25):
        sp = parts.choc_hotswap(w)
        specs.append((sp["name"], sp))
    sp = parts.diode_sod123(kbar_right=False)
    specs.append(("D_SOD-123", sp))
    sp = parts.diode_sod123(kbar_right=True)
    specs.append(("D_SOD-123_BackSide", sp))
    sp = parts.pro_micro_rp2040(mirror=False)
    specs.append(("ProMicro_RP2040", sp))
    sp = parts.pro_micro_rp2040(mirror=True)
    specs.append(("ProMicro_RP2040_Mirrored", sp))
    for name, fn in (("TRRS_PJ-320A", parts.trrs_pj320a),
                     ("SW_Reset_6mm", parts.reset_switch),
                     ("MountingHole_M2", parts.mount_hole_m2)):
        sp = fn()
        specs.append((name, sp))
    for name, sp in specs:
        with open(os.path.join(OUT, name + ".kicad_mod"), "w") as f:
            f.write(mod_text(name, sp))
    print("wrote %d footprints to %s" % (len(specs), OUT))


if __name__ == "__main__":
    main()
