"""Geometry helpers shared by the generator and the (independent) verifier."""
import math

U = 19.05          # key pitch used by this board (mm)
ROW0_Y = 9.525     # centre line of matrix row 0
ROW_PITCH = 19.05


def place(px, py, lx, ly, ang=0.0, side="F"):
    """Transform a local footprint coordinate to board coordinates.

    KiCad convention: positive angle rotates counter clockwise on screen
    (y grows downwards in the file), and a footprint placed on the back side is
    mirrored about its local Y axis before the rotation is applied.
    """
    a = math.radians(ang)
    c, s = math.cos(a), math.sin(a)
    if side == "B":
        lx = -lx
    return (px + lx * c + ly * s, py - lx * s + ly * c)


def rot_pt(x, y, ang_deg):
    a = math.radians(ang_deg)
    c, s = math.cos(a), math.sin(a)
    return (x * c + y * s, -x * s + y * c)


# ---------------------------------------------------------------- distances
def pt_seg(p, a, b):
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 <= 1e-12:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / L2
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def seg_seg(a, b, c, d):
    def cross(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])

    d1 = cross(c, d, a)
    d2 = cross(c, d, b)
    d3 = cross(a, b, c)
    d4 = cross(a, b, d)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return 0.0
    return min(pt_seg(a, c, d), pt_seg(b, c, d), pt_seg(c, a, b), pt_seg(d, a, b))


def pt_in_poly(p, poly):
    x, y = p
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            xin = (x1 - x0) * (y - y0) / (y1 - y0) + x0
            if x < xin:
                inside = not inside
    return inside


def poly_seg(poly, a, b):
    """Distance between a convex polygon and a segment (0 when they touch)."""
    if pt_in_poly(a, poly) or pt_in_poly(b, poly):
        return 0.0
    n = len(poly)
    best = 1e9
    for i in range(n):
        c = poly[i]
        d = poly[(i + 1) % n]
        best = min(best, seg_seg(a, b, c, d))
        if best == 0.0:
            return 0.0
    return best


def poly_poly(P, Q):
    if any(pt_in_poly(p, Q) for p in P):
        return 0.0
    if any(pt_in_poly(q, P) for q in Q):
        return 0.0
    best = 1e9
    n = len(P)
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        for j in range(len(Q)):
            c, d = Q[j], Q[(j + 1) % len(Q)]
            best = min(best, seg_seg(a, b, c, d))
            if best == 0.0:
                return 0.0
    return best


def dist_point_poly(p, poly):
    if pt_in_poly(p, poly):
        return 0.0
    best = 1e9
    n = len(poly)
    for i in range(n):
        best = min(best, pt_seg(p, poly[i], poly[(i + 1) % n]))
    return best


def circle_poly(cx, cy, r, n=16):
    """Circumscribed n-gon (never smaller than the circle)."""
    rr = r / math.cos(math.pi / n)
    return [(cx + rr * math.cos(2 * math.pi * i / n + math.pi / n),
             cy + rr * math.sin(2 * math.pi * i / n + math.pi / n)) for i in range(n)]


def oval_poly(cx, cy, w, h, ang=0.0, n=8):
    """Stadium shaped pad approximated by a polygon (circumscribed)."""
    r = min(w, h) / 2.0
    ln = (max(w, h) / 2.0) - r
    pts = []
    for i in range(n + 1):
        a = -math.pi / 2 + math.pi * i / n
        pts.append((ln + r * math.cos(a) / math.cos(math.pi / (2 * n)),
                    r * math.sin(a) / math.cos(math.pi / (2 * n))))
    for i in range(n + 1):
        a = math.pi / 2 + math.pi * i / n
        pts.append((-ln + r * math.cos(a) / math.cos(math.pi / (2 * n)),
                    r * math.sin(a) / math.cos(math.pi / (2 * n))))
    if w < h:  # vertical stadium: swap axes
        pts = [(y, x) for (x, y) in pts]
    out = []
    for (x, y) in pts:
        rx, ry = rot_pt(x, y, ang)
        out.append((cx + rx, cy + ry))
    return out


def rect_poly(cx, cy, w, h, ang=0.0):
    pts = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    out = []
    for (x, y) in pts:
        rx, ry = rot_pt(x, y, ang)
        out.append((cx + rx, cy + ry))
    return out
