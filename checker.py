#!/usr/bin/env python3
"""KDA graphe d'adjacences — slice 0.

Graphe de pièces + loi en dur + checker. Pas de solveur géométrique,
pas de DXF, pas de packer. `poly` mm est lu et ignoré.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Loi — constantes du checker, jamais lues depuis le fixture.
COLLAR = ["rue", "parking", "entree_site", "porte", "galerie", "sejour", "jardin"]

MUST_PAIRS = [
    ("cuisine", "sam"),
    ("sam", "sejour"),
    ("cuisine", "cellier"),
    ("sdb", "chambre"),
    ("guerite", "rue"),
    ("sejour", "patio"),
]

SEJOUR_JARDIN_RELS = frozenset({"must", "must_face", "vent"})


CHAMBRE_TYPES = frozenset({"chambre", "ch_sde"})
HALL_TYPES = frozenset({"hall", "degagement"})
EXTERIOR_TYPES = frozenset({"ext", "rue", "jardin"})
EXTERIOR_KINDS = frozenset({"air", "jardin", "site"})
EXTERIOR_KIND_TYPES = frozenset({"patio", "jardin", "ext", "rue"})
HABITABLE_KINDS = frozenset({"jour", "nuit"})
FAIL_ORDER = [
    "broken_collar",
    "must",
    "forbid",
    "patio",
    "rectangle_close",
    "hall_width",
    "ch_sde",
    "wing_depth",
    "no_traversante",
    "hall_leftover",
    "service_rue",
]

TRAVERSE_TYPES = frozenset({"ext", "jardin", "patio", "galerie"})
TRAVERSE_KINDS = frozenset({"air", "jardin"})
WET_OR_STORE = frozenset({"sdb", "cellier", "ch_sde"})
SERVICE_ON_RUE = frozenset({"guerite", "local_ge", "garage"})
RUE_PATH = frozenset({"rue", "parking", "entree_site"})


def _nodes(graph: dict) -> list[dict]:
    return list(graph.get("nodes") or [])


def _by_id(graph: dict) -> dict[str, dict]:
    return {n["id"]: n for n in _nodes(graph) if n.get("id")}


def first_of_type(graph: dict, typ: str) -> dict | None:
    for n in _nodes(graph):
        if n.get("type") == typ:
            return n
    return None


def find_named(graph: dict, name: str) -> dict | None:
    """Collar lookup: type d'abord, sinon id."""
    hit = first_of_type(graph, name)
    if hit is not None:
        return hit
    for n in _nodes(graph):
        if n.get("id") == name:
            return n
    return None


def _edges(graph: dict) -> list[dict]:
    return list(graph.get("edges") or [])


def adjacency(graph: dict) -> dict[str, list[tuple[str, str]]]:
    adj: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for e in _edges(graph):
        a, b = e.get("a"), e.get("b")
        rel = e.get("rel") or "near"
        if not a or not b or a == b:
            continue
        adj[a].append((b, rel))
        adj[b].append((a, rel))
    return adj


def edges_between(graph: dict, a_id: str, b_id: str) -> list[str]:
    rels = []
    for e in _edges(graph):
        pair = {e.get("a"), e.get("b")}
        if pair == {a_id, b_id}:
            rels.append(e.get("rel") or "near")
    return rels


def has_hop(graph: dict, a_id: str, b_id: str) -> bool:
    """Direct adjacency, any rel except forbid. Hall does not count as a hop."""
    for rel in edges_between(graph, a_id, b_id):
        if rel != "forbid":
            return True
    return False


def is_exterior(node: dict) -> bool:
    t = node.get("type")
    k = node.get("kind")
    if t in EXTERIOR_TYPES:
        return True
    if k in EXTERIOR_KINDS and t in EXTERIOR_KIND_TYPES:
        return True
    return False



def _is_chambre_side(node: dict) -> bool:
    return node.get("type") in CHAMBRE_TYPES


def _fail_collar(graph: dict) -> list[str]:
    detail = []
    found: list[dict | None] = []
    for name in COLLAR:
        n = find_named(graph, name)
        found.append(n)
        if n is None:
            detail.append(f"nœud collier manquant : {name}")
    for i in range(len(COLLAR) - 1):
        a_name, b_name = COLLAR[i], COLLAR[i + 1]
        a, b = found[i], found[i + 1]
        if a is None or b is None:
            detail.append(f"maillon manquant : {a_name} → {b_name}")
            continue
        if not has_hop(graph, a["id"], b["id"]):
            detail.append(
                f"maillon manquant : {a_name} → {b_name} "
                f"(pas d'arête directe ; un hall/dégagement ne compte pas)"
            )
    return detail


def _fail_must(graph: dict) -> list[str]:
    detail = []
    adj = adjacency(graph)
    byid = _by_id(graph)

    for ta, tb in MUST_PAIRS:
        na, nb = first_of_type(graph, ta), first_of_type(graph, tb)
        if na is None or nb is None:
            missing = []
            if na is None:
                missing.append(ta)
            if nb is None:
                missing.append(tb)
            detail.append(
                f"must cassé : {ta}–{tb} (type manquant : {', '.join(missing)})"
            )
            continue
        if not has_hop(graph, na["id"], nb["id"]):
            detail.append(f"must cassé : {ta}–{tb} (pas d'arête)")

    sejour = first_of_type(graph, "sejour")
    jardin = first_of_type(graph, "jardin")
    if sejour is None or jardin is None:
        detail.append("must cassé : sejour–jardin (type manquant)")
    else:
        rels = edges_between(graph, sejour["id"], jardin["id"])
        if not any(r in SEJOUR_JARDIN_RELS for r in rels):
            detail.append(
                "must cassé : sejour–jardin (besoin must | must_face | vent)"
            )

    cuisine = first_of_type(graph, "cuisine")
    if cuisine is None:
        detail.append("must cassé : cuisine must_face ext (cuisine manquante)")
    else:
        faced = False
        for nb_id, rel in adj.get(cuisine["id"], []):
            if rel == "forbid":
                continue
            nb = byid.get(nb_id)
            if nb is None:
                continue
            if is_exterior(nb):
                faced = True
                break
        if not faced:
            detail.append(
                "must cassé : cuisine must_face ext "
                "(besoin d'une arête vers ext/rue/jardin/patio)"
            )
    return detail


def _fail_forbid(graph: dict) -> list[str]:
    byid = _by_id(graph)
    detail = []
    for e in _edges(graph):
        a, b = byid.get(e.get("a")), byid.get(e.get("b"))
        if a is None or b is None:
            continue
        ta, tb = a.get("type"), b.get("type")
        pair = {ta, tb}

        if "garage" in pair and (
            _is_chambre_side(a) or _is_chambre_side(b)
        ):
            other = a if a.get("type") != "garage" else b
            detail.append(
                f"forbid : garage–{other.get('id')} "
                f"(type {other.get('type')} compte comme chambre)"
            )
        if "local_ge" in pair and (
            _is_chambre_side(a) or _is_chambre_side(b)
        ):
            other = a if a.get("type") != "local_ge" else b
            detail.append(
                f"forbid : local_ge–{other.get('id')} "
                f"(type {other.get('type')} compte comme chambre)"
            )
        if pair == {"sdb", "sejour"}:
            detail.append(
                f"forbid : sdb–sejour (porte / arête {e.get('rel')!r} sur le séjour)"
            )
    return detail


def _fail_patio(graph: dict) -> list[str]:
    detail = []
    patios = [n for n in _nodes(graph) if n.get("type") == "patio"]
    adj = adjacency(graph)
    byid = _by_id(graph)
    if not patios:
        detail.append("patio absent")
        return detail
    for p in patios:
        if p.get("kind") != "air":
            detail.append(
                f"patio {p.get('id')!r} kind={p.get('kind')!r}, doit être air"
            )
    good = False
    for p in patios:
        hab = set()
        for nb_id, rel in adj.get(p["id"], []):
            if rel == "forbid":
                continue
            nb = byid.get(nb_id)
            if nb and nb.get("kind") in HABITABLE_KINDS:
                hab.add(nb_id)
        if len(hab) >= 2:
            good = True
    if not good:
        detail.append(
            "aucun patio n'a ≥2 voisins habitables (kind jour|nuit ; "
            "galerie/seuil ne comptent pas)"
        )
    return detail


def _has_opening_air(graph: dict) -> bool:
    adj = adjacency(graph)
    byid = _by_id(graph)
    for n in _nodes(graph):
        if n.get("type") != "patio" or n.get("kind") != "air":
            continue
        for nb_id, rel in adj.get(n["id"], []):
            if rel == "forbid":
                continue
            nb = byid.get(nb_id)
            if nb and nb.get("kind") == "jour":
                return True
    return False


def _as_pts(poly) -> list[tuple[float, float]]:
    if not poly:
        return []
    pts = [(float(p[0]), float(p[1])) for p in poly]
    if pts[0] != pts[-1]:
        pts = pts + [pts[0]]
    return pts


def _shoelace(pts: list[tuple[float, float]]) -> float:
    a = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def _poly_is_rectangle(poly, tol: float = 1.0) -> bool:
    """Predicate on a ring. Not a solver: area(poly) == area(bbox) and 4 corners."""
    pts = _as_pts(poly)
    if len(pts) < 5:
        return False
    corners: list[tuple[float, float]] = []
    for x, y in pts[:-1]:
        if not any(abs(x - a) <= tol and abs(y - b) <= tol for a, b in corners):
            corners.append((x, y))
    if len(corners) != 4:
        return False
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    bb = (max(xs) - min(xs)) * (max(ys) - min(ys))
    if bb <= 0:
        return False
    return abs(_shoelace(pts) - bb) <= max(tol, 0.001 * bb)


def _indoor_nodes(graph: dict) -> list[dict]:
    return [
        n
        for n in _nodes(graph)
        if n.get("kind") in {"jour", "nuit", "circulation", "seuil", "service"}
    ]


def _indoor_polys_tile_rectangle(graph: dict, tol: float = 1.0) -> bool:
    polys = [n.get("poly") for n in _indoor_nodes(graph) if n.get("poly")]
    if len(polys) < 2 or not all(_poly_is_rectangle(p) for p in polys):
        return False
    areas = 0.0
    minx = miny = 1e18
    maxx = maxy = -1e18
    for poly in polys:
        pts = _as_pts(poly)
        areas += _shoelace(pts)
        xs = [c[0] for c in pts]
        ys = [c[1] for c in pts]
        minx, maxx = min(minx, min(xs)), max(maxx, max(xs))
        miny, maxy = min(miny, min(ys)), max(maxy, max(ys))
    bb = (maxx - minx) * (maxy - miny)
    if bb <= 0:
        return False
    return abs(areas - bb) <= max(tol, 0.02 * bb)


def _close_is_rectangle(close: dict, graph: dict) -> bool:
    """Read the form. shape=rectangle is optional, never required."""
    if _poly_is_rectangle(close.get("poly")):
        return True
    try:
        w = float(close["w_m"]) if close.get("w_m") is not None else 0.0
        h = float(close["h_m"]) if close.get("h_m") is not None else 0.0
    except (TypeError, ValueError, KeyError):
        w = h = 0.0
    if w > 0 and h > 0:
        return True
    if _indoor_polys_tile_rectangle(graph):
        return True
    return close.get("shape") == "rectangle"


def _fail_rectangle_close(graph: dict) -> list[str]:
    close = graph.get("close") or {}
    holes = close.get("holes") or close.get("holes_m") or []
    if holes:
        return []
    if close.get("filled") is False:
        return []
    if not _close_is_rectangle(close, graph):
        return []
    return [
        "close rectangle rempli sans trou dans la forme "
        "(poly / w×h / dallage ; un nœud patio n'ouvre pas un pavé) — "
        "fail même si les aires matchent"
    ]



def _fail_hall_width(graph: dict) -> list[str]:
    detail = []
    for n in _nodes(graph):
        if n.get("type") not in HALL_TYPES:
            continue
        w = n.get("width_m")
        if w is None:
            continue
        try:
            wf = float(w)
        except (TypeError, ValueError):
            continue
        if wf > 2.00:
            detail.append(
                f"{n.get('type')} {n.get('id')!r} width_m={wf} > 2.00 "
                f"(galerie/patio exempts)"
            )
    return detail


def _fail_ch_sde(graph: dict) -> list[str]:
    detail = []
    for n in _nodes(graph):
        if n.get("type") == "ch_sde":
            detail.append(f"nœud {n.get('id')!r} type=ch_sde (CH+SDE fusionnés)")
    return detail



def _faces_air(graph: dict, node_id: str) -> set[str]:
    adj = adjacency(graph)
    byid = _by_id(graph)
    faces: set[str] = set()
    for nb_id, rel in adj.get(node_id, []):
        if rel == "forbid":
            continue
        nb = byid.get(nb_id)
        if not nb:
            continue
        if nb.get("type") in TRAVERSE_TYPES or nb.get("kind") in TRAVERSE_KINDS:
            faces.add(nb["id"])
    return faces


def _close_wh_m(close: dict, graph: dict) -> tuple[float, float]:
    poly = close.get("poly")
    if poly and len(poly) >= 4:
        xs = [float(p[0]) for p in poly]
        ys = [float(p[1]) for p in poly]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        if w > 500 or h > 500:  # mm model
            w, h = w / 1000.0, h / 1000.0
        return w, h
    try:
        w = float(close["w_m"]) if close.get("w_m") is not None else 0.0
        h = float(close["h_m"]) if close.get("h_m") is not None else 0.0
    except (TypeError, ValueError, KeyError):
        w = h = 0.0
    return w, h


def _fail_wing_depth(graph: dict) -> list[str]:
    close = graph.get("close") or {}
    holes = close.get("holes") or close.get("holes_m") or []
    if holes:
        return []
    if close.get("filled") is False:
        return []
    w, h = _close_wh_m(close, graph)
    if w <= 0 or h <= 0:
        return []
    depth = min(w, h)
    if depth <= 8.0:
        return []
    if not _close_is_rectangle(close, graph):
        return []
    return [
        f"corps rempli profond {depth:.1f} m > 8 m "
        "sans patio/galerie qui le perce"
    ]


def _fail_no_traversante(graph: dict) -> list[str]:
    """Séjour : 2 faces. Autres jour/nuit (hors cellier/sdb) : au moins 1 face air.
    Rayess (séjour patio+jardin) passe ; un tampon sans patio meurt."""
    detail = []
    for n in _nodes(graph):
        typ = n.get("type")
        if typ in WET_OR_STORE:
            continue
        if n.get("kind") not in HABITABLE_KINDS and typ not in {
            "sejour",
            "sam",
            "cuisine",
            "chambre",
        }:
            continue
        faces = _faces_air(graph, n["id"])
        if typ == "sejour" and len(faces) < 2:
            detail.append(
                f"sejour {n.get('id')!r} sans deux faces "
                "(ext/jardin/patio/galerie)"
            )
        elif typ in {"sam", "cuisine", "chambre"} and len(faces) < 1:
            detail.append(f"{typ} {n.get('id')!r} sans face air (dead-end)")
    return detail


def _fail_hall_leftover(graph: dict) -> list[str]:
    detail = []
    for n in _nodes(graph):
        if n.get("type") not in HALL_TYPES:
            continue
        wide = False
        fat = False
        try:
            if n.get("width_m") is not None and float(n["width_m"]) > 2.00:
                wide = True
        except (TypeError, ValueError):
            pass
        try:
            if n.get("area_m2") is not None and float(n["area_m2"]) > 12.0:
                fat = True
        except (TypeError, ValueError):
            pass
        if wide or fat:
            detail.append(
                f"{n.get('type')} {n.get('id')!r} leftover "
                f"(width>2.00 ou area>12 ; galerie/patio exempts)"
            )
    return detail


def _fail_service_rue(graph: dict) -> list[str]:
    detail = []
    byid = _by_id(graph)
    adj = adjacency(graph)
    for n in _nodes(graph):
        if n.get("type") not in SERVICE_ON_RUE:
            continue
        ok = False
        for nb_id, rel in adj.get(n["id"], []):
            if rel == "forbid":
                continue
            nb = byid.get(nb_id)
            if nb and (nb.get("type") in RUE_PATH or nb.get("id") in RUE_PATH):
                ok = True
                break
        if not ok:
            detail.append(
                f"{n.get('type')} {n.get('id')!r} pas sur le chemin rue→entrée"
            )
    return detail


def check(graph: dict[str, Any]) -> dict[str, Any]:
    """Return {ok, fails, detail}. ok iff fails is empty. Fails in LAW order."""
    checkers = {
        "broken_collar": _fail_collar,
        "must": _fail_must,
        "forbid": _fail_forbid,
        "patio": _fail_patio,
        "rectangle_close": _fail_rectangle_close,
        "hall_width": _fail_hall_width,
        "ch_sde": _fail_ch_sde,
        "wing_depth": _fail_wing_depth,
        "no_traversante": _fail_no_traversante,
        "hall_leftover": _fail_hall_leftover,
        "service_rue": _fail_service_rue,
    }
    detail: dict[str, list[str]] = {}
    fails: list[str] = []
    for name in FAIL_ORDER:
        msgs = checkers[name](graph)
        if msgs:
            fails.append(name)
            detail[name] = msgs
    return {"ok": len(fails) == 0, "fails": fails, "detail": detail}


# --- SVG bubble (not a plan) -------------------------------------------------

KIND_FILL = {
    "site": "#4a5568",
    "service": "#c05621",
    "seuil": "#2b6cb0",
    "jour": "#276749",
    "air": "#319795",
    "nuit": "#6b46c1",
    "jardin": "#38a169",
    "circulation": "#c53030",
}

KIND_ROW = ["site", "service", "seuil", "jour", "air", "nuit", "jardin", "circulation"]


def _xml(s: Any) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_svg(graph: dict, result: dict, path: str | Path) -> Path:
    """Bubble diagram: collar left→right, extras by kind, failed hops dashed red."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    gid = graph.get("id") or "graphe"
    fails = result.get("fails") or []
    title = f"{gid} · OK" if result.get("ok") else f"{gid} · FAIL: {', '.join(fails)}"

    width, height = 960, 460
    collar_y = 130
    r = 28
    n_col = len(COLLAR)
    x0, x1 = 70, 890
    collar_xy: dict[str, tuple[float, float]] = {}
    collar_nodes: list[tuple[str, dict | None]] = []
    for i, name in enumerate(COLLAR):
        x = x0 + (x1 - x0) * i / (n_col - 1)
        n = find_named(graph, name)
        collar_xy[name] = (x, collar_y)
        collar_nodes.append((name, n))

    used_ids = {n["id"] for _, n in collar_nodes if n is not None}
    extras: dict[str, list[dict]] = defaultdict(list)
    for n in _nodes(graph):
        if n["id"] in used_ids:
            continue
        extras[n.get("kind") or "other"].append(n)

    extra_xy: dict[str, tuple[float, float]] = {}
    y_row = 280
    x_cursor = 70
    row_h = 90
    for kind in KIND_ROW + [k for k in extras if k not in KIND_ROW]:
        for n in extras.get(kind, []):
            if x_cursor > 890:
                x_cursor = 70
                y_row += row_h
            extra_xy[n["id"]] = (x_cursor, y_row)
            x_cursor += 95
        if extras.get(kind):
            x_cursor += 20

    pos: dict[str, tuple[float, float]] = dict(extra_xy)
    for name, n in collar_nodes:
        if n is not None:
            pos[n["id"]] = collar_xy[name]

    broken_hops: set[frozenset] = set()
    for i in range(len(COLLAR) - 1):
        a_name, b_name = COLLAR[i], COLLAR[i + 1]
        a, b = find_named(graph, a_name), find_named(graph, b_name)
        if a is None or b is None or not has_hop(graph, a["id"], b["id"]):
            broken_hops.add(frozenset({a_name, b_name}))

    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f7f3ea"/>',
        f'<text x="24" y="36" font-family="ui-sans-serif, system-ui, sans-serif" '
        f'font-size="18" font-weight="700" fill="#1a202c">{_xml(title)}</text>',
        '<text x="24" y="58" font-family="ui-sans-serif, system-ui, sans-serif" '
        'font-size="12" fill="#718096">bubble · collier rue→jardin · pas un plan</text>',
    ]

    # Failed collar hops first (under nodes).
    for i in range(len(COLLAR) - 1):
        a_name, b_name = COLLAR[i], COLLAR[i + 1]
        x_a, y_a = collar_xy[a_name]
        x_b, y_b = collar_xy[b_name]
        if frozenset({a_name, b_name}) in broken_hops:
            parts.append(
                f'<line x1="{x_a}" y1="{y_a}" x2="{x_b}" y2="{y_b}" '
                f'stroke="#c53030" stroke-width="3" stroke-dasharray="8 6" '
                f'stroke-linecap="round"/>'
            )

    # Real edges.
    seen_pairs: set[frozenset] = set()
    for e in _edges(graph):
        a, b = e.get("a"), e.get("b")
        if a not in pos or b not in pos:
            continue
        key = frozenset({a, b})
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        x_a, y_a = pos[a]
        x_b, y_b = pos[b]
        rel = e.get("rel") or "near"
        if rel == "forbid":
            stroke, dash, sw = "#c53030", "4 4", 2
        else:
            stroke, dash, sw = "#a0aec0", "", 1.6
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        parts.append(
            f'<line x1="{x_a}" y1="{y_a}" x2="{x_b}" y2="{y_b}" '
            f'stroke="{stroke}" stroke-width="{sw}"{dash_attr}/>'
        )

    def draw_node(n: dict | None, name: str, xy: tuple[float, float], ghost: bool) -> None:
        x, y = xy
        if ghost or n is None:
            parts.append(
                f'<circle cx="{x}" cy="{y}" r="{r}" fill="#edf2f7" '
                f'stroke="#c53030" stroke-width="2" stroke-dasharray="5 4"/>'
            )
            parts.append(
                f'<text x="{x}" y="{y + 4}" text-anchor="middle" '
                f'font-family="ui-sans-serif, system-ui, sans-serif" font-size="10" '
                f'fill="#c53030">{_xml(name)}</text>'
            )
            return
        fill = KIND_FILL.get(n.get("kind") or "", "#718096")
        parts.append(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" '
            f'stroke="#1a202c" stroke-width="1.4"/>'
        )
        label = n.get("type") or n.get("id") or name
        parts.append(
            f'<text x="{x}" y="{y + 4}" text-anchor="middle" '
            f'font-family="ui-sans-serif, system-ui, sans-serif" font-size="10" '
            f'fill="#fff" font-weight="600">{_xml(label)}</text>'
        )

    for name, n in collar_nodes:
        draw_node(n, name, collar_xy[name], ghost=n is None)

    for n in _nodes(graph):
        if n["id"] in extra_xy:
            draw_node(n, n.get("type") or n["id"], extra_xy[n["id"]], ghost=False)

    parts.append(
        '<text x="24" y="440" font-family="ui-sans-serif, system-ui, sans-serif" '
        'font-size="11" fill="#718096">slice 0 · graphe seul · poly ignoré</text>'
    )
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return path


def load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: python3 checker.py <graph.json>", file=sys.stderr)
        return 0
    graph_path = Path(argv[0])
    graph = load(graph_path)
    result = check(graph)
    out_dir = Path.cwd() / "out"
    # Prefer package out/ when launched from the package root.
    pkg_out = Path(__file__).resolve().parent / "out"
    if Path.cwd().resolve() == Path(__file__).resolve().parent:
        out_dir = pkg_out
    elif pkg_out.exists():
        out_dir = pkg_out
    out_dir.mkdir(parents=True, exist_ok=True)
    svg_path = out_dir / f"{graph.get('id', graph_path.stem)}.svg"
    write_svg(graph, result, svg_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
