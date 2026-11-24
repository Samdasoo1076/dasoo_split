"""Board model: footprints, matrix truss, tracks, zones, KiCad output."""
import math
import os
import random as _random

from . import parts
from .geom import U, ROW0_Y, ROW_PITCH, place
from .layout import CONFIG, keys, stab_holes, STAB_MIN_U

# --- matrix truss geometry (all values relative to a key centre) -----------
DIODE_DX = 6.75          # diode centre offset from the switch centre
DIODE_DY = 9.0           # diode centre below the switch centre
STUB_DX = 8.5            # switch pad 2 -> diode anode vertical stub
VIA_DX = -1.75           # cathode via offset from the diode centre
BRANCH_DY = -8.35        # column branch line, above the switch centre
TRUNK_DX = -7.5          # column trunk, left of the row-0 key centre
SIG_W = 0.25
PWR_W = 0.5
VIA_D = 0.6
VIA_DRILL = 0.3


_RNG = _random.Random(20260617)


def u():
    """Deterministic UUID so that regenerating gives byte identical files."""
    b = _RNG.getrandbits(128)
    h = "%032x" % b
    return "%s-%s-4%s-a%s-%s" % (h[0:8], h[8:12], h[13:16], h[17:20], h[20:32])


def num(v):
    if isinstance(v, str):
        return v
    s = "%.6f" % v
    s = s.rstrip("0").rstrip(".")
    if s in ("-0", ""):
        s = "0"
    return s


class Track:
    def __init__(self, a, b, width, layer, net):
        self.a, self.b, self.width, self.layer, self.net = a, b, width, layer, net


class Via:
    def __init__(self, x, y, net, dia=VIA_D, drill=VIA_DRILL):
        self.x, self.y, self.net, self.dia, self.drill = x, y, net, dia, drill


# A stabilizer hole is a keepout: the row bus steps this far around it (edge of
# the hole to the centre line of the track, so 0.375 mm of copper clearance for
# a 0.25 mm track and still 0.25 mm more than the 0.2 mm design clearance).
BUS_HOLE_CLEAR = 0.5


def bus_points(xs, y, holes, margin=BUS_HOLE_CLEAR):
    """Polyline that links the cathode vias of one matrix row on F.Cu.

    The bus runs straight at ``y`` except where a stabilizer hole of a wide key
    sits on that line.  There it detours *above* the hole: the strip between the
    switch body and the hole (y from about cy + 4 to cy + 6) is empty on F.Cu,
    while below the hole the next row's stabilizer holes and switch pads begin.
    The legs are 45 degrees when there is room, a square jog when there is not.
    """
    blocks = []
    for h in holes:
        r = h["d"] / 2.0 + margin
        L, R = h["x"] - r, h["x"] + r
        T, B = h["y"] - r, h["y"] + r
        if T < y < B and L < xs[-1] and R > xs[0]:
            blocks.append((L, R, T))
    blocks.sort()
    pts = [(xs[0], y)]
    cur = xs[0]
    for L, R, T in blocks:
        d = y - T
        if d > 0 and L - d > cur + 1e-9:
            pts += [(L, y), (L - d, T), (R + d, T), (R, y)]
        else:
            pts += [(L, y), (L, T), (R, T), (R, y)]
        cur = R
    pts.append((xs[-1], y))
    return pts


class Board:
    def __init__(self, hand):
        self.hand = hand
        self.cfg = CONFIG[hand]
        self.keys = keys(hand)
        self.fps = []
        self.tracks = []
        self.vias = []
        self.net_names = []
        self.net_id = {}
        self.warnings = []
        self._n_stab = 0

    # ------------------------------------------------------------------ nets
    def net(self, name):
        if name not in self.net_id:
            self.net_id[name] = len(self.net_names) + 1
            self.net_names.append(name)
        return self.net_id[name]

    # ------------------------------------------------------------ footprints
    def add(self, kind, ref, value, x, y, ang=0.0, side="F", **kw):
        if callable(parts.FACTORY[kind]):
            spec = parts.FACTORY[kind](**kw) if kw else parts.FACTORY[kind]()
        else:  # pragma: no cover
            spec = parts.FACTORY[kind](**kw)
        fp = parts.Footprint("choc60", spec["name"], ref, value, x, y, ang, side,
                             pads=[dict(p) for p in spec["pads"]],
                             graphics=spec["graphics"], attr=spec.get("attr"),
                             descr=spec.get("descr", ""), tags=spec.get("tags", ""))
        self.fps.append(fp)
        return fp

    def tracks_of(self, net):
        nid = self.net_id.get(net)
        return [t for t in self.tracks if self.net_id[t.net] == nid]

    def add_track(self, a, b, width, layer, net):
        if abs(a[0] - b[0]) < 1e-9 and abs(a[1] - b[1]) < 1e-9:
            return
        self.net(net)
        self.tracks.append(Track(a, b, width, layer, net))

    def add_via(self, x, y, net, dia=VIA_D, drill=VIA_DRILL):
        self.net(net)
        self.vias.append(Via(x, y, net, dia, drill))

    # -------------------------------------------------------------- assembly
    def build(self):
        cfg = self.cfg
        for k in self.keys:
            k["col_net"] = "COL%d" % k["col"]
            k["row_net"] = "ROW%d" % k["row"]
            self.net(k["col_net"])
            self.net(k["row_net"])
            self.net(k["knet"])
            if k["kind"] == "encoder":
                enc = self.add("encoder", k["ref"], "EC11 rotary encoder",
                               k["cx"], k["cy"], 0.0, "F")
                enc.pad("A").net = "ENC_A"
                enc.pad("B").net = "ENC_B"
                enc.pad("C").net = "GND"
                enc.pad("S1").net = k["col_net"]
                enc.pad("S2").net = k["knet"]
                for n in ("ENC_A", "ENC_B", "GND"):
                    self.net(n)
                k["sw"] = enc
                k["colpad"] = enc.pad("S1")
            else:
                k["sw"] = self.add("choc", k["ref"], "ChocV1 %.2fu" % k["wu"],
                                   k["cx"], k["cy"], 0.0, "F", width_u=k["wu"])
                k["sw"].pad("1").net = k["col_net"]
                k["sw"].pad("2").net = k["knet"]
                k["colpad"] = k["sw"].pad("1")
                if k["wu"] >= STAB_MIN_U - 1e-9:
                    # 2 u and wider: four NPTH holes for a Cherry MX PCB mount
                    # stabilizer, centred on the key like the switch
                    self._n_stab += 1
                    k["stab"] = self.add("stab", "ST%d" % self._n_stab,
                                         "Cherry MX PCB stabilizer 2u",
                                         k["cx"], k["cy"], 0.0, "F")
            k["diode"] = self.add("diode", k["dref"], "1N4148W",
                                  k["cx"] + DIODE_DX, k["cy"] + DIODE_DY,
                                  0.0, "B", kbar_right=True)
            k["diode"].pad("1").net = k["row_net"]
            k["diode"].pad("2").net = k["knet"]

        # MCU / TRRS / reset / mounts
        m = cfg["mcu"]
        self.mcu = self.add("mcu", "U1", "RP2040 Pro Micro", m["px"], m["py"], 0.0, "F",
                            mirror=m["mirror"])
        t = cfg["trrs"]
        self.trrs = self.add("trrs", "J1", "PJ-320A", t["px"], t["py"], t["ang"], "F")
        r = cfg["reset"]
        self.reset = self.add("reset", "SW_RST", "Reset", r["px"], r["py"], r["ang"], "F")
        self.mounts = []
        for i, (mx, my) in enumerate(cfg["mounts"], 1):
            self.mounts.append(self.add("mount", "H%d" % i, "M2", mx, my, 0.0, "F"))
        self.assign_mcu_nets()

    def assign_mcu_nets(self):
        row_pins = ["GP2", "GP3", "GP4", "GP5", "GP6"]
        col_pins = ["GP7", "GP8", "GP9", "GP20", "GP21", "GP22", "GP23", "GP26",
                    "GP27"]
        pin_net = {}
        for i, gp in enumerate(row_pins):
            pin_net[gp] = "ROW%d" % i
        used_cols = set(k["col"] for k in self.keys)
        for i, gp in enumerate(col_pins):
            if i in used_cols:
                pin_net[gp] = "COL%d" % i
        pin_net["GP0"] = "TX"
        pin_net["GP1"] = "RX"
        if self.hand == "left":        # the encoder only exists on the left
            pin_net["GP28"] = "ENC_A"
            pin_net["GP29"] = "ENC_B"
        pin_net["VCC"] = "VCC"
        pin_net["GND"] = "GND"
        pin_net["RST"] = "RST"
        for p in self.mcu.pads:
            if p.name in pin_net:
                p.net = pin_net[p.name]
                self.net(p.net)
        left = self.hand == "left"
        trrs = {"SLEEVE": "RX" if left else "TX",
                "TIP": "VCC",
                "RING1": "GND",
                "RING2": "TX" if left else "RX"}
        for p in self.trrs.pads:
            if p.name in trrs:
                p.net = trrs[p.name]
                self.net(p.net)
        # reset switch: left pair = RST, right pair = GND
        for p in self.reset.pads:
            p.net = "RST" if float(p.lx) < 0 else "GND"
            self.net(p.net)

    # -------------------------------------------------------------- the truss
    def build_truss(self):
        """Place the diode of every key and the horizontal row buses.

        Every key gets a short back-layer stub from switch pad 2 to the diode
        anode, and the diode cathode drops a via onto the row bus.  The buses
        are horizontal lines on F.Cu (rows), the column nets are routed
        vertically on B.Cu afterwards.
        """
        for k in self.keys:
            cx, cy = k["cx"], k["cy"]
            if k["kind"] == "encoder":
                # the switch terminals point down; hook S2 to the diode anode
                # with a short 90 degree jog that stays clear of the cathode pad
                yk = cy + 7.0
                self.add_track((cx + 2.5, yk), (cx + 8.5, yk), SIG_W, "B.Cu", k["knet"])
                self.add_track((cx + 8.5, yk), (cx + 8.5, cy + DIODE_DY), SIG_W, "B.Cu", k["knet"])
            else:
                self.add_track((cx + STUB_DX, cy - 3.8),
                               (cx + STUB_DX, cy + DIODE_DY), SIG_W, "B.Cu", k["knet"])
            vx, vy = cx + DIODE_DX + VIA_DX, cy + DIODE_DY
            self.add_via(vx, vy, k["row_net"])
        rows = {}
        for k in self.keys:
            rows.setdefault(k["row"], []).append(k)
        self.row_bus = {}
        holes = stab_holes(self.hand)
        for r, ks in sorted(rows.items()):
            ys = ks[0]["cy"] + DIODE_DY
            xs = sorted(k["cx"] + DIODE_DX + VIA_DX for k in ks)
            pts = bus_points(xs, ys, holes)
            for a, b in zip(pts, pts[1:]):
                self.add_track(a, b, SIG_W, "F.Cu", "ROW%d" % r)
            self.row_bus[r] = (min(xs), max(xs), ys)
        self.col_keys = {}
        for k in self.keys:
            self.col_keys.setdefault(k["col"], []).append(k)

    # ----------------------------------------------------------------- output
    def all_pads(self):
        for fp in self.fps:
            for p in fp.pads:
                yield p

    def pcb_text(self, title):
        out = []
        a = out.append
        a("(kicad_pcb")
        a("\t(version 20241229)")
        a('\t(generator "pcbnew")')
        a('\t(generator_version "9.0")')
        a("\t(general")
        a("\t\t(thickness 1.6)")
        a("\t\t(legacy_teardrops no)")
        a("\t)")
        a('\t(paper "A3")')
        a("\t(layers")
        for n, name, kind in [(0, "F.Cu", "signal"), (2, "B.Cu", "signal"),
                              (9, "F.Adhes", "user"), (11, "B.Adhes", "user"),
                              (13, "F.Paste", "user"), (15, "B.Paste", "user"),
                              (5, "F.SilkS", "user"), (7, "B.SilkS", "user"),
                              (1, "F.Mask", "user"), (3, "B.Mask", "user"),
                              (17, "Dwgs.User", "user"), (19, "Cmts.User", "user"),
                              (21, "Eco1.User", "user"), (23, "Eco2.User", "user"),
                              (25, "Edge.Cuts", "user"), (27, "Margin", "user"),
                              (31, "F.CrtYd", "user"), (29, "B.CrtYd", "user"),
                              (35, "F.Fab", "user"), (33, "B.Fab", "user")]:
            a('\t\t(%d "%s" %s)' % (n, name, kind))
        a("\t)")
        a("\t(setup")
        a("\t\t(pad_to_mask_clearance 0)")
        a("\t\t(allow_soldermask_bridges_in_footprints no)")
        a("\t\t(tenting front back)")
        a("\t\t(pcbplotparams")
        a("\t\t\t(layerselection 0x00010fc_ffffffff)")
        a("\t\t\t(plot_on_all_layers_selection 0x0000000_00000000)")
        a("\t\t\t(disableapertmacros no)")
        a("\t\t\t(usegerberextensions yes)")
        a("\t\t\t(usegerberattributes yes)")
        a("\t\t\t(usegerberadvancedattributes yes)")
        a("\t\t\t(creategerberjobfile yes)")
        a("\t\t\t(dashed_line_dash_ratio 12.000000)")
        a("\t\t\t(dashed_line_gap_ratio 3.000000)")
        a("\t\t\t(svgprecision 4)")
        a("\t\t\t(plotframeref no)")
        a("\t\t\t(mode 1)")
        a("\t\t\t(useauxorigin no)")
        a("\t\t\t(hpglpennumber 1)")
        a("\t\t\t(hpglpenspeed 20)")
        a("\t\t\t(hpglpendiameter 15.000000)")
        a("\t\t\t(pdf_front_fp_property_popups yes)")
        a("\t\t\t(pdf_back_fp_property_popups yes)")
        a("\t\t\t(pdf_metadata yes)")
        a("\t\t\t(pdf_single_document no)")
        a("\t\t\t(dxfpolygonmode yes)")
        a("\t\t\t(dxfimperialunits yes)")
        a("\t\t\t(dxfusepcbnewfont yes)")
        a("\t\t\t(psnegative no)")
        a("\t\t\t(psa4output no)")
        a("\t\t\t(plot_black_and_white yes)")
        a("\t\t\t(sketchpadsonfab no)")
        a("\t\t\t(plotpadnumbers no)")
        a("\t\t\t(hidednponfab no)")
        a("\t\t\t(sketchdnponfab yes)")
        a("\t\t\t(crossoutdnponfab yes)")
        a("\t\t\t(subtractmaskfromsilk no)")
        a("\t\t\t(outputformat 1)")
        a("\t\t\t(mirror no)")
        a("\t\t\t(drillshape 1)")
        a("\t\t\t(scaleselection 1)")
        a("\t\t\t(outputdirectory \"\")")
        a("\t\t)")
        a("\t)")
        a('\t(net 0 "")')
        for i, name in enumerate(self.net_names, 1):
            a('\t(net %d "%s")' % (i, name))
        for fp in self.fps:
            out.extend(self._fp_text(fp))
        # edge cuts
        x0, y0, x1, y1 = self.cfg["outline"]
        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        for i in range(4):
            s = corners[i]
            e = corners[(i + 1) % 4]
            a("\t(gr_line")
            a("\t\t(start %s %s)" % (num(s[0]), num(s[1])))
            a("\t\t(end %s %s)" % (num(e[0]), num(e[1])))
            a("\t\t(stroke (width 0.1) (type default))")
            a('\t\t(layer "Edge.Cuts")')
            a('\t\t(uuid "%s")' % u())
            a("\t)")
        a("\t(gr_text \"choc-split-60 %s\"" % self.hand)
        a("\t\t(at %s %s 0)" % (num((x0 + x1) / 2), num(y1 - 4)))
        a('\t\t(layer "F.SilkS")')
        a('\t\t(uuid "%s")' % u())
        a("\t\t(effects (font (size 2 2) (thickness 0.3)))")
        a("\t)")
        for tr in self.tracks:
            a("\t(segment")
            a("\t\t(start %s %s)" % (num(tr.a[0]), num(tr.a[1])))
            a("\t\t(end %s %s)" % (num(tr.b[0]), num(tr.b[1])))
            a("\t\t(width %s)" % num(tr.width))
            a('\t\t(layer "%s")' % tr.layer)
            a("\t\t(net %d)" % self.net_id[tr.net])
            a('\t\t(uuid "%s")' % u())
            a("\t)")
        for v in self.vias:
            a("\t(via")
            a("\t\t(at %s %s)" % (num(v.x), num(v.y)))
            a("\t\t(size %s)" % num(v.dia))
            a("\t\t(drill %s)" % num(v.drill))
            a('\t\t(layers "F.Cu" "B.Cu")')
            a("\t\t(net %d)" % self.net_id[v.net])
            a('\t\t(uuid "%s")' % u())
            a("\t)")
        for layer in ("F.Cu", "B.Cu"):
            a("\t(zone")
            a("\t\t(net %d)" % self.net_id["GND"])
            a('\t\t(net_name "GND")')
            a('\t\t(layer "%s")' % layer)
            a('\t\t(uuid "%s")' % u())
            a("\t\t(hatch edge 0.5)")
            a("\t\t(connect_pads")
            a("\t\t\t(clearance 0.4)")
            a("\t\t)")
            a("\t\t(min_thickness 0.25)")
            a("\t\t(filled_areas_thickness no)")
            a("\t\t(fill yes")
            a("\t\t\t(thermal_gap 0.3)")
            a("\t\t\t(thermal_bridge_width 0.3)")
            a("\t\t)")
            a("\t\t(polygon")
            a("\t\t\t(pts")
            a("\t\t\t\t(xy %s %s) (xy %s %s) (xy %s %s) (xy %s %s)"
              % (num(x0 + 0.5), num(y0 + 0.5), num(x1 - 0.5), num(y0 + 0.5),
                 num(x1 - 0.5), num(y1 - 0.5), num(x0 + 0.5), num(y1 - 0.5)))
            a("\t\t\t)")
            a("\t\t)")
            a("\t)")
        a("\t(embedded_fonts no)")
        a(")")
        return "\n".join(out) + "\n"

    # ---------------------------------------------------------- footprint out
    def _fp_text(self, fp):
        o = []
        a = o.append
        a('\t(footprint "choc60:%s"' % fp.name)
        a('\t\t(layer "%s")' % ("F.Cu" if fp.side == "F" else "B.Cu"))
        a('\t\t(uuid "%s")' % u())
        if abs(fp.ang) > 1e-9:
            a("\t\t(at %s %s %s)" % (num(fp.px), num(fp.py), num(fp.ang)))
        else:
            a("\t\t(at %s %s)" % (num(fp.px), num(fp.py)))
        a('\t\t(descr "%s")' % fp.descr)
        a('\t\t(tags "%s")' % fp.tags)
        silk = "F.SilkS" if fp.side == "F" else "B.SilkS"
        fab = "F.Fab" if fp.side == "F" else "B.Fab"
        just = "" if fp.side == "F" else " (justify mirror)"
        a('\t\t(property "Reference" "%s"' % fp.ref)
        a("\t\t\t(at 0 -10.2 0)")
        a('\t\t\t(layer "%s")' % silk)
        a('\t\t\t(uuid "%s")' % u())
        a("\t\t\t(effects (font (size 1 1) (thickness 0.15))%s)" % just)
        a("\t\t)")
        a('\t\t(property "Value" "%s"' % fp.value.replace('"', "'"))
        a("\t\t\t(at 0 10.2 0)")
        a('\t\t\t(layer "%s")' % fab)
        a('\t\t\t(uuid "%s")' % u())
        a("\t\t\t(effects (font (size 1 1) (thickness 0.15))%s)" % just)
        a("\t\t)")
        a('\t\t(property "Footprint" "choc60:%s"' % fp.name)
        a("\t\t\t(at 0 0 0)")
        a('\t\t\t(layer "%s")' % fab)
        a("\t\t\t(hide yes)")
        a('\t\t\t(uuid "%s")' % u())
        a("\t\t\t(effects (font (size 1.27 1.27))%s)" % just)
        a("\t\t)")
        a('\t\t(property "Datasheet" ""')
        a("\t\t\t(at 0 0 0)")
        a('\t\t\t(layer "%s")' % fab)
        a("\t\t\t(hide yes)")
        a('\t\t\t(uuid "%s")' % u())
        a("\t\t\t(effects (font (size 1.27 1.27))%s)" % just)
        a("\t\t)")
        if fp.attr:
            a("\t\t(attr %s)" % fp.attr)
        for g in fp.graphics:
            o.extend(self._graphic(g, fp))
        for p in fp.pads:
            o.extend(self._pad_text(p, fp))
        a("\t\t(embedded_fonts no)")
        a("\t)")
        return o

    def _graphic(self, g, fp):
        layer = g[3]
        if fp.side == "B":
            layer = parts.BACK_MAP.get(layer, layer)
        o = []
        if g[0] == "line":
            (x1, y1), (x2, y2) = g[1], g[2]
            o.append("\t\t(fp_line")
            o.append("\t\t\t(start %s %s)" % (num(x1), num(y1)))
            o.append("\t\t\t(end %s %s)" % (num(x2), num(y2)))
            o.append("\t\t\t(stroke (width %s) (type solid))" % num(g[4]))
            o.append('\t\t\t(layer "%s")' % layer)
            o.append('\t\t\t(uuid "%s")' % u())
            o.append("\t\t)")
        elif g[0] == "circle":
            (cx, cy), r = g[1], g[2][1]
            o.append("\t\t(fp_circle")
            o.append("\t\t\t(center %s %s)" % (num(cx), num(cy)))
            o.append("\t\t\t(end %s %s)" % (num(cx + r), num(cy)))
            o.append("\t\t\t(stroke (width %s) (type solid))" % num(g[4]))
            o.append('\t\t\t(fill no)')
            o.append('\t\t\t(layer "%s")' % layer)
            o.append('\t\t\t(uuid "%s")' % u())
            o.append("\t\t)")
        return o

    def _pad_text(self, p, fp):
        o = []
        layers = " ".join('"%s"' % l for l in fp_pad_layers(p))
        name = p.num if p.num != "" else ""
        head = '\t\t(pad "%s" %s %s' % (name, p.kind, p.shape)
        o.append(head)
        if abs(p.lang) > 1e-9:
            o.append("\t\t\t(at %s %s %s)" % (num(p.lx), num(p.ly), num(p.lang)))
        else:
            o.append("\t\t\t(at %s %s)" % (num(p.lx), num(p.ly)))
        o.append("\t\t\t(size %s %s)" % (num(p.w), num(p.h)))
        if p.kind != "smd":
            if abs(p.drill[0] - p.drill[1]) < 1e-9:
                o.append("\t\t\t(drill %s)" % num(p.drill[0]))
            else:
                o.append("\t\t\t(drill oval %s %s)" % (num(p.drill[0]), num(p.drill[1])))
        o.append("\t\t\t(layers %s)" % layers)
        if p.shape == "roundrect":
            o.append("\t\t\t(roundrect_rratio %s)" % num(p.rratio))
        if p.net:
            o.append('\t\t\t(net %d "%s")' % (self.net_id[p.net], p.net))
        if p.num != "":
            o.append('\t\t\t(pinfunction "%s")' % (p.name or p.num))
            o.append('\t\t\t(pintype "passive")')
        o.append('\t\t\t(uuid "%s")' % u())
        o.append("\t\t)")
        return o


def fp_pad_layers(p):
    return p.glayers
