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
            # a back side footprint keeps its local frame (no mirror), so the
            # pad's own rotation is simply added to the placement angle
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
    """Kailh Choc v2 (CPG1353) hot swap footprint.

    The contacts are the ones of the Choc hot swap socket CPG135001S30, and
    Kailh's own v2 drawing (CPG135301D01) puts the two switch pins at exactly
    the Choc v1 positions, so the two 2.55 x 2.5 mm socket pads and the two
    3.05 mm socket legs keep the coordinates of the proven v1 footprint.  What
    is v2 only:

      * the centre hole clears the Ø5.00 v2 mounting post (v1 is Ø3.40),
      * v1's two Ø1.90 side pegs at x = +-5.5 are gone (a v1 switch no longer
        fits this board),
      * v2 has one Ø1.60 guide post at Kailh's (-5.15, -5.00), which in this
        footprint's frame is (-5.00, +5.15) -- the same rotation that maps
        Kailh's pin coordinates onto the socket legs.  The hole is a
        1.8 x 2.2 mm slot (long axis along Y) so that the post enters even when
        it is the 2 x 1.5 mm rectangular post drawn in `Kailh_PG1353_Hotswap`
        (ai03, 1.5 x 2 oval) and so that switch swaps are not a press fit.
    """
    key_w = width_u * U
    pads = [
        dict(num="1", kind="smd", shape="roundrect", lx=-3.5, ly=-6.0,
             w=2.55, h=2.5, layers=("B.Cu", "B.Mask", "B.Paste"), rratio=0.1),
        dict(num="2", kind="smd", shape="roundrect", lx=8.5, ly=-3.8,
             w=2.55, h=2.5, layers=("B.Cu", "B.Mask", "B.Paste"), rratio=0.1),
        dict(num="", kind="np_thru_hole", shape="circle", lx=0, ly=-5.9, w=3.05,
             drill=(3.05, 3.05), layers=("*.Cu", "*.Mask")),
        dict(num="", kind="np_thru_hole", shape="circle", lx=5, ly=-3.8, w=3.05,
             drill=(3.05, 3.05), layers=("*.Cu", "*.Mask")),
        dict(num="", kind="np_thru_hole", shape="circle", lx=0, ly=0, w=5.05,
             drill=(5.05, 5.05), layers=("*.Cu", "*.Mask")),
        dict(num="", kind="np_thru_hole", shape="oval", lx=-5, ly=5.15,
             w=1.8, h=2.2, drill=(1.8, 2.2), layers=("*.Cu", "*.Mask")),
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
        name="SW_Hotswap_Kailh_Choc_V2_%s" % ("%.2fu" % width_u),
        attr="smd",
        descr="Kailh Choc v2 (CPG1353) hot swap socket, %.2fu key" % width_u,
        tags="kailh choc v2 hotswap low profile",
        pads=pads, graphics=g)


def diode_sod123(kbar_right=False):
    """SOD-123 diode.  ``kbar_right`` puts the cathode pad (pad 1) and the
    silkscreen band on the right of the footprint origin.

    The footprint sits on the back side and KiCad keeps a back side
    footprint's stored coordinates unmirrored, so pad 1 lands where it is
    written: ``kbar_right=False`` means cathode-left on the board.  The row net
    follows the cathode, so the generator picks the flag from the placement and
    the router reads the placed pad back instead of guessing a sign (see
    Board.build_truss).
    """
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
          # the connector outline outside the courtyard is silk: a lone
          # segment on F.CrtYd makes KiCad report U1's courtyard as malformed
          ("line", (usb_x - 3.0, -4.0), (usb_x - 3.0, 4.0), "F.SilkS", 0.1)]
    # pin 1 marker
    p1 = pads[0]
    g += [("circle", (p1["lx"] + 0.0, -5.4), ("r", 0.35), "F.SilkS", 0.12)]
    return dict(name="ProMicro_RP2040", attr="through_hole",
                descr="RP2040 Pro Micro compatible controller (Pro Micro pinout)",
                tags="RP2040 Pro Micro Elite-Pi", pads=pads, graphics=g)


def usb_c_receptacle():
    """USB 2.0 Type-C receptacle, 16 pin (HRO TYPE-C-31-M-12 geometry).

    Pad geometry copied from KiCad's
    ``Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12``: 16 SMT pins on
    0.5 mm pitch at y = -4.045 (the A/B pairs of the four shell-side power pins
    share one physical pad each, exactly as on the part, so the plug works in
    either orientation), four shell legs, 8.94 x 7.30 mm body, mating face
    towards -Y.

    One deliberate deviation: the two Ø0.65 locating peg holes at
    (+-2.89, -2.60) are left out.  They sit directly behind the VBUS pads
    (+-2.45) and leave only 0.665 mm to the next pad, which is narrower than
    the 0.2 mm clearance + 0.3 mm hole clearance + 0.25 mm track the two VBUS
    pads need to get out on a two layer board.  Cut the two plastic locating
    pegs flush before soldering; the four shell legs still hold the part and
    the 16 pads carry the signal.
    """
    smd = ("F.Cu", "F.Mask", "F.Paste")
    pads = []
    for lx, num, w in ((-3.25, "A1", 0.6), (-3.25, "B12", 0.6),
                       (-2.45, "A4", 0.6), (-2.45, "B9", 0.6),
                       (-1.75, "B8", 0.3), (-1.25, "A5", 0.3),
                       (-0.75, "B7", 0.3), (-0.25, "A6", 0.3),
                       (0.25, "A7", 0.3), (0.75, "B6", 0.3),
                       (1.25, "A8", 0.3), (1.75, "B5", 0.3),
                       (2.45, "A9", 0.6), (2.45, "B4", 0.6),
                       (3.25, "A12", 0.6), (3.25, "B1", 0.6)):
        pads.append(dict(num=num, kind="smd", shape="rect", lx=lx, ly=-4.045,
                         w=w, h=1.45, layers=smd, name=num))
    for sx in (-1, 1):
        pads.append(dict(num="S1", kind="thru_hole", shape="oval",
                         lx=sx * 4.32, ly=1.05, w=1.0, h=1.6, drill=(0.6, 1.2),
                         layers=("*.Cu", "*.Mask"), name="SHIELD"))
        pads.append(dict(num="S1", kind="thru_hole", shape="oval",
                         lx=sx * 4.32, ly=-3.13, w=1.0, h=2.1, drill=(0.6, 1.7),
                         layers=("*.Cu", "*.Mask"), name="SHIELD"))
    g = [("line", (-4.7, 2.0), (-4.7, 3.9), "F.SilkS", 0.12),
         ("line", (-4.7, -1.9), (-4.7, 0.1), "F.SilkS", 0.12),
         ("line", (4.7, 2.0), (4.7, 3.9), "F.SilkS", 0.12),
         ("line", (4.7, -1.9), (4.7, 0.1), "F.SilkS", 0.12),
         ("line", (-4.7, 3.9), (4.7, 3.9), "F.SilkS", 0.12),
         # the mouth: two short ticks either side of the plug opening
         ("line", (-4.7, -1.9), (-3.5, -1.9), "F.SilkS", 0.12),
         ("line", (4.7, -1.9), (3.5, -1.9), "F.SilkS", 0.12),
         # body and courtyard move with the part, so keep them on the fab side
         ("line", (-4.47, -3.65), (4.47, -3.65), "F.Fab", 0.1),
         ("line", (4.47, -3.65), (4.47, 3.65), "F.Fab", 0.1),
         ("line", (4.47, 3.65), (-4.47, 3.65), "F.Fab", 0.1),
         ("line", (-4.47, 3.65), (-4.47, -3.65), "F.Fab", 0.1),
         ("line", (-5.32, -5.27), (5.32, -5.27), "F.CrtYd", 0.05),
         ("line", (5.32, -5.27), (5.32, 4.15), "F.CrtYd", 0.05),
         ("line", (5.32, 4.15), (-5.32, 4.15), "F.CrtYd", 0.05),
         ("line", (-5.32, 4.15), (-5.32, -5.27), "F.CrtYd", 0.05)]
    return dict(name="USB_C_Receptacle_HRO_TYPE-C-31-M-12", attr="smd",
                descr="USB 2.0 Type-C receptacle, 16 pin, HRO TYPE-C-31-M-12 "
                      "(locating peg holes omitted)",
                tags="USB Type-C receptacle 16P USB2.0",
                pads=pads, graphics=g, ref_at=(0.0, 6.3), val_at=(0.0, 7.6))


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


def stabilizer_choc_v2_2u():
    """Kailh Choc v2 PCB mount stabilizer, 2.00 u pattern.

    Geometry copied from Salicylic-acid3's
    ``kbd_Stabilizer.pretty/Choc_v2_PCBMountStab_2u`` (the Keeb-On! screw in
    Choc v2 stabilizer), which is measured from the real part and validated on
    1.6 mm boards:

      * four oval NPTH clip holes, at x = +-11.9:  3.2 x 3.4 mm at y = -6.2 and
        3.0 x 4.0 mm at y = +8.24,
      * two rectangular board cutouts on Edge.Cuts, x = 8.9 .. 14.9 (mirrored),
        y = -3.75 .. +3.75, where the stabilizer housing hangs through the PCB.

    The same footprint serves 2.00 / 2.25 / 2.50 / 2.75 u keys.  It does *not*
    accept Cherry MX stabilizers and vice versa, and the housing needs the two
    cutouts, so the switch of such a key has to be turned 90 degrees (Salicylic
    recommends exactly that: with the switch in line the socket collides with
    the protrusion on the back of the stabilizer).
    """
    pads = []
    for sx in (-1, 1):
        pads.append(dict(num="", kind="np_thru_hole", shape="oval",
                         lx=sx * 11.9, ly=-6.2, w=3.2, h=3.4, drill=(3.2, 3.4),
                         layers=("*.Cu", "*.Mask")))
        pads.append(dict(num="", kind="np_thru_hole", shape="oval",
                         lx=sx * 11.9, ly=8.24, w=3.0, h=4.0, drill=(3.0, 4.0),
                         layers=("*.Cu", "*.Mask")))
    g = []
    # board cutout where the stabilizer housing sits below the PCB
    for sx in (-1, 1):
        x0, x1 = (8.9, 14.9) if sx > 0 else (-14.9, -8.9)
        g += [("line", (x0, -3.75), (x1, -3.75), "Edge.Cuts", 0.05),
              ("line", (x1, -3.75), (x1, 3.75), "Edge.Cuts", 0.05),
              ("line", (x1, 3.75), (x0, 3.75), "Edge.Cuts", 0.05),
              ("line", (x0, 3.75), (x0, -3.75), "Edge.Cuts", 0.05)]
    # housing outline and the four body corners of the 2 u key, on F.Fab
    g += [("line", (-19.05, -9.525), (19.05, -9.525), "F.Fab", 0.15),
          ("line", (19.05, -9.525), (19.05, 9.525), "F.Fab", 0.15),
          ("line", (19.05, 9.525), (-19.05, 9.525), "F.Fab", 0.15),
          ("line", (-19.05, 9.525), (-19.05, -9.525), "F.Fab", 0.15)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            g += [("line", (sx * 7.0, sy * 7.0), (sx * 6.0, sy * 7.0), "F.Fab", 0.15),
                  ("line", (sx * 7.0, sy * 7.0), (sx * 7.0, sy * 6.0), "F.Fab", 0.15)]
    # stabilizer wire, under the key cap
    g += [("line", (-8.0, 8.24), (8.0, 8.24), "F.SilkS", 0.12)]
    return dict(name="Stabilizer_Choc_V2_PCBMount_2u", attr="through_hole",
                descr="Kailh Choc v2 PCB mount stabilizer 2.00-2.75u "
                      "(4 oval NPTH holes + 2 Edge.Cuts cutouts)",
                tags="stabilizer Choc v2 PCB mount",
                pads=pads, graphics=g)


FACTORY = {
    "choc": choc_hotswap,
    "stab": stabilizer_choc_v2_2u,
    "diode": diode_sod123,
    "mcu": pro_micro_rp2040,
    "usbc": usb_c_receptacle,
    "reset": reset_switch,
    "encoder": rotary_ec11,
    "mount": mount_hole_m2,
}
