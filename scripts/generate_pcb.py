"""Build the two choc-split-60 PCBs (layout, hand placed matrix truss, routed
fan-in) and write the KiCad project files.

Run:  python3 scripts/generate_pcb.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from pcbgen.build import Board, SIG_W, PWR_W, VIA_D, VIA_DRILL   # noqa: E402
from pcbgen.router import Router                                  # noqa: E402
from pcbgen.schematic import write_schematic                      # noqa: E402
from pcbgen.pro import write_project                              # noqa: E402

ROOT = os.path.dirname(HERE)


def pad_cells(router, pad):
    nid = router.b.net_id[pad.net]
    out = []
    r = max(pad.w, pad.h) / 2 + 0.1
    iy0, iy1, ix0, ix1 = router._bbox(pad.gx, pad.gy, r)
    for lay in (0, 1):
        for iy in range(iy0, iy1 + 1):
            for ix in range(ix0, ix1 + 1):
                if router.owner[lay][iy, ix] == nid:
                    out.append((lay, iy, ix))
    return out


def net_cells(router, net):
    nid = router.b.net_id[net]
    out = []
    for lay in (0, 1):
        iy, ix = np.nonzero(router.owner[lay] == nid)
        out.extend((lay, int(a), int(b)) for a, b in zip(iy, ix))
    return out


def route_jobs(board):
    """Return the ordered list of (net, [pads]) connections still to make."""
    mcu = board.mcu
    by_net = {}
    for p in mcu.pads:
        if p.net:
            by_net.setdefault(p.net, []).append(p)
    jobs = []
    # matrix fan-in first: one controller pin per row / column net
    for net in ["ROW0", "ROW1", "ROW2", "ROW3", "ROW4", "ROW5",
                "COL0", "COL1", "COL2", "COL3", "COL4", "COL5", "COL6", "COL7"]:
        jobs.append((net, [], SIG_W, True))
    for net in ["RST", "TX", "RX", "VCC", "GND"]:
        jobs.append((net, [], SIG_W if net in ("TX", "RX", "RST") else PWR_W, False))
    return jobs


def build(hand, verbose=True):
    connected = {}
    b = Board(hand)
    b.build()
    b.build_truss()
    r = Router(b)
    r.build_masks()

    # ---- column chains -----------------------------------------------------
    for col in sorted(b.col_keys):
        ks = sorted(b.col_keys[col], key=lambda k: k["cy"])
        net = "COL%d" % col
        connected.setdefault(net, set())
        connected[net].add(id(ks[0]["sw"].pad("1")))
        for k in ks[1:]:
            _connect_pad(b, r, k["sw"].pad("1"), connected[net])
            connected[net].add(id(k["sw"].pad("1")))
    # ---- matrix fan-in -----------------------------------------------------
    for row in range(6):
        _connect_pin(b, r, "ROW%d" % row)
    for col in sorted(b.col_keys):
        _connect_pin(b, r, "COL%d" % col)
    # ---- power / serial ----------------------------------------------------
    for net in ["RST", "TX", "RX", "VCC"]:
        _connect_pads(b, r, net, PWR_W if net == "VCC" else SIG_W)
    _connect_pads(b, r, "GND", PWR_W)
    if verbose and r.failed:
        print("  ! failed nets:", r.failed)
    return b, r


def _connect_pin(b, r, net):
    """Connect the controller pad of `net` to the copper already placed."""
    pad = None
    for p in b.mcu.pads:
        if p.net == net:
            pad = p
            break
    if pad is None:
        return
    src = net_cells(r, net)
    if not src:
        r.failed.append((net, "no existing copper"))
        return
    goals = pad_cells(r, pad)
    gset = set(goals)
    src = [c for c in src if c not in gset]
    if not src:
        r.failed.append((net, "pad only"))
        return
    nid = b.net_id[net]
    path = r.path(nid, src, goals, width=SIG_W)
    if path is None:
        path = r.path(nid, src, goals, width=SIG_W, prefer=None)
    if path is None:
        r.failed.append((net, "no path"))
        return
    r.commit(nid, path, SIG_W, net)


def _connect_pad(b, r, pad, done=None):
    """Route one pad of an existing net into that net's routed copper."""
    net = pad.net
    nid = b.net_id[net]
    goals = pad_cells(r, pad)
    gset = set(goals)
    done = done or set()
    exclude = set(gset)
    for fp in b.fps:
        for p in fp.pads:
            if p.net == net and p is not pad and id(p) not in done:
                exclude.update(pad_cells(r, p))
    src = [c for c in net_cells(r, net) if c not in exclude]
    if not src:
        return
    path = r.path(nid, src, goals, width=SIG_W)
    if path is None:
        path = r.path(nid, src, goals, width=SIG_W, prefer=None)
    if path is None:
        r.failed.append((net, "no path to %s" % pad.fp.ref))
        return
    r.commit(nid, path, SIG_W, net)


def _connect_pads(b, r, net, width):
    pads = [p for fp in b.fps if fp is not b.mcu for p in fp.pads if p.net == net]
    pads += [p for p in b.mcu.pads if p.net == net]
    if len(pads) < 2:
        return
    pads.sort(key=lambda p: (p.gx, p.gy))
    nid = b.net_id[net]
    done = {id(pads[0])}
    seed = pad_cells(r, pads[0])
    for p in pads[1:]:
        goals = pad_cells(r, p)
        if not goals:
            continue
        excl = set(goals)
        for q in pads:
            if id(q) not in done and q is not p:
                excl.update(pad_cells(r, q))
        src = [c for c in (net_cells(r, net) + seed) if c not in excl]
        if not src:
            continue
        path = r.path(nid, src, goals, width=width)
        if path is None:
            path = r.path(nid, src, goals, width=width, prefer=None)
        if path is None:
            r.failed.append((net, "no path to %s" % p.fp.ref))
            continue
        r.commit(nid, path, width, net)
        done.add(id(p))


def pad_seed(r, pad):
    cells = pad_cells(r, pad)
    if cells:
        return cells
    iy, ix = r.cell(pad.gx, pad.gy)
    return [(0, iy, ix), (1, iy, ix)]


def write_board(b, path, title, root):
    txt = b.pcb_text(title)
    with open(path, "w") as f:
        f.write(txt)
    write_project(b, path, title, root=root)


def main():
    for hand in ("left", "right"):
        print("building", hand)
        b, r = build(hand)
        print("  keys=%d tracks=%d vias=%d" % (len(b.keys), len(b.tracks), len(b.vias)))
        out = os.path.join(ROOT, "pcb", "choc-split-60-%s.kicad_pcb" % hand)
        sch = os.path.join(ROOT, "pcb", "choc-split-60-%s.kicad_sch" % hand)
        root = write_schematic(b, sch, "choc-split-60-%s" % hand, None)
        write_board(b, out, "choc-split-60-%s" % hand, root)
        print("  wrote", out)


if __name__ == "__main__":
    main()
