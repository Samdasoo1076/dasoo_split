"""Footprint models (KiCad 9 syntax) used by the choc-split-60 boards."""
import math
from .geom import U, place

BACK_MAP = {
    "F.Cu": "B.Cu", "B.Cu": "F.Cu",
    "F.SilkS": "B.SilkS", "B.SilkS": "F.SilkS",
    "F.Fab": "B.Fab", "B.Fab": "F.Fab",
    "F.CrtYd": "B.CrtYd", "B.CrtYd": "F.CrtYd",
    "F.Mask": "B.Mask", "B.Mask": "F.Mask",
    "F.Paste": "B.Paste", "B.Paste": "F.Paste",
    "*.Cu": "*.Cu", "*.Mask": "*.Mask",
}


class Pad:
    def __init__(self, num, kind, shape, lx, ly, w, h=None, ang=0.0,
                 layers=("F.Cu",), net=None, drill=(0.0, 0.0), rratio=0.1,
                 name="", locked=False):
        self.num = num
        self.kind = kind          # smd | thru_hole | np_thru_hole
        self.shape = shape        # circle | oval | rect | roundrect
        self.lx, self.ly = lx, ly
        self.w = w
        self.h = w if h is None else h
        self.lang = ang
        self.layers = tuple(layers)
        self.net = net
        self.drill = drill
        self.rratio = rratio
        self.name = name
        # filled in by Footprint.place()
        self.gx = self.gy = 0.0
        self.gang = 0.0
        self.glayers = self.layers
        self.fp = None

    # -- geometry -----------------------------------------------------------
    @property
    def is_hole(self):
        return self.kind == "np_thru_hole"

    def on_layer(self, layer):
        if self.is_hole:
            return True
        return layer in self.glayers or "*.Cu" in self.glayers

    def pad_layers(self):
        """Copper layers the pad lives on."""
        out = []
        for L in self.glayers:
            if L == "*.Cu":
                return ["F.Cu", "B.Cu"]
            if L in ("F.Cu", "B.Cu"):
                out.append(L)
        return out

    def __repr__(self):
        return "<Pad %s.%s %s %.2f,%.2f>" % (
            self.fp.ref if self.fp else "?", self.num, self.shape, self.gx, self.gy)


class Footprint:
    def __init__(self, lib, name, ref, value, px, py, ang=0.0, side="F",
                 pads=(), graphics=(), attr=None, descr="", tags="",
                 pin_names=None):
        self.lib = lib
        self.name = name
        self.ref = ref
        self.value = value
        self.px, self.py, self.ang, self.side = px, py, ang, side
        self.attr = attr
        self.descr = descr
        self.tags = tags
        self.graphics = list(graphics)
        self.pads = []
        for p in pads:
            p = Pad(**p) if isinstance(p, dict) else p
            p.fp = self
            p.gx, p.gy = place(px, py, p.lx, p.ly, ang, side)
            p.gang = ang - p.lang if side == "F" else ang + p.lang
            # note: a mirrored pad's local rotation flips sign as well
            if side == "B":
                p.gang = ang + p.lang
            p.glayers = tuple(BACK_MAP.get(l, l) if side == "B" else l
                              for l in p.layers)
            self.pads.append(p)

    def pad(self, num):
        for p in self.pads:
            if p.num == str(num):
                return p
        raise KeyError("pad %s not in %s" % (num, self.ref))

    def named(self, name):
        for p in self.pads:
            if p.name == name:
                return p
        raise KeyError("pad name %s not in %s" % (name, self.ref))

    def __repr__(self):
        return "<Footprint %s %s>" % (self.name, self.ref)


# --------------------------------------------------------------- definitions
def choc_hotswap(width_u):
    """Kailh Choc v1 hot swap footprint (geometry from the
    keyswitch-kicad-library `SW_Hotswap_Kailh_Choc_V1V2` footprint)."""
    key_w = width_u * U
    pads = [
        dict(num="1", kind="smd", shape="roundrect", lx=-3.5, ly=-6.0,
             w=2.55, h=2.5, layers=("B.Cu", "B.Mask", "B.Paste"), rratio=0.1),
        dict(num="2", kind="smd", shape="roundrect", lx=8.5, ly=-3.8,
             w=2.55, h=2.5, layers=("B.Cu", "B.Mask", "B.Paste"), rratio=0.1),
        dict(num="", kind="np_thru_hole", shape="circle", lx=0, ly=-5.9, w=3.05, drill=(3.05, 3.05)),
        dict(num="", kind="np_thru_hole", shape="circle", lx=5, ly=-3.8, w=3.05, drill=(3.05, 3.05)),
        dict(num="", kind="np_thru_hole", shape="circle", lx=0, ly=0, w=5.05, drill=(5.05, 5.05)),
        dict(num="", kind="np_thru_hole", shape="circle", lx=-5.5, ly=0, w=1.9, drill=(1.9, 1.9)),
        dict(num="", kind="np_thru_hole", shape="circle", lx=5.5, ly=0, w=1.9, drill=(1.9, 1.9)),
        dict(num="", kind="np_thru_hole", shape="circle", lx=-5, ly=5.15, w=1.6, drill=(1.6, 1.6)),
    ]
    g = []
    # switch body outline
    for layer, wd, d in (("F.SilkS", 0.12, 7.6), ("F.Fab", 0.1, 7.5), ("F.CrtYd", 0.05, 7.75)):
        g += [("line", (-d, -d), (d, -d), layer, wd),
              ("line", (d, -d), (d, d), layer, wd),
              ("line", (d, d), (-d, d), layer, wd),
              ("line", (-d, d), (-d, -d), layer, wd)]
    if width_u > 1.0:
        hw = key_w / 2 - 0.6
        hh = U / 2 - 0.6
        g += [("line", (-hw, -hh), (hw, -hh), "F.Fab", 0.1),
              ("line", (hw, -hh), (hw, hh), "F.Fab", 0.1),
              ("line", (hw, hh), (-hw, hh), "F.Fab", 0.1),
              ("line", (-hw, hh), (-hw, -hh), "F.Fab", 0.1)]
    # centre mark
    g += [("line", (-1.0, 7.0), (1.0, 7.0), "F.SilkS", 0.12),
          ("line", (0, 6.0), (0, 8.0), "F.SilkS", 0.12)]
    return dict(
        name="SW_Hotswap_Kailh_Choc_V1_%s" % ("%.2fu" % width_u),
        attr="smd",
        descr="Kailh Choc v1 (CPG1350) hot swap socket, %.2fu key" % width_u,
        tags="kailh choc hotswap low profile",
        pads=pads, graphics=g)


def diode_sod123(kbar_right=False):
    """SOD-123 diode.  ``kbar_right`` swaps the pads so that the part, when
    placed on the back side (KiCad mirrors footprints there), keeps its
    cathode pad on the left and the silkscreen band next to it."""
    kx = 1.75 if kbar_right else -1.75
    ax = -kx
    pads = [
        dict(num="1", kind="smd", shape="roundrect", lx=kx, ly=0, w=1.3, h=1.5,
             layers=("F.Cu", "F.Mask", "F.Paste"), rratio=0.1, name="K"),
        dict(num="2", kind="smd", shape="roundrect", lx=ax, ly=0, w=1.3, h=1.5,
             layers=("F.Cu", "F.Mask", "F.Paste"), rratio=0.1, name="A"),
    ]
    bx = 1.6 if kbar_right else -1.6
    g = [("line", (-1.35, -0.85), (1.35, -0.85), "F.SilkS", 0.12),
         ("line", (1.35, -0.85), (1.35, 0.85), "F.SilkS", 0.12),
         ("line", (1.35, 0.85), (-1.35, 0.85), "F.SilkS", 0.12),
         ("line", (-1.35, 0.85), (-1.35, -0.85), "F.SilkS", 0.12),
         ("line", (bx, -0.95), (bx, 0.95), "F.SilkS", 0.2),   # cathode bar
         ("line", (-2.25, -1.0), (2.25, -1.0), "F.CrtYd", 0.05),
         ("line", (2.25, -1.0), (2.25, 1.0), "F.CrtYd", 0.05),
         ("line", (2.25, 1.0), (-2.25, 1.0), "F.CrtYd", 0.05),
         ("line", (-2.25, 1.0), (-2.25, -1.0), "F.CrtYd", 0.05)]
    return dict(name="D_SOD-123", attr="smd",
                descr="1N4148W small signal diode, SOD-123",
                tags="diode SOD-123", pads=pads, graphics=g)


PRO_MICRO_PINS = [
    # (pad number, name)
    ("1", "GP0"), ("2", "GP1"), ("3", "GND"), ("4", "GND"),
    ("5", "GP2"), ("6", "GP3"), ("7", "GP4"), ("8", "GP5"),
    ("9", "GP6"), ("10", "GP7"), ("11", "GP8"), ("12", "GP9"),
]


def pro_micro_rp2040(mirror=False):
    """RP2040 Pro Micro (Elite-Pi / SparkFun Pro Micro RP2040 pinout),
    drawn with the USB-C connector pointing to -X."""
    left_row = PRO_MICRO_PINS                     # y = +7.62
    right_row = [("13", "RAW"), ("14", "GND"), ("15", "RST"), ("16", "VCC"),
                 ("17", "GP29"), ("18", "GP28"), ("19", "GP27"), ("20", "GP26"),
                 ("21", "GP22"), ("22", "GP20"), ("23", "GP23"), ("24", "GP21")]
    pads = []
    for i, (num, name) in enumerate(left_row):
        lx = -13.97 + 2.54 * i
        pads.append(dict(num=num, kind="thru_hole", shape="circle", lx=lx, ly=7.62,
                         w=1.75, drill=(1.05, 1.05), layers=("*.Cu", "*.Mask"),
                         name=name))
    for i, (num, name) in enumerate(right_row):
        lx = -13.97 + 2.54 * i
        pads.append(dict(num=num, kind="thru_hole", shape="circle", lx=lx, ly=-7.62,
                         w=1.75, drill=(1.05, 1.05), layers=("*.Cu", "*.Mask"),
                         name=name))
    if mirror:
        for p in pads:
            p["lx"] = -p["lx"]
    g = []
    b = 16.51
    h = 8.89
    for layer, wd in (("F.SilkS", 0.12), ("F.Fab", 0.1), ("F.CrtYd", 0.05)):
        g += [("line", (-b, -h), (b, -h), layer, wd),
              ("line", (b, -h), (b, h), layer, wd),
              ("line", (b, h), (-b, h), layer, wd),
              ("line", (-b, h), (-b, -h), layer, wd)]
    # USB-C connector marker on the -X edge
    usb_x = -b
    g += [("line", (usb_x - 1.3, -4.0), (usb_x - 1.3, 4.0), "F.SilkS", 0.15),
          ("line", (usb_x - 1.3, -4.0), (usb_x, -4.0), "F.SilkS", 0.15),
          ("line", (usb_x - 1.3, 4.0), (usb_x, 4.0), "F.SilkS", 0.15),
          ("line", (usb_x - 3.0, -4.0), (usb_x - 3.0, 4.0), "F.CrtYd", 0.05)]
    # pin 1 marker
    p1 = pads[0]
    g += [("circle", (p1["lx"] + 0.0, -5.4), ("r", 0.35), "F.SilkS", 0.12)]
    return dict(name="ProMicro_RP2040", attr="through_hole",
                descr="RP2040 Pro Micro compatible controller (Pro Micro pinout)",
                tags="RP2040 Pro Micro Elite-Pi", pads=pads, graphics=g)


def trrs_pj320a():
    pads = [
        dict(num="1", kind="thru_hole", shape="oval", lx=-2.3, ly=11.3, w=1.6, h=2.0,
             drill=(0.9, 1.3), layers=("*.Cu", "*.Mask"), name="SLEEVE"),
        dict(num="2", kind="thru_hole", shape="oval", lx=2.3, ly=10.2, w=1.6, h=2.0,
             drill=(0.9, 1.3), layers=("*.Cu", "*.Mask"), name="TIP"),
        dict(num="3", kind="thru_hole", shape="oval", lx=2.3, ly=6.2, w=1.6, h=2.0,
             drill=(0.9, 1.3), layers=("*.Cu", "*.Mask"), name="RING1"),
        dict(num="4", kind="thru_hole", shape="oval", lx=2.3, ly=3.2, w=1.6, h=2.0,
             drill=(0.9, 1.3), layers=("*.Cu", "*.Mask"), name="RING2"),
        dict(num="", kind="np_thru_hole", shape="circle", lx=0, ly=8.6, w=0.8, drill=(0.8, 0.8)),
        dict(num="", kind="np_thru_hole", shape="circle", lx=0, ly=1.6, w=0.8, drill=(0.8, 0.8)),
    ]
    g = [("line", (-3.05, 12.1), (3.05, 12.1), "F.SilkS", 0.15),
         ("line", (3.05, 12.1), (3.05, 0), "F.SilkS", 0.15),
         ("line", (3.05, 0), (-3.05, 0), "F.SilkS", 0.15),
         ("line", (-3.05, 0), (-3.05, 12.1), "F.SilkS", 0.15),
         ("line", (-2.8, 0), (-2.8, -2.0), "F.SilkS", 0.15),
         ("line", (-2.8, -2.0), (2.8, -2.0), "F.SilkS", 0.15),
         ("line", (2.8, -2.0), (2.8, 0), "F.SilkS", 0.15),
         ("line", (-3.6, -2.6), (3.6, -2.6), "F.CrtYd", 0.05),
         ("line", (3.6, -2.6), (3.6, 12.6), "F.CrtYd", 0.05),
         ("line", (3.6, 12.6), (-3.6, 12.6), "F.CrtYd", 0.05),
         ("line", (-3.6, 12.6), (-3.6, -2.6), "F.CrtYd", 0.05)]
    return dict(name="TRRS_PJ-320A", attr="through_hole",
                descr="TRRS jack PJ-320A (4 pole, through hole)",
                tags="TRRS jack PJ-320A", pads=pads, graphics=g)


def reset_switch():
    pads = []
    for i, (lx, ly, nm) in enumerate([(-2.25, -3.25, "1"), (2.25, -3.25, "2"),
                                     (-2.25, 3.25, "3"), (2.25, 3.25, "4")]):
        pads.append(dict(num=nm, kind="thru_hole", shape="circle", lx=lx, ly=ly,
                         w=1.8, drill=(1.0, 1.0), layers=("*.Cu", "*.Mask")))
    g = [("line", (-3.0, -3.0), (3.0, -3.0), "F.SilkS", 0.15),
         ("line", (3.0, -3.0), (3.0, 3.0), "F.SilkS", 0.15),
         ("line", (3.0, 3.0), (-3.0, 3.0), "F.SilkS", 0.15),
         ("line", (-3.0, 3.0), (-3.0, -3.0), "F.SilkS", 0.15),
         ("line", (-3.4, -3.6), (3.4, -3.6), "F.CrtYd", 0.05),
         ("line", (3.4, -3.6), (3.4, 3.6), "F.CrtYd", 0.05),
         ("line", (3.4, 3.6), (-3.4, 3.6), "F.CrtYd", 0.05),
         ("line", (-3.4, 3.6), (-3.4, -3.6), "F.CrtYd", 0.05),
         ("circle", (0, 0), ("r", 1.2), "F.SilkS", 0.12)]
    return dict(name="SW_Reset_6mm", attr="through_hole",
                descr="6x6 mm tactile reset switch, 4.5 x 6.5 mm lead spacing",
                tags="tactile reset switch", pads=pads, graphics=g)


def rotary_ec11():
    """Alps EC11 / Bourns PEC11R compatible rotary encoder with push switch.

    Terminal geometry follows the Bourns PEC11R datasheet: the three encoder
    terminals A-C-B sit in one row at 2.5 mm pitch, the two switch terminals
    are 5 mm apart on the opposite side, and the two mounting posts are 2.1 mm
    diameter.  The shaft centre is the footprint origin; the 12.4 mm body sits
    on the PCB (no centre hole).  The encoder terminals point to -Y and the
    switch terminals to +Y, so the switch wiring drops towards the diode row.
    """
    pads = []
    for num, name, lx in (("A", "A", -2.5), ("C", "C", 0.0), ("B", "B", 2.5)):
        pads.append(dict(num=num, kind="thru_hole", shape="circle", lx=lx, ly=-7.5,
                         w=2.0, drill=(1.05, 1.05), layers=("*.Cu", "*.Mask"), name=name))
    for num, name, lx in (("S1", "S1", -2.5), ("S2", "S2", 2.5)):
        pads.append(dict(num=num, kind="thru_hole", shape="circle", lx=lx, ly=7.0,
                         w=2.0, drill=(1.05, 1.05), layers=("*.Cu", "*.Mask"), name=name))
    pads.append(dict(num="", kind="np_thru_hole", shape="circle", lx=-6.0, ly=0.0,
                     w=2.1, drill=(2.1, 2.1)))
    pads.append(dict(num="", kind="np_thru_hole", shape="circle", lx=6.0, ly=0.0,
                     w=2.1, drill=(2.1, 2.1)))
    g = [("line", (-6.2, -6.2), (6.2, -6.2), "F.SilkS", 0.12),
         ("line", (6.2, -6.2), (6.2, 6.2), "F.SilkS", 0.12),
         ("line", (6.2, 6.2), (-6.2, 6.2), "F.SilkS", 0.12),
         ("line", (-6.2, 6.2), (-6.2, -6.2), "F.SilkS", 0.12),
         ("line", (-6.2, -6.2), (6.2, -6.2), "F.Fab", 0.1),
         ("line", (6.2, -6.2), (6.2, 6.2), "F.Fab", 0.1),
         ("line", (6.2, 6.2), (-6.2, 6.2), "F.Fab", 0.1),
         ("line", (-6.2, 6.2), (-6.2, -6.2), "F.Fab", 0.1),
         ("circle", (0, 0), ("r", 3.0), "F.SilkS", 0.12),
         ("line", (-1.5, -8.6), (1.5, -8.6), "F.SilkS", 0.12),
         ("line", (0, -7.6), (0, -9.6), "F.SilkS", 0.12),
         ("line", (-7.2, -9.6), (7.2, -9.6), "F.CrtYd", 0.05),
         ("line", (7.2, -9.6), (7.2, 9.4), "F.CrtYd", 0.05),
         ("line", (7.2, 9.4), (-7.2, 9.4), "F.CrtYd", 0.05),
         ("line", (-7.2, 9.4), (-7.2, -9.6), "F.CrtYd", 0.05)]
    return dict(name="RotaryEncoder_EC11", attr="through_hole",
                descr="Alps EC11 / Bourns PEC11R rotary encoder with push switch (5 pin)",
                tags="rotary encoder EC11 PEC11R", pads=pads, graphics=g)


def mount_hole_m2():
    pads = [dict(num="", kind="np_thru_hole", shape="circle", lx=0, ly=0,
                 w=2.2, drill=(2.2, 2.2), layers=("*.Cu", "*.Mask"))]
    g = [("circle", (0, 0), ("r", 1.1), "F.SilkS", 0.15),
         ("circle", (0, 0), ("r", 2.2), "F.CrtYd", 0.05)]
    return dict(name="MountingHole_M2", attr="through_hole",
                descr="M2 mounting hole, 2.2 mm drill", tags="mounting hole",
                pads=pads, graphics=g)


def stabilizer_cherry_mx_2u():
    """Cherry MX PCB mount stabilizer, 2.00 u hole pattern.

    The same footprint serves 2.00 / 2.25 / 2.50 / 2.75 u keys: the holes sit
    11.938 mm left and right of the key centre regardless of the key width.
    Hole offsets and drills are copied from the keyswitch-kicad-library
    ``Mounting_Keyboard_Stabilizer.pretty/Stabilizer_Cherry_MX_2.00u``
    footprint (3.048 mm positioning hole behind the switch, 3.9878 mm
    mounting hole towards the front of the key), so a stock part fits.
    The housing outlines are drawn on F.Fab: on F.SilkS they would sit 0.06 mm
    from the neighbouring key's switch outline.
    """
    pads = []
    for sx in (-1, 1):
        for drill, dy in ((3.048, -6.985), (3.9878, 8.225)):
            pads.append(dict(num="", kind="np_thru_hole", shape="circle",
                            lx=sx * 11.938, ly=dy, w=drill, drill=(drill, drill),
                            layers=("*.Cu", "*.Mask")))
    g = []
    for sx in (-1, 1):
        x0 = 8.563 if sx > 0 else -15.313
        x1 = 15.313 if sx > 0 else -8.563
        for (a, b) in (((x0, -5.53), (x1, -5.53)), ((x1, -5.53), (x1, 6.77)),
                       ((x1, 6.77), (x0, 6.77)), ((x0, 6.77), (x0, -5.53))):
            g.append(("line", a, b, "F.Fab", 0.1))
    # stabilizer wire, drawn under the key cap
    g += [("line", (-11.938, -4.0), (11.938, -4.0), "F.Fab", 0.1)]
    return dict(name="Stabilizer_Cherry_MX_2.00u", attr="through_hole",
                descr="Cherry MX PCB mount stabilizer 2.00-2.75u (4 NPTH holes)",
                tags="stabilizer Cherry MX PCB mount",
                pads=pads, graphics=g)


FACTORY = {
    "choc": choc_hotswap,
    "stab": stabilizer_cherry_mx_2u,
    "diode": diode_sod123,
    "mcu": pro_micro_rp2040,
    "trrs": trrs_pj320a,
    "reset": reset_switch,
    "encoder": rotary_ec11,
    "mount": mount_hole_m2,
}
