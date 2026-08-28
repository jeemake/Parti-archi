#!/usr/bin/env python3
"""H1 — pipeline Recherche : seeds ≥50 → checker dures → score §6 → top 10.

Import checker. Ne détruit pas parti.py. Pas de neurone, pas de DXF.
"""
from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

from shapely import affinity
from shapely.geometry import Polygon, box

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from checker import MUST_PAIRS, check, first_of_type, has_hop
from kda_graphe.diagramme import phrase_parti, render as render_diag
from kda_graphe.parti import (
    DEFAULT_AREA,
    KIND_OF,
    OUT_DIR,
    _add_edge,
    _close_from_emprise,
    _ensure_node,
    _frozen_tampon,
    _poly,
    _rue_vec,
    _tid,
    build_graph,
    buildable,
    export_emprise,
    massing,
    repair_once,
)

DISPOSITIONS = ("cour", "ailes", "barre", "cour_services")
ORIENTS_DEG = (0, 90, 180, 270)
MIRRORS = (False, True)
ASSIGNS = ("base", "vent")

WEIGHTS = {
    "efficacite_surface": 0.25,
    "qualite_adjacences": 0.20,
    "lumiere": 0.20,
    "ventilation": 0.15,
    "compactite": 0.10,
    "simplicite": 0.10,
}


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _origin(coords):
    return _poly(coords).centroid


def _rotate_coords(coords, deg, origin):
    if deg % 360 == 0:
        return [(float(x), float(y)) for x, y in coords]
    r = affinity.rotate(_poly(coords), deg, origin=origin)
    return [(float(x), float(y)) for x, y in r.exterior.coords[:-1]]


def _mirror_coords(coords, origin):
    r = affinity.scale(_poly(coords), xfact=-1, yfact=1, origin=origin)
    return [(float(x), float(y)) for x, y in r.exterior.coords[:-1]]


def massing_cour_services(pad, lot_coords, rue_edge: int):
    """Patio central + cour service (SSK5). Deux trous, pas un pack."""
    base = massing("cour", pad, lot_coords, rue_edge)
    (_, _), _, (nx, ny) = _rue_vec(lot_coords, rue_edge)
    c = pad.centroid
    side = max(2.2, min(4.0, (pad.area ** 0.5) * 0.16))
    cx, cy = c.x + nx * (side * 1.8), c.y + ny * (side * 1.8)
    hole2 = box(cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2)
    out = base.difference(hole2)
    return out if not out.is_empty else base


def _bbox_rect(pad):
    minx, miny, maxx, maxy = pad.bounds
    return box(minx, miny, maxx, maxy)


def _apply_assign(graph: dict, assign: str) -> dict:
    if assign != "vent":
        return graph
    g = deepcopy(graph)
    nodes = {n["id"]: n for n in g["nodes"]}
    for name, kind, area in (
        ("patio", "air", 18),
        ("ext", "site", None),
        ("jardin", "jardin", 50),
        ("chambre", "nuit", 14),
        ("cuisine", "jour", 12),
        ("sam", "jour", 14),
    ):
        _ensure_node(nodes, name)
        if name == "patio":
            nodes[name]["kind"] = "air"
    edges = list(g.get("edges") or [])
    extras = (
        ("sejour", "patio", "vent"),
        ("cuisine", "patio", "vent"),
        ("sam", "jardin", "vent"),
        ("chambre", "jardin", "must_face"),
        ("chambre", "patio", "near"),
    )
    for a, b, rel in extras:
        _add_edge(edges, _tid(nodes, a), _tid(nodes, b), rel, nodes)
    g["nodes"] = list(nodes.values())
    g["edges"] = edges
    return g


def _stamp_cour_services(graph: dict) -> dict:
    g = deepcopy(graph)
    nodes = {n["id"]: n for n in g["nodes"]}
    nodes["cour_service"] = {
        "id": "cour_service",
        "type": "cour_service",
        "kind": "air",
        "area_m2": 9,
    }
    edges = list(g.get("edges") or [])
    for a, b, rel in (
        ("garage", "cour_service", "near"),
        ("local_ge", "cour_service", "near"),
        ("guerite", "cour_service", "near"),
    ):
        _add_edge(edges, _tid(nodes, a), _tid(nodes, b), rel, nodes)
    g["nodes"] = list(nodes.values())
    g["edges"] = edges
    g["id"] = "cour_services"
    return g


def _emprise_for(disp: str, pad, lot_coords, rue_edge: int, frozen: bool, anti: bool):
    if frozen or anti:
        return pad if frozen else _bbox_rect(pad)
    if disp == "cour_services":
        return massing_cour_services(pad, lot_coords, rue_edge)
    return massing(disp, pad, lot_coords, rue_edge)


def score_parts(graph: dict, emp, pad) -> dict:
    """Métriques §6 — proxies graphe + forme. Une note, pas NSGA-II."""
    emp_a = float(emp.area) if emp is not None and not emp.is_empty else 0.0
    pad_a = float(pad.area) if pad is not None and not pad.is_empty else 1.0
    ratio = emp_a / pad_a if pad_a > 0 else 0.0
    # surface : un corps troué / à ailes n'est pas pénalisé ; un plein n'est pas un gain

    held = 0
    for ta, tb in MUST_PAIRS:
        na, nb = first_of_type(graph, ta), first_of_type(graph, tb)
        if na and nb and has_hop(graph, na["id"], nb["id"]):
            held += 1
    adj_q = held / max(len(MUST_PAIRS), 1)

    face = 0
    for e in graph.get("edges") or []:
        if e.get("rel") != "must_face":
            continue
        pair = {e.get("a"), e.get("b")}
        if pair & {"ext", "jardin", "rue", "patio"}:
            face += 1
    lum = _clip01(face / 3.0)

    vents = sum(1 for e in (graph.get("edges") or []) if e.get("rel") == "vent")
    patio = first_of_type(graph, "patio")
    hab = 0
    if patio:
        byid = {n["id"]: n for n in graph.get("nodes") or []}
        for e in graph.get("edges") or []:
            pair = {e.get("a"), e.get("b")}
            if patio["id"] not in pair or e.get("rel") == "forbid":
                continue
            other = next(iter(pair - {patio["id"]}), None)
            nb = byid.get(other or "")
            if nb and nb.get("kind") in {"jour", "nuit"}:
                hab += 1
    vent_s = _clip01((vents + hab + (2 if patio else 0)) / 5.0)

    ex = {"holes_m": [], "parts_m": []}
    try:
        ex = export_emprise(emp)
    except Exception:
        pass
    holed = bool(ex.get("holes_m")) or len(ex.get("parts_m") or []) > 1
    # plein compact = malus ; trous / ailes = bonus (plus de +0.15 qui noie cour)
    if holed:
        compact = 0.92
        eff = 0.88
    else:
        compact = 0.12
        eff = _clip01(0.35 * ratio)

    nparts = len(ex.get("parts_m") or []) or 1
    # 2 parties (ailes) ≠ malus. Un seul rectangle plein = malus.
    if holed and nparts == 1:
        simp = 1.0
    elif nparts == 2:
        simp = 1.0
    elif nparts > 2:
        simp = 0.7
    else:
        simp = 0.22

    pen = 0.0
    if pad is not None and emp is not None and not emp.is_empty:
        try:
            if not pad.buffer(0.08).contains(emp):
                pen += 0.15
        except Exception:
            pen += 0.15

    parts = {
        "efficacite_surface": _clip01(eff),
        "qualite_adjacences": _clip01(adj_q),
        "lumiere": lum,
        "ventilation": vent_s,
        "compactite": compact,
        "simplicite": simp,
        "penalite": round(pen, 4),
    }
    total = sum(WEIGHTS[k] * parts[k] for k in WEIGHTS) - pen
    return {"total": round(_clip01(total), 4), "parts": {k: round(v, 4) for k, v in parts.items()}}


def _make_one(disp, lot_coords, rue_edge, reculs, programme, assign, frozen, anti=False) -> dict:
    pad = buildable(lot_coords, rue_edge, reculs)
    emp = _emprise_for(disp, pad, lot_coords, rue_edge, frozen, anti)
    ex = export_emprise(emp)
    void = (not frozen) and (not anti) and (bool(ex["holes_m"]) or len(ex["parts_m"]) > 1)
    family_tpl = "cour" if disp == "cour_services" else disp
    if anti:
        family_tpl = "barre"
    graph = build_graph(family_tpl, programme, ex["poly_m"], has_void=(not frozen and not anti))
    if disp == "cour_services" and not anti:
        graph = _stamp_cour_services(graph)
    graph = _apply_assign(graph, assign)
    if anti or frozen:
        graph["close"] = {
            "poly": ex["poly_m"] if frozen else list(_bbox_rect(pad).exterior.coords)[:-1],
            "holes": [],
            "filled": True,
        }
        if anti and not frozen:
            emp = _bbox_rect(pad)
            ex = export_emprise(emp)
            graph["close"]["poly"] = ex["poly_m"]
    else:
        graph["close"] = {
            "poly": ex["poly_m"],
            "holes": ex["holes_m"],
            "filled": not void,
        }
    graph["id"] = disp if not anti else "tampon"
    result = check(graph)
    if not result.get("ok") and not frozen and not anti:
        graph, emp, result = repair_once(graph, emp, family_tpl, lot_coords, rue_edge)
        graph["close"] = _close_from_emprise(emp)
        result = check(graph)
        ex = export_emprise(emp)
    sc = score_parts(graph, emp, pad)
    return {
        "disposition": "tampon" if anti else disp,
        "assign": assign,
        "graph": graph,
        "emprise": {
            "poly_m": ex["poly_m"],
            "holes_m": [] if (frozen or anti) else ex["holes_m"],
            "parts_m": ex["parts_m"],
        },
        "checker": {
            "ok": bool(result.get("ok")),
            "fail": list(result.get("fails") or []),
        },
        "score": sc,
        "_emp": emp,
        "_result": result,
    }


def generate(src) -> dict:
    if isinstance(src, (str, Path)):
        data = json.loads(Path(src).read_text(encoding="utf-8"))
    else:
        data = src
    lot = data["lot"]["poly_m"]
    rue_edge = int(data["lot"].get("rue_edge") or 0)
    reculs = data.get("reculs_m") or {"rue": 5, "voisins": 3}
    programme = data.get("programme") or []
    frozen = _frozen_tampon(lot, reculs)
    origin = _origin(lot)

    candidates = []
    for disp in DISPOSITIONS:
        for deg in ORIENTS_DEG:
            for mir in MIRRORS:
                for assign in ASSIGNS:
                    coords = _rotate_coords(lot, deg, origin)
                    if mir:
                        coords = _mirror_coords(coords, origin)
                    c = _make_one(
                        disp, coords, rue_edge, reculs, programme, assign, frozen, anti=False
                    )
                    c["orient_deg"] = deg
                    c["mirror"] = mir
                    candidates.append(c)
    if not frozen:
        for deg in ORIENTS_DEG:
            coords = _rotate_coords(lot, deg, origin)
            c = _make_one(
                "tampon", coords, rue_edge, reculs, programme, "base", frozen, anti=True
            )
            c["orient_deg"] = deg
            c["mirror"] = False
            candidates.append(c)

    valid = [c for c in candidates if c["checker"]["ok"]]
    valid.sort(key=lambda c: (-c["score"]["total"], c["disposition"]))
    k = min(3, len(valid))
    shown_raw = valid[:k]
    more_raw = valid[k:k + 7]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    shown = []
    for i, c in enumerate(shown_raw, 1):
        svg_rel = f"out/h{i:02d}.svg"
        phrase = phrase_parti(c["disposition"], c["graph"])
        render_diag(
            c["graph"],
            OUT_DIR / f"h{i:02d}.svg",
            emprise=c["emprise"],
            result=c["_result"],
            disposition=c["disposition"],
            phrase=phrase,
        )
        shown.append(
            {
                "rank": i,
                "disposition": c["disposition"],
                "parti": phrase,
                "graph": c["graph"],
                "emprise": {
                    "poly_m": c["emprise"]["poly_m"],
                    "holes_m": c["emprise"]["holes_m"],
                },
                "checker": c["checker"],
                "score": c["score"],
                "svg": svg_rel,
            }
        )
    more = []
    for j, c in enumerate(more_raw, k + 1):
        more.append(
            {
                "rank": j,
                "disposition": c["disposition"],
                "parti": phrase_parti(c["disposition"], c["graph"]),
                "checker": c["checker"],
                "score": {"total": c["score"]["total"]},
            }
        )
    return {
        "candidates_n": len(candidates),
        "valid_n": len(valid),
        "shown": shown,
        "more": more,
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: python -m kda_graphe.hybride <lot.json>", file=sys.stderr)
        return 2
    out = generate(argv[0])
    dest = OUT_DIR / "hybride.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    slim = {
        "candidates_n": out["candidates_n"],
        "valid_n": out["valid_n"],
        "shown": [
            {
                "rank": s["rank"],
                "disposition": s["disposition"],
                "checker": s["checker"],
                "score": s["score"],
                "svg": s["svg"],
                "parti": s.get("parti"),
                "holes_n": len((s.get("emprise") or {}).get("holes_m") or []),
            }
            for s in out["shown"]
        ],
        "more": out.get("more") or [],
    }
    print(json.dumps(slim, ensure_ascii=False, indent=2))
    print(f"wrote {dest}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
