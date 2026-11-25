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
    for net in ["ROW0", "ROW1", "ROW2", "ROW3", "ROW4",
                "COL0", "COL1", "COL2", "COL3", "COL4", "COL5", "COL6", "COL7",
                "COL8"]:
        jobs.append((net, [], SIG_W, True))
    for net in ["RST", "TX", "RX", "VCC", "GND"]:
        jobs.append((net, [], SIG_W if net in ("TX", "RX", "RST") else PWR_W, False))
    return jobs


def build(hand, verbose=True):
    connected = {}
    b = Board(hand)
    b.build()
    b.build_truss()
    b.build_usbc_fanout()
    r = Router(b)
    r.build_masks()

    # ---- column chains -----------------------------------------------------
    for col in sorted(b.col_keys):
        ks = sorted(b.col_keys[col], key=lambda k: k["cy"])
        net = "COL%d" % col
        connected.setdefault(net, set())
        connected[net].add(id(ks[0]["colpad"]))
        for k in ks[1:]:
            _connect_pad(b, r, k["colpad"], connected[net])
            connected[net].add(id(k["colpad"]))
    # ---- matrix fan-in -----------------------------------------------------
    for row in range(5):
        _connect_pin(b, r, "ROW%d" % row)
    # Columns are fanned in from the outside in: the last columns sit closest to
    # the controller and the corridors around it are the scarcest, so they claim
    # their path first and the short runs use what is left.
    for col in sorted(b.col_keys, reverse=True):
        _connect_pin(b, r, "COL%d" % col)
    # ---- encoder (left half only) ------------------------------------------
    for net in ["ENC_A", "ENC_B"]:
        _connect_pads(b, r, net, SIG_W)
    # ---- power / serial ----------------------------------------------------
    # RST only links the reset switch to the controller; the four link nets are
    # already fanned out of the USB-C connector by hand (build_usbc_fanout), so
    # the router only has to run them from that fan-out to the controller pin.
    _connect_pads(b, r, "RST", SIG_W)
    for net, width in ((b.dplus, SIG_W), (b.dminus, SIG_W),
                       ("VCC", PWR_W), ("GND", PWR_W)):
        _connect_entry(b, r, net, width)
    _connect_pads(b, r, "GND", PWR_W, skip_refs=("J1",))
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


def _entry_cells(r, nid, pt, lay):
    """Grid cells that sit on the hand routed copper around a point.

    The maze grid is 0.25 mm and the hand drawn fan-out does not necessarily
    land on a grid line, so the owner map can be empty along a perfectly good
    track.  Take the cells of the square the point falls in (their centres are
    at most 0.18 mm away, so they still overlap the 0.25 mm track) and keep the
    ones no other net blocks.
    """
    blocked = r._blocked_for(nid)[lay]
    iy, ix = r.cell(pt[0], pt[1])
    out = []
    for jy in (iy, iy + 1):
        for jx in (ix, ix + 1):
            if 0 <= jy < r.ny and 0 <= jx < r.nx and not blocked[jy, jx]:
                out.append((lay, jy, jx))
    if not out:
        out = [(lay, iy, ix)]
    return out


def _connect_entry(b, r, net, width):
    """Route a USB-C net from its hand placed fan-out to the controller pin."""
    pt, layer = b.usbc_entry(net)
    nid = b.net_id[net]
    lay = 0 if layer == "F.Cu" else 1
    src = _entry_cells(r, nid, pt, lay)
    pad = next((p for p in b.mcu.pads if p.net == net), None)
    if pad is None or not src:
        r.failed.append((net, "no entry"))
        return
    goals = pad_cells(r, pad)
    path = r.path(nid, src, goals, width=width)
    if path is None:
        path = r.path(nid, src, goals, width=width, prefer=None)
    if path is None:
        r.failed.append((net, "no path from the connector"))
        return
    r.commit(nid, path, width, net)


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


def _connect_pads(b, r, net, width, skip_refs=()):
    pads = [p for fp in b.fps if fp is not b.mcu and fp.ref not in skip_refs
            for p in fp.pads if p.net == net]
    # the fan-out of a skipped part is copper of this net; only its own pads are
    # not allowed to seed a new track (they were already wired by hand)
    skip_cells = set()
    for fp in b.fps:
        if fp.ref in skip_refs:
            for p in fp.pads:
                if p.net:
                    skip_cells.update(pad_cells(r, p))
    pads += [p for p in b.mcu.pads if p.net == net]
    if len(pads) < 2:
        return
    pads.sort(key=lambda p: (p.gx, p.gy))
    nid = b.net_id[net]
    # Start from copper that is already there (a net can reach this point half
    # routed, e.g. GND from the USB-C fan-out), never from the first pad itself:
    # seeding on a pad would grow a second island that never joins the first.
    pending = list(pads)
    for _ in range(len(pending) + 1):
        if not pending:
            return
        goal = {id(p): (pad_cells(r, p) or pad_seed(r, p)) for p in pending}
        excl = set()
        for g in goal.values():
            excl.update(g)
        src = [c for c in net_cells(r, net)
               if c not in excl and c not in skip_cells]
        if not src:
            p = pending.pop(0)           # nothing routed yet: this pad seeds
            src = goal[id(p)]
        moved = False
        for p in list(pending[::-1]):
            goals = goal[id(p)]
            path = r.path(nid, src, goals, width=width)
            if path is None:
                path = r.path(nid, src, goals, width=width, prefer=None)
            if path is None:
                continue
            r.commit(nid, path, width, net)
            pending.remove(p)
            moved = True
            excl = set()
            for q in pending:
                excl.update(goal[id(q)])
            src = [c for c in net_cells(r, net)
                   if c not in excl and c not in skip_cells]
        if not moved:
            break
    for p in pending:
        r.failed.append((net, "no path to %s" % p.fp.ref))


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
    only_sch = "--schematic-only" in sys.argv[1:]
    for hand in ("left", "right"):
        print("building", hand)
        sch = os.path.join(ROOT, "pcb", "choc-split-60-%s.kicad_sch" % hand)
        if only_sch:
            # redraw the schematic page only; the routed PCB is left untouched
            b = Board(hand)
            b.build()
            root = _root_uuid(sch)
            write_schematic(b, sch, "choc-split-60-%s" % hand, root)
            print("  wrote", sch)
            continue
        b, r = build(hand)
        print("  keys=%d tracks=%d vias=%d" % (len(b.keys), len(b.tracks), len(b.vias)))
        out = os.path.join(ROOT, "pcb", "choc-split-60-%s.kicad_pcb" % hand)
        root = write_schematic(b, sch, "choc-split-60-%s" % hand, None)
        write_board(b, out, "choc-split-60-%s" % hand, root)
        print("  wrote", out)


def _root_uuid(path):
    """Keep the sheet uuid stable when only the schematic is regenerated."""
    if not os.path.exists(path):
        return None
    with open(path) as f:
        for line in f:
            if line.strip().startswith('(uuid "'):
                return line.split('"')[1]
    return None


if __name__ == "__main__":
    main()
