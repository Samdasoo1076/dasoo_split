"""Physical key layout for both halves of the choc-split-60.

Every entry is ``(label, x in units, width in units, matrix column[, kind])``
where ``kind`` defaults to ``"switch"``.  The x is the left edge of the key in
key units (19.05 mm); matrix row is the row index in the table.

2026-11 revision
  * the two Th1/Th2 thumb keys under each space bar are gone
  * the left half gained a 5 key macro column, 0.25 u (4.7625 mm) to the left
    of the `` column: rotary encoder, Home, End, Page Up, Page Down
  * the right half gained a proper arrow cluster (up above down)
  * the right half now carries the real ANSI row stagger.  Splitting a full
    ANSI board between ``6`` and ``7`` puts the right half's key columns at
    7.0 / 6.5 / 6.75 / 7.25 u on the four letter rows, so once the right half
    is rebased on its own left edge the row starts are 0.5 / 0.0 / 0.25 /
    0.75 u -- exactly the 0 / 0.5 / 0.75 / 1.25 u stagger of the left half
    minus the 0.5 u the number row already sits right of the tab row.
  * the right half gains a ``B`` of its own at -0.25 u (the left half keeps
    its ``B``), RShift shrinks to 1 u, RFn is gone (0.25 u gap before Left)
    and the cell that frees at the end of the arrow row is a 1 u Delete.

2026-11 third revision (user request):
  * the left half's top left key is ``Esc`` now (it used to be `` ` ``)
  * the right half's number row gains a 1 u `` ` `` left of ``BSpc``, so the
    2 u backspace is split into `` ` `` + 1 u ``BSpc`` and the row still ends
    at 8.5 u
  * the right half's bottom two rows move 0.25 u left (row 3 starts at
    -0.5 u, row 4 at 0.5 u), so ``Del`` and ``Right`` end at 8.5 u as well:
    all five rows now stop on one straight vertical line, and
    ``Left/Down/Right`` sit exactly under ``RShift/Up/Del``

2026-11 fourth revision (user request):
  * the 2 u backspace comes back: instead of splitting ``BSpc`` into
    `` ` `` + 1 u, the right number row moves 1.0 u left (row 0 now starts at
    -0.5 u) and carries `7 8 9 0 - =` + 1 u `` ` `` + a full 2 u ``BSpc``,
    still ending on 8.5 u
  * the right bottom row moves another 0.25 u left (row 4 starts at 0.25 u),
    so ``RCtrl`` (3.75 - 5.0 u) leaves exactly 0.5 u of empty PCB before
    ``Left`` (5.5 u)
  * the left bottom row's ``Space`` moves 0.5 u right (4.25 - 6.25 u) to give
    the same 0.5 u of PCB between ``LAlt`` and the space bar
  * every key of 2 u and wider gets the Kailh Choc v2 PCB mount stabilizer
    (4 oval clip holes + two board cutouts, 2.00 u pattern, see
    :func:`stab_holes` / :func:`stab_cutouts`) and is turned 90 degrees, because
    the hot swap socket would otherwise run into the stabilizer cutout (and the
    protrusion on the back of the stabilizer)
"""
from .geom import U, ROW0_Y, ROW_PITCH

# x of the left macro column: its right edge sits 0.25 u left of the main
# column (which starts at x = 0).
MACRO_X = -1.25

LEFT_ROWS = [
    [("ENC", MACRO_X, 1, 7, "encoder"),
     ("Esc", 0, 1, 0), ("1", 1, 1, 1), ("2", 2, 1, 2), ("3", 3, 1, 3),
     ("4", 4, 1, 4), ("5", 5, 1, 5), ("6", 6, 1, 6)],
    [("Home", MACRO_X, 1, 7),
     ("Tab", 0, 1.5, 0), ("Q", 1.5, 1, 1), ("W", 2.5, 1, 2), ("E", 3.5, 1, 3),
     ("R", 4.5, 1, 4), ("T", 5.5, 1, 5)],
    [("End", MACRO_X, 1, 7),
     ("Caps", 0, 1.75, 0), ("A", 1.75, 1, 1), ("S", 2.75, 1, 2), ("D", 3.75, 1, 3),
     ("F", 4.75, 1, 4), ("G", 5.75, 1, 5)],
    [("PgUp", MACRO_X, 1, 7),
     ("LShift", 0, 2.25, 0), ("Z", 2.25, 1, 1), ("X", 3.25, 1, 2), ("C", 4.25, 1, 3),
     ("V", 5.25, 1, 4), ("B", 6.25, 1, 5)],
    # bottom: LCtrl 1.25 + LWin 1.25 + LAlt 1.25 end at 3.75 u, then 0.5 u of
    # empty PCB, then the 2 u space bar at 4.25 - 6.25 u (0.5 u further right
    # than before; ``B`` above ends at 7.25 u, so the board outline is
    # unchanged and the space bar still sits well inside it).
    [("PgDn", MACRO_X, 1, 7),
     ("LCtrl", 0, 1.25, 0), ("LWin", 1.25, 1.25, 1), ("LAlt", 2.5, 1.25, 2),
     ("Space", 4.25, 2.0, 3)],
]

# Right half.  Every row starts at its own x so that the finished board keeps
# the ANSI stagger; every row ends at 8.5 u, so the right edge is one straight
# line from the number row down to the space bar.  Row 0 (numbers) sits 0.5 u
# right of the tab row, row 2 (home) 0.25 u.  Row 3 starts at -0.5 u: the split
# of a full ANSI board puts this row's ``B`` 0.5 u left of ``N`` (and its ``N``
# level with ``Y``), which keeps the 2.5 u stagger the left half's bottom row
# has against its ``Tab`` row.
#
# 2026-11 second revision (user request):
#   * ``B`` added here, left of ``N`` (the left half keeps its ``B`` too)
#   * RShift is 1.0 u (was 1.75 u) and sits directly left of ``Up``
#   * no RFn key: 0.25 u of empty PCB between RCtrl and Left
#   * the space freed at the right of the arrow cluster is a 1 u ``Del``
#   * the row therefore needs a ninth matrix column (COL8)
#
# 2026-11 third revision (user request):
#   * 1 u `` ` `` on the right of ``=``, the 2 u backspace becomes 1 u
#   * rows 3 and 4 move 0.25 u left, so ``Del`` / ``Right`` end at 8.5 u too
#     and the arrows land under ``RShift`` / ``Up`` / ``Del``
#
# 2026-11 fourth revision (user request):
#   * the 2 u backspace is back: row 0 moves 1.0 u left (start -0.5 u) and
#     carries `7 8 9 0 - =` + 1 u `` ` `` + 2 u ``BSpc``, so the row still ends
#     at 8.5 u and ``7`` sits right after the left half's ``6`` (which is why
#     this row is 1 u left of the ANSI position the letter rows keep)
#   * row 4 moves 0.25 u left again (start 0.25 u): ``RCtrl`` ends at 5.0 u
#     and exactly 0.5 u of empty PCB separates it from ``Left`` at 5.5 u
RIGHT_ROWS = [
    # -0.5 u start: 7 8 9 0 - = ` (1 u each) + BSpc 2 u -> right edge 8.5 u.
    # The row sits 1.0 u further left than the tab row so that backspace keeps
    # its full 2 u width instead of being split into ` + 1 u.
    [("7", -0.5, 1, 0), ("8", 0.5, 1, 1), ("9", 1.5, 1, 2), ("0", 2.5, 1, 3),
     ("-", 3.5, 1, 4), ("=", 4.5, 1, 5), ("`", 5.5, 1, 6), ("BSpc", 6.5, 2.0, 7)],
    # 0.0 u start, \\ 1.5 u (same width as the left half's Tab) -> 8.5 u
    [("Y", 0, 1, 0), ("U", 1, 1, 1), ("I", 2, 1, 2), ("O", 3, 1, 3),
     ("P", 4, 1, 4), ("[", 5, 1, 5), ("]", 6, 1, 6), ("\\", 7, 1.5, 7)],
    # 0.25 u start, Enter 2.25 u -> 8.5 u
    [("H", 0.25, 1, 0), ("J", 1.25, 1, 1), ("K", 2.25, 1, 2), ("L", 3.25, 1, 3),
     (";", 4.25, 1, 4), ("'", 5.25, 1, 5), ("Enter", 6.25, 2.25, 6)],
    # -0.5 u start: B | N M , . / | RShift 1 u | Up | Del -> 8.5 u
    [("B", -0.5, 1, 0), ("N", 0.5, 1, 1), ("M", 1.5, 1, 2),
     (",", 2.5, 1, 3), (".", 3.5, 1, 4), ("/", 4.5, 1, 5),
     ("RShift", 5.5, 1.0, 6), ("Up", 6.5, 1, 7), ("Del", 7.5, 1, 8)],
    # bottom: 0.25 + 2.25 + 1.25 * 2 = exactly 5.0 u, then a 0.5 u gap, then
    # Left / Down / Right under RShift / Up / Del, so every row ends at 8.5 u.
    [("Space", 0.25, 2.25, 0), ("RAlt", 2.5, 1.25, 1), ("RCtrl", 3.75, 1.25, 2),
     ("Left", 5.5, 1, 6), ("Down", 6.5, 1, 7), ("Right", 7.5, 1, 8)],
]

ROWS = {"left": LEFT_ROWS, "right": RIGHT_ROWS}

# Board outline (x0, y0, x1, y1) and the hardware bay contents, per half.
CONFIG = {
    "left": dict(
        outline=(-26.0, -27.0, 150.0, 103.0),
        mcu=dict(px=7.0, py=-11.0, mirror=False),
        # USB-C link port on the inner end of the top edge (cable from above).
        # The HRO TYPE-C-31-M-12 has its mouth on the +Y side of the footprint
        # (the 16 pins are at the back, -Y), so the part is placed 180 degrees
        # turned: the mouth faces the top board edge.  The recommended layout
        # puts the board edge 5.79 mm in front of the locating-peg line
        # (local y -2.60), i.e. local y +3.19, so the 8.94 x 7.30 mm body
        # overhangs the edge by 0.46 mm and the pad row sits 7.2 mm inside it.
        usbc=dict(px=143.6, py=-23.81, ang=180.0),
        reset=dict(px=95.0, py=-12.0, ang=0.0),
        # the old top right mount hole sat exactly under the link port; it
        # moved 16 mm inboard, out of the connector and its fan-out
        mounts=[(30.0, -23.5), (130.0, -23.5), (-22.0, 99.5), (66.0, 99.5),
                (146.0, 99.5), (146.0, 55.0)],
    ),
    "right": dict(
        # B starts at -0.5 u (-9.53 mm) and every row ends at 8.5 u (161.93 mm),
        # so the outline leaves 5.2 mm / 4.3 mm beside them, as before -- the
        # 181 mm wide board just sits 4.76 mm further left.  The right hand
        # mounting hole moved from the (now much narrower) right strip into
        # the bottom band, clear of the Right key's diode.
        outline=(-14.75, -27.0, 166.25, 103.0),
        mcu=dict(px=148.0, py=-11.0, mirror=True),
        usbc=dict(px=-8.9, py=-23.81, ang=180.0),
        reset=dict(px=120.0, py=-12.0, ang=0.0),
        mounts=[(-6.5, 99.5), (55.0, 99.5), (130.0, 99.5), (160.0, 99.5),
                (6.0, -23.5), (100.0, -23.5)],
    ),
}


def keys(hand):
    """Return the key table with board coordinates and matrix positions."""
    out = []
    sn = 0
    for r, row in enumerate(ROWS[hand]):
        for entry in row:
            label, xu, wu, col = entry[0], entry[1], entry[2], entry[3]
            kind = entry[4] if len(entry) > 4 else "switch"
            if kind == "encoder":
                ref, dref, knet = "RE1", "D_ENC", "K_ENC"
            else:
                sn += 1
                ref, dref, knet = "SW%d" % sn, "D%d" % sn, "K%d" % sn
            cx = (xu + wu / 2.0) * U
            cy = ROW0_Y + r * ROW_PITCH
            # 2 u and wider: the Choc v2 stabilizer needs the whole strip beside
            # the switch clear (see STAB_CUTOUT), so those switches are placed
            # 90 degrees turned -- with the pads in line, the hot swap socket
            # pad 2 lands inside the cutout.  -90 keeps switch pad 2 (the COL2ROW
            # side, which continues to the diode) next to the diode row.
            sw_ang = -90.0 if (kind == "switch" and
                               wu >= STAB_MIN_U - 1e-9) else 0.0
            out.append(dict(
                n=sn, ref=ref, dref=dref, label=label, kind=kind,
                row=r, col=col, xu=xu, wu=wu, cx=cx, cy=cy, sw_ang=sw_ang,
                knet=knet,
                matrix=(r, col),
            ))
    return out


def matrix_size(hand):
    rows = len(ROWS[hand])
    cols = max(max(e[3] for e in r) for r in ROWS[hand]) + 1
    return rows, cols


# ------------------------------------------------- Choc v2 PCB stabilizer
# Kailh Choc v2 PCB mount stabilizer (Salicylic-acid3 / Keeb-On! part), 2.00 u
# pattern.  It differs from the Cherry MX one in the clip holes and in that the
# housing hangs through the PCB, so every wide key also needs two Edge.Cuts
# cutouts:
#   * 3.2 x 3.4  mm oval NPTH at (+-11.9, cy - 6.2)   (clip hole, back)
#   * 3.0 x 4.0  mm oval NPTH at (+-11.9, cy + 8.24)  (screw hole, front)
#   * cutout x = 8.9 .. 14.9 (mirrored), y = cy - 3.75 .. cy + 3.75
STAB_MIN_U = 2.0            # every key this wide or wider gets a stabilizer
# (dx from the key centre, dy from the key centre, size along x, size along y)
STAB_HOLES = ((11.9, -6.2, 3.2, 3.4), (11.9, 8.24, 3.0, 4.0))
STAB_CUTOUT = (8.9, -3.75, 14.9, 3.75)   # right hand cutout; mirrored in x


def stab_keys(hand):
    """Keys of one half that need a stabilizer (2 u and wider)."""
    return [k for k in keys(hand)
            if k["kind"] != "encoder" and k["wu"] >= STAB_MIN_U - 1e-9]


def stab_holes(hand):
    """The four oval clip holes of every wide key, in board coordinates."""
    out = []
    for k in stab_keys(hand):
        for sx in (-1, 1):
            for dx, dy, w, h in STAB_HOLES:
                out.append(dict(ref=k["ref"], label=k["label"], wu=k["wu"],
                                x=k["cx"] + sx * dx, y=k["cy"] + dy,
                                w=w, h=h, d=max(w, h)))
    return out


def stab_cutouts(hand):
    """The two Edge.Cuts rectangles of every wide key, in board coordinates."""
    out = []
    for k in stab_keys(hand):
        x0, y0, x1, y1 = STAB_CUTOUT
        out.append(dict(ref=k["ref"], label=k["label"],
                        x0=k["cx"] - x1, y0=k["cy"] + y0,
                        x1=k["cx"] - x0, y1=k["cy"] + y1, side="left"))
        out.append(dict(ref=k["ref"], label=k["label"],
                        x0=k["cx"] + x0, y0=k["cy"] + y0,
                        x1=k["cx"] + x1, y1=k["cy"] + y1, side="right"))
    return out


def keycaps(hand):
    """Count of keycaps per width, e.g. {1.0: 40, 1.25: 6, ...}."""
    out = {}
    for k in keys(hand):
        if k["kind"] == "encoder":
            continue
        out[k["wu"]] = out.get(k["wu"], 0) + 1
    return out
