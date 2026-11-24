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
"""
from .geom import U, ROW0_Y, ROW_PITCH

# x of the left macro column: its right edge sits 0.25 u left of the main
# column (which starts at x = 0).
MACRO_X = -1.25

LEFT_ROWS = [
    [("ENC", MACRO_X, 1, 7, "encoder"),
     ("`", 0, 1, 0), ("1", 1, 1, 1), ("2", 2, 1, 2), ("3", 3, 1, 3),
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
    [("PgDn", MACRO_X, 1, 7),
     ("LCtrl", 0, 1.25, 0), ("LWin", 1.25, 1.25, 1), ("LAlt", 2.5, 1.25, 2),
     ("Space", 3.75, 2.0, 3)],
]

# Right half.  Every row starts at its own x so that the finished board keeps
# the ANSI stagger; the top three rows all end at 8.5 u so the right edge is one
# straight line.  Row 0 (numbers) sits 0.5 u right of the tab row, row 2 (home)
# 0.25 u.  Row 3 starts at -0.25 u: the split of a full ANSI board puts this
# row's ``B`` 0.25 u left of ``N``, which is the same 2.25 u stagger the left
# half's bottom row has against its ``Tab`` row.
#
# 2026-11 second revision (user request):
#   * ``B`` added here, 0.25 u left of ``N`` and so 0.25 u left of Y
#   * RShift is 1.0 u (was 1.75 u) and sits directly left of ``Up``
#   * no RFn key: 0.25 u of empty PCB between RCtrl and Left
#   * the space freed at the right of the arrow cluster is a 1 u ``Del``
#   * the row therefore needs a ninth matrix column (COL8)
RIGHT_ROWS = [
    # 0.5 u start, BSpc 2.0 u -> right edge 8.5 u
    [("7", 0.5, 1, 0), ("8", 1.5, 1, 1), ("9", 2.5, 1, 2), ("0", 3.5, 1, 3),
     ("-", 4.5, 1, 4), ("=", 5.5, 1, 5), ("BSpc", 6.5, 2.0, 6)],
    # 0.0 u start, \\ 1.5 u (same width as the left half's Tab) -> 8.5 u
    [("Y", 0, 1, 0), ("U", 1, 1, 1), ("I", 2, 1, 2), ("O", 3, 1, 3),
     ("P", 4, 1, 4), ("[", 5, 1, 5), ("]", 6, 1, 6), ("\\", 7, 1.5, 7)],
    # 0.25 u start, Enter 2.25 u -> 8.5 u
    [("H", 0.25, 1, 0), ("J", 1.25, 1, 1), ("K", 2.25, 1, 2), ("L", 3.25, 1, 3),
     (";", 4.25, 1, 4), ("'", 5.25, 1, 5), ("Enter", 6.25, 2.25, 6)],
    # -0.25 u start: B | N M , . / | RShift 1 u | Up | Del -> 8.75 u
    [("B", -0.25, 1, 0), ("N", 0.75, 1, 1), ("M", 1.75, 1, 2),
     (",", 2.75, 1, 3), (".", 3.75, 1, 4), ("/", 4.75, 1, 5),
     ("RShift", 5.75, 1.0, 6), ("Up", 6.75, 1, 7), ("Del", 7.75, 1, 8)],
    # bottom: 0.75 + 2.25 + 1.25 * 2 = 5.5 u, then a 0.25 u gap, then Left /
    # Down / Right under RShift / Up / Del, so both rows end at 8.75 u.
    [("Space", 0.75, 2.25, 0), ("RAlt", 3.0, 1.25, 1), ("RCtrl", 4.25, 1.25, 2),
     ("Left", 5.75, 1, 6), ("Down", 6.75, 1, 7), ("Right", 7.75, 1, 8)],
]

ROWS = {"left": LEFT_ROWS, "right": RIGHT_ROWS}

# Board outline (x0, y0, x1, y1) and the hardware bay contents, per half.
CONFIG = {
    "left": dict(
        outline=(-26.0, -27.0, 150.0, 103.0),
        mcu=dict(px=7.0, py=-11.0, mirror=False),
        trrs=dict(px=147.0, py=-11.0, ang=-90.0),
        reset=dict(px=95.0, py=-12.0, ang=0.0),
        mounts=[(30.0, -23.5), (146.0, -23.5), (-22.0, 99.5), (66.0, 99.5),
                (146.0, 99.5), (146.0, 55.0)],
    ),
    "right": dict(
        # B starts 0.25 u (4.76 mm) left of x = 0 and Del / Right end at
        # 8.75 u (166.7 mm), so the outline leaves 5.2 mm / 4.3 mm beside them.
        outline=(-10.0, -27.0, 171.0, 103.0),
        mcu=dict(px=148.0, py=-11.0, mirror=True),
        trrs=dict(px=-7.0, py=-11.0, ang=90.0),
        reset=dict(px=120.0, py=-12.0, ang=0.0),
        mounts=[(-6.5, 99.5), (55.0, 99.5), (130.0, 99.5),
                (-6.0, -23.5), (100.0, -23.5), (167.0, 55.0)],
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
            out.append(dict(
                n=sn, ref=ref, dref=dref, label=label, kind=kind,
                row=r, col=col, xu=xu, wu=wu, cx=cx, cy=cy,
                knet=knet,
                matrix=(r, col),
            ))
    return out


def matrix_size(hand):
    rows = len(ROWS[hand])
    cols = max(max(e[3] for e in r) for r in ROWS[hand]) + 1
    return rows, cols


def keycaps(hand):
    """Count of keycaps per width, e.g. {1.0: 40, 1.25: 6, ...}."""
    out = {}
    for k in keys(hand):
        if k["kind"] == "encoder":
            continue
        out[k["wu"]] = out.get(k["wu"], 0) + 1
    return out
