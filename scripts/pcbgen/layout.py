"""Physical key layout for both halves of the choc-split-60."""
from .geom import U, ROW0_Y, ROW_PITCH

# (label, x in units, width in units) per row, top to bottom.
LEFT_ROWS = [
    [("`", 0, 1), ("1", 1, 1), ("2", 2, 1), ("3", 3, 1), ("4", 4, 1), ("5", 5, 1), ("6", 6, 1)],
    [("Tab", 0, 1.5), ("Q", 1.5, 1), ("W", 2.5, 1), ("E", 3.5, 1), ("R", 4.5, 1), ("T", 5.5, 1)],
    [("Caps", 0, 1.75), ("A", 1.75, 1), ("S", 2.75, 1), ("D", 3.75, 1), ("F", 4.75, 1), ("G", 5.75, 1)],
    [("LShift", 0, 2.25), ("Z", 2.25, 1), ("X", 3.25, 1), ("C", 4.25, 1), ("V", 5.25, 1), ("B", 6.25, 1)],
    [("LCtrl", 0, 1.25), ("LWin", 1.25, 1.25), ("LAlt", 2.5, 1.25), ("Space", 3.75, 2.0)],
    [("Thumb1", 4.0, 1, 4), ("Thumb2", 5.0, 1, 5)],
]

RIGHT_ROWS = [
    [("7", 0, 1), ("8", 1, 1), ("9", 2, 1), ("0", 3, 1), ("-", 4, 1), ("=", 5, 1), ("BSpc", 6, 2.0)],
    [("Y", 0, 1), ("U", 1, 1), ("I", 2, 1), ("O", 3, 1), ("P", 4, 1), ("[", 5, 1), ("]", 6, 1), ("\\", 7, 1)],
    [("H", 0, 1), ("J", 1, 1), ("K", 2, 1), ("L", 3, 1), (";", 4, 1), ("'", 5, 1), ("Enter", 6, 2.25)],
    [("N", 0, 1), ("M", 1, 1), (",", 2, 1), (".", 3, 1), ("/", 4, 1), ("RShift", 5, 1.75)],
    [("Space", 0, 2.0), ("RAlt", 2.0, 1.25), ("RFn", 3.25, 1.25), ("RCtrl", 4.5, 1.25)],
    [("Thumb1", 1.0, 1, 1), ("Thumb2", 2.0, 1, 2)],
]

ROWS = {"left": LEFT_ROWS, "right": RIGHT_ROWS}

# Board outline (x0, y0, x1, y1) and the hardware bay contents, per half.
CONFIG = {
    "left": dict(
        outline=(-10.0, -22.0, 150.0, 121.0),
        mcu=dict(px=7.0, py=-11.0, mirror=False),
        trrs=dict(px=147.0, py=-11.0, ang=-90.0),
        reset=dict(px=95.0, py=-12.0, ang=0.0),
        mounts=[(30.0, -18.5), (146.0, -18.5), (-6.5, 117.5), (146.0, 117.5),
                (66.0, 117.5), (146.0, 55.0)],
    ),
    "right": dict(
        outline=(-10.0, -22.0, 165.0, 121.0),
        mcu=dict(px=148.0, py=-11.0, mirror=True),
        trrs=dict(px=-7.0, py=-11.0, ang=90.0),
        reset=dict(px=120.0, py=-12.0, ang=0.0),
        mounts=[(110.0, -18.5), (-6.0, -18.5), (-6.5, 117.5), (161.0, 117.5),
                (80.0, 117.5), (-6.5, 55.0)],
    ),
}


def keys(hand):
    """Return the key table with board coordinates and matrix positions."""
    out = []
    idx = 0
    for r, row in enumerate(ROWS[hand]):
        for c, entry in enumerate(row):
            label, xu, wu = entry[0], entry[1], entry[2]
            if len(entry) > 3:
                c = entry[3]
            idx += 1
            cx = (xu + wu / 2.0) * U
            cy = ROW0_Y + r * ROW_PITCH
            out.append(dict(
                n=idx, ref="SW%d" % idx, dref="D%d" % idx, label=label,
                row=r, col=c, xu=xu, wu=wu, cx=cx, cy=cy,
                knet="K%d" % idx,
                matrix=(r, c),
            ))
    return out


def matrix_size():
    rows = max(len(ROWS["left"]), len(ROWS["right"]))
    cols = max(max(len(r) for r in ROWS["left"]), max(len(r) for r in ROWS["right"]))
    return rows, cols
