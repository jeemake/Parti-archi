#!/usr/bin/env python3
"""3 partis constructifs — cour / ailes / barre. Pas un top-k. Pas un GAN."""
from __future__ import annotations

import json
import math
import sys
from copy import deepcopy
from pathlib import Path

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from checker import COLLAR, check, write_svg

FAMILIES = ("cour", "ailes", "barre")
TPL_DIR = Path(__file__).resolve().parent / "templates"
OUT_DIR = ROOT / "out"

KIND_OF = {
    "rue": "site",
    "parking": "site",
    "entree_site": "site",
    "porte": "seuil",
    "galerie": "seuil",
    "jardin": "jardin",
    "ext": "site",
    "patio": "air",
    "sejour": "jour",
    "sam": "jour",
    "cuisine": "jour",
    "cellier": "jour",
    "chambre": "nuit",
    "sdb": "nuit",
    "guerite": "service",
    "local_ge": "service",
    "garage": "service",
}
DEFAULT_AREA = {
    "parking": 28,
    "entree_site": 8,
    "porte": 4,
    "jardin": 50,
    "patio": 18,
    "galerie": 14,
    "guerite": 6,
    "local_ge": 6,
    "garage": 12,
    "sejour": 36,
    "sam": 14,
    "cuisine": 12,
    "cellier": 4,
    "chambre": 14,
    "sdb": 5,
}

SHARED_EDGES = [
    ("cuisine", "sam", "must"),
    ("sam", "sejour", "must"),
    ("cuisine", "cellier", "must"),
    ("sdb", "chambre", "must"),
    ("guerite", "rue", "must"),
    ("sejour", "patio", "must"),
    ("sejour", "jardin", "must_face"),
    ("cuisine", "ext", "must_face"),
    ("garage", "rue", "near"),
    ("local_ge", "rue", "near"),
    ("sam", "patio", "near"),
]


def _poly(coords):
    p = Polygon(coords)
    if not p.is_valid:
        p = p.buffer(0)
    if p.exterior.is_ccw is False:
        p = Polygon(list(p.exterior.coords)[::-1])
    return p



def _ring(seq):
    return [(float(x), float(y)) for x, y in list(seq)[:-1]]


def export_emprise(geom):
    empty = {"poly_m": [], "holes_m": [], "parts_m": []}
    if geom is None or geom.is_empty:
        return empty
    if geom.geom_type == "MultiPolygon":
        parts = [_ring(p.exterior.coords) for p in geom.geoms]
        holes = []
        for p in geom.geoms:
            holes.extend(_ring(h.coords) for h in p.interiors)
        parts = [p for p in parts if len(p) >= 3]
        return {"poly_m": parts[0] if parts else [], "holes_m": holes, "parts_m": parts}
    if geom.geom_type != "Polygon":
        return empty
    return {
        "poly_m": _ring(geom.exterior.coords),
        "holes_m": [_ring(h.coords) for h in geom.interiors],
        "parts_m": [_ring(geom.exterior.coords)],
    }


def _coords(geom):
    return export_emprise(geom)["poly_m"]


def _has_hole(geom) -> bool:
    ex = export_emprise(geom)
    return bool(ex["holes_m"]) or len(ex["parts_m"]) > 1


def _is_aa_rectangle(coords, tol=0.05) -> bool:
    if not coords or len(coords) < 4:
        return False
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    bb = (max(xs) - min(xs)) * (max(ys) - min(ys))
    if bb <= 0:
        return False
    p = Polygon(coords)
    return abs(p.area - bb) <= max(tol, 0.02 * bb)

def _frozen_tampon(lot_coords, reculs) -> bool:
    reculs = reculs or {}
    if float(reculs.get("rue") or 0) > 0 or float(reculs.get("voisins") or 0) > 0:
        return False
    pts = [(float(x), float(y)) for x, y in lot_coords]
    return _is_aa_rectangle(pts)


def buildable(lot_coords, rue_edge: int, reculs: dict):
    poly = _poly(lot_coords)
    coords = list(poly.exterior.coords)[:-1]
    n = len(coords)
    strips = []
    for i in range(n):
        a, b = coords[i], coords[(i + 1) % n]
        rec = float(reculs.get("rue" if i == rue_edge else "voisins", 0) or 0)
        if rec <= 0:
            continue
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        strips.append(
            Polygon(
                [
                    a,
                    b,
                    (b[0] + nx * rec, b[1] + ny * rec),
                    (a[0] + nx * rec, a[1] + ny * rec),
                ]
            )
        )
    if not strips:
        return poly
    pad = poly.difference(unary_union(strips))
    if pad.is_empty:
        vals = [float(v) for v in reculs.values() if v]
        pad = poly.buffer(-min(vals)) if vals else poly
    if pad.geom_type == "MultiPolygon":
        pad = max(pad.geoms, key=lambda g: g.area)
    return pad


def _rue_vec(lot_coords, rue_edge: int):
    coords = list(_poly(lot_coords).exterior.coords)[:-1]
    a, b = coords[rue_edge % len(coords)], coords[(rue_edge + 1) % len(coords)]
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    return (a, b), (ux, uy), (nx, ny)


def massing(family: str, pad, lot_coords, rue_edge: int):
    (_, _), (ux, uy), (nx, ny) = _rue_vec(lot_coords, rue_edge)
    c = pad.centroid
    if family == "cour":
        side = max(3.0, min(6.5, (pad.area ** 0.5) * 0.28))
        hole = box(c.x - side / 2, c.y - side / 2, c.x + side / 2, c.y + side / 2)
        out = pad.difference(hole)
        return out if not out.is_empty else pad
    if family == "ailes":
        # slit through (H / II), not an interior hole
        w = 2.3
        half = 1.0e4
        slit = Polygon(
            [
                (c.x - ux * half - nx * w / 2, c.y - uy * half - ny * w / 2),
                (c.x + ux * half - nx * w / 2, c.y + uy * half - ny * w / 2),
                (c.x + ux * half + nx * w / 2, c.y + uy * half + ny * w / 2),
                (c.x - ux * half + nx * w / 2, c.y - uy * half + ny * w / 2),
            ]
        )
        out = pad.difference(slit)
        return out if not out.is_empty else pad
    minx, miny, maxx, maxy = pad.bounds
    W, H = maxx - minx, maxy - miny
    if W >= H:
        bh = min(H * 0.85, max(W / 2.5, 4.0))
        y0 = maxy - bh if ny > 0 else miny
        bar = pad.intersection(box(minx, y0, maxx, y0 + bh))
    else:
        bw = min(W * 0.85, max(H / 2.5, 4.0))
        x0 = maxx - bw if nx > 0 else minx
        bar = pad.intersection(box(x0, miny, x0 + bw, maxy))
    if bar.is_empty:
        bar = pad
    bc = bar.centroid
    bite_s = max(2.0, min(3.5, (bar.area ** 0.5) * 0.18))
    if W >= H:
        bite = box(minx, bc.y - bite_s / 2, minx + bite_s, bc.y + bite_s / 2)
    else:
        bite = box(bc.x - bite_s / 2, miny, bc.x + bite_s / 2, miny + bite_s)
    out = bar.difference(bite)
    return out if not out.is_empty else bar



def _close_from_emprise(geom) -> dict:
    ex = export_emprise(geom)
    void = bool(ex["holes_m"]) or len(ex["parts_m"]) > 1
    return {"poly": ex["poly_m"], "holes": ex["holes_m"], "filled": not void}

def _tid(nodes: dict, typ: str):
    for n in nodes.values():
        if n.get("type") == typ or n.get("id") == typ:
            return n["id"]
    return typ


def _add_edge(edges, a, b, rel, nodes):
    if a not in nodes or b not in nodes or a == b:
        return
    key = frozenset({a, b})
    for e in edges:
        if frozenset({e["a"], e["b"]}) == key:
            return
    edges.append({"a": a, "b": b, "rel": rel})


def _load_template(family: str) -> list[dict]:
    p = TPL_DIR / f"{family}.json"
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    return list(data.get("edges") or [])


def _ensure_node(nodes: dict, name: str) -> None:
    if any(n.get("type") == name or n.get("id") == name for n in nodes.values()):
        return
    nodes[name] = {
        "id": name,
        "type": name,
        "kind": KIND_OF.get(name, "site"),
        "area_m2": DEFAULT_AREA.get(name),
    }


def build_graph(family: str, programme: list[dict], emprise_coords: list, has_void: bool) -> dict:
    nodes: dict[str, dict] = {}
    for p in programme or []:
        n = dict(p)
        nid = n.get("id") or n.get("type")
        n["id"] = nid
        n.setdefault("type", nid)
        n.setdefault("kind", KIND_OF.get(n["type"], "jour"))
        nodes[nid] = n
    for name in list(COLLAR) + ["ext"]:
        _ensure_node(nodes, name)
    if has_void:
        _ensure_node(nodes, "patio")
    for extra in ("guerite", "local_ge", "garage", "sam", "cuisine", "cellier", "chambre", "sdb"):
        _ensure_node(nodes, extra)
    for n in nodes.values():
        if n.get("type") == "patio":
            n["kind"] = "air"
    edges: list[dict] = []
    for a, b in zip(COLLAR, COLLAR[1:]):
        _add_edge(edges, _tid(nodes, a), _tid(nodes, b), "must", nodes)
    for a, b, rel in SHARED_EDGES:
        if not has_void and "patio" in (a, b):
            continue
        _add_edge(edges, _tid(nodes, a), _tid(nodes, b), rel, nodes)
    for e in _load_template(family):
        if not has_void and "patio" in (e.get("a"), e.get("b")):
            continue
        _add_edge(edges, _tid(nodes, e["a"]), _tid(nodes, e["b"]), e.get("rel") or "near", nodes)
    close = {"poly": emprise_coords, "filled": not has_void}
    return {"id": family, "nodes": list(nodes.values()), "edges": edges, "close": close}


def _nodes_by_id(g):
    return {n["id"]: n for n in g.get("nodes") or []}


def repair_once(graph: dict, emprise, family: str, lot_coords, rue_edge: int):
    r = check(graph)
    if r.get("ok"):
        return graph, emprise, r
    fails = r.get("fails") or []
    if not fails:
        return graph, emprise, r
    first = fails[0]
    g = deepcopy(graph)
    nodes = _nodes_by_id(g)
    edges = list(g.get("edges") or [])
    if first == "patio":
        _ensure_node(nodes, "patio")
        _ensure_node(nodes, "sejour")
        _ensure_node(nodes, "sam")
        for n in nodes.values():
            if n.get("type") == "patio":
                n["kind"] = "air"
        pid = _tid(nodes, "patio")
        _add_edge(edges, _tid(nodes, "sejour"), pid, "must", nodes)
        _add_edge(edges, _tid(nodes, "sam"), pid, "near", nodes)
    elif first == "broken_collar":
        for name in COLLAR:
            _ensure_node(nodes, name)
        for a, b in zip(COLLAR, COLLAR[1:]):
            _add_edge(edges, _tid(nodes, a), _tid(nodes, b), "must", nodes)
    elif first == "rectangle_close":
        emprise = massing(
            family,
            emprise if emprise is not None else _poly(lot_coords),
            lot_coords,
            rue_edge,
        )
        coords = _coords(emprise)
        g["close"] = _close_from_emprise(emprise)
        g["nodes"] = list(nodes.values())
        g["edges"] = edges
        return g, emprise, check(g)
    elif first == "must":
        detail = (r.get("detail") or {}).get("must") or [""]
        text = " ".join(detail)
        for a, b, rel in SHARED_EDGES:
            if a in text and b in text:
                _ensure_node(nodes, a)
                _ensure_node(nodes, b)
                _add_edge(edges, _tid(nodes, a), _tid(nodes, b), rel, nodes)
                break
        else:
            if "cuisine" in text:
                _ensure_node(nodes, "cuisine")
                _ensure_node(nodes, "ext")
                _add_edge(edges, _tid(nodes, "cuisine"), _tid(nodes, "ext"), "must_face", nodes)
    elif first == "forbid":
        drop = []
        for e in edges:
            ta = nodes.get(e["a"], {}).get("type")
            tb = nodes.get(e["b"], {}).get("type")
            types = {ta, tb}
            if types == {"garage", "chambre"} or types == {"local_ge", "chambre"}:
                drop.append(e)
            if types == {"sdb", "sejour"}:
                drop.append(e)
            if "ch_sde" in {ta, tb} and ({"garage", "local_ge"} & {ta, tb}):
                drop.append(e)
        edges = [e for e in edges if e not in drop]
    elif first in {"hall_width", "ch_sde"}:
        new_nodes = {}
        for nid, n in nodes.items():
            if n.get("type") == "ch_sde":
                new_nodes[nid] = {**n, "type": "chambre", "id": nid}
                sdb_id = f"sdb_{nid}"
                new_nodes[sdb_id] = {"id": sdb_id, "type": "sdb", "kind": "nuit", "area_m2": 5}
                _add_edge(edges, nid, sdb_id, "must", {**nodes, **new_nodes})
            elif n.get("type") in {"hall", "degagement"}:
                new_nodes[nid] = {**n, "type": "galerie", "kind": "seuil", "id": nid, "width_m": 1.8}
            else:
                new_nodes[nid] = n
        nodes = new_nodes
    g["nodes"] = list(nodes.values())
    g["edges"] = edges
    return g, emprise, check(g)


def write_parti_svg(graph, result, emprise_coords, path: Path):
    write_svg(graph, result, path)
    if not emprise_coords:
        return path
    xs = [p[0] for p in emprise_coords]
    ys = [p[1] for p in emprise_coords]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    bw, bh = max(maxx - minx, 1e-6), max(maxy - miny, 1e-6)
    ox, oy, s = 720.0, 70.0, 180.0 / max(bw, bh)
    pts = []
    for x, y in list(emprise_coords) + [emprise_coords[0]]:
        px = ox + (x - minx) * s
        py = oy + (maxy - y) * s
        pts.append(f"{px:.1f},{py:.1f}")
    d = "M " + " L ".join(pts) + " Z"
    insert = (
        f'<path d="{d}" fill="#efe8dc" fill-opacity="0.9" stroke="#6b6b6b" '
        f'stroke-width="1.2"/>'
        f'<text x="{ox}" y="{oy - 8}" font-size="10" fill="#718096">emprise {graph.get("id")}</text>\n'
    )
    text = Path(path).read_text(encoding="utf-8")
    text = text.replace(
        '<rect width="100%" height="100%" fill="#f7f3ea"/>',
        '<rect width="100%" height="100%" fill="#f7f3ea"/>\n' + insert,
    )
    Path(path).write_text(text, encoding="utf-8")
    return path



def generate(src) -> dict:
    if isinstance(src, (str, Path)):
        data = json.loads(Path(src).read_text(encoding="utf-8"))
    else:
        data = src
    lot = data["lot"]["poly_m"]
    rue_edge = int(data["lot"].get("rue_edge") or 0)
    reculs = data.get("reculs_m") or {"rue": 5, "voisins": 3}
    programme = data.get("programme") or []
    pad = buildable(lot, rue_edge, reculs)
    frozen = _frozen_tampon(lot, reculs)
    options = []
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for family in FAMILIES:
        emp = pad if frozen else massing(family, pad, lot, rue_edge)
        ex = export_emprise(emp)
        void = (not frozen) and (bool(ex["holes_m"]) or len(ex["parts_m"]) > 1)
        graph = build_graph(family, programme, ex["poly_m"], has_void=void)
        graph["close"] = {
            "poly": ex["poly_m"],
            "holes": [] if frozen else ex["holes_m"],
            "filled": True if frozen else not void,
        }
        result = check(graph)
        if not result.get("ok") and not frozen:
            graph, emp, result = repair_once(graph, emp, family, lot, rue_edge)
            graph["close"] = _close_from_emprise(emp)
            result = check(graph)
            ex = export_emprise(emp)
        svg_rel = f"out/{family}.svg"
        write_parti_svg(graph, result, ex["poly_m"], OUT_DIR / f"{family}.svg")
        options.append(
            {
                "id": family,
                "family": family,
                "graph": graph,
                "emprise": {
                    "poly_m": ex["poly_m"],
                    "holes_m": ex["holes_m"],
                    "parts_m": ex["parts_m"],
                },
                "checker": {
                    "ok": bool(result.get("ok")),
                    "fail": list(result.get("fails") or []),
                },
                "svg": svg_rel,
            }
        )
    return {"options": options}

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: python -m kda_graphe.parti <lot.json>", file=sys.stderr)
        return 2
    out = generate(argv[0])
    dest = OUT_DIR / "parti.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"wrote {dest}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
