#!/usr/bin/env python3
"""Adapter diagramme : graphe KDA + emprise → item Graph2Plan → RPLAN-Toolbox plot_graph.

Pas de Data.zip, pas de data.mat, pas de train, pas de poids, pas de Matlab, pas de plot_fp.
Retrieval = nos 10 dispositions. patio ≠ living.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VENDOR_TB = ROOT / "vendor" / "RPLAN-Toolbox"
if str(VENDOR_TB) not in sys.path:
    sys.path.insert(0, str(VENDOR_TB))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rplan.plot import get_axes, get_figure, plot_graph  # noqa: E402

from checker import check  # noqa: E402

OUT_DIR = ROOT / "out"

# Graph2Plan / RPLAN rType (utils.room_label). patio is NEVER 0 (LivingRoom).
RTYPE = {
    "sejour": 0,
    "sam": 4,
    "cuisine": 2,
    "chambre": 1,
    "sdb": 3,
    "cellier": 11,
    "galerie": 10,
    "porte": 10,
    "entree_site": 10,
    "garage": 11,
    "local_ge": 11,
    "guerite": 11,
    "parking": 13,
    "jardin": 9,
    "ext": 13,
    "rue": 13,
    "hall": 12,
    "degagement": 12,
    "ch_sde": 1,
}
AIR_TYPES = frozenset({"patio", "cour_service", "cour_services"})

# Retrieval : 10 dispositions KDA (centres unitaires). Pas data.mat.
SLOTS = {
    "cour": {
        "patio": (0.50, 0.50),
        "sejour": (0.50, 0.72),
        "sam": (0.68, 0.58),
        "cuisine": (0.72, 0.40),
        "cellier": (0.82, 0.32),
        "galerie": (0.32, 0.58),
        "porte": (0.22, 0.42),
        "chambre": (0.28, 0.28),
        "sdb": (0.40, 0.22),
        "guerite": (0.12, 0.22),
        "garage": (0.12, 0.38),
        "local_ge": (0.12, 0.52),
        "jardin": (0.50, 0.90),
        "parking": (0.12, 0.08),
        "entree_site": (0.22, 0.28),
        "rue": (0.12, 0.00),
    },
    "ailes": {
        "patio": (0.50, 0.50),
        "sejour": (0.50, 0.28),
        "sam": (0.32, 0.28),
        "cuisine": (0.18, 0.28),
        "cellier": (0.12, 0.40),
        "galerie": (0.50, 0.42),
        "porte": (0.50, 0.12),
        "chambre": (0.82, 0.55),
        "sdb": (0.82, 0.70),
        "guerite": (0.18, 0.12),
        "garage": (0.08, 0.12),
        "local_ge": (0.08, 0.28),
        "jardin": (0.50, 0.88),
        "parking": (0.22, 0.06),
        "entree_site": (0.38, 0.10),
        "rue": (0.22, 0.00),
    },
    "barre": {
        "sejour": (0.38, 0.55),
        "sam": (0.22, 0.55),
        "cuisine": (0.12, 0.55),
        "cellier": (0.12, 0.38),
        "galerie": (0.50, 0.55),
        "porte": (0.50, 0.22),
        "chambre": (0.72, 0.55),
        "sdb": (0.84, 0.55),
        "guerite": (0.12, 0.18),
        "garage": (0.22, 0.18),
        "local_ge": (0.32, 0.18),
        "jardin": (0.50, 0.88),
        "parking": (0.22, 0.06),
        "entree_site": (0.38, 0.12),
        "rue": (0.22, 0.00),
        "patio": (0.50, 0.72),
    },
    "cour_services": {
        "patio": (0.48, 0.52),
        "cour_service": (0.22, 0.28),
        "sejour": (0.55, 0.72),
        "sam": (0.70, 0.58),
        "cuisine": (0.74, 0.40),
        "cellier": (0.82, 0.32),
        "galerie": (0.38, 0.58),
        "porte": (0.28, 0.42),
        "chambre": (0.70, 0.28),
        "sdb": (0.82, 0.22),
        "guerite": (0.12, 0.18),
        "garage": (0.12, 0.38),
        "local_ge": (0.12, 0.52),
        "jardin": (0.50, 0.90),
        "parking": (0.12, 0.06),
        "entree_site": (0.22, 0.28),
        "rue": (0.12, 0.00),
    },
    "tampon": {
        "sejour": (0.35, 0.40),
        "sam": (0.55, 0.40),
        "cuisine": (0.72, 0.40),
        "hall": (0.50, 0.55),
        "chambre": (0.30, 0.72),
        "sdb": (0.45, 0.72),
        "ch_sde": (0.30, 0.72),
        "porte": (0.50, 0.22),
        "garage": (0.18, 0.22),
        "local_ge": (0.18, 0.38),
        "jardin": (0.50, 0.88),
        "parking": (0.22, 0.08),
        "entree_site": (0.38, 0.16),
        "rue": (0.22, 0.00),
    },
    "noyau": {"sejour": (0.50, 0.50), "porte": (0.50, 0.20)},
    "jour_nuit": {"sejour": (0.40, 0.40), "chambre": (0.70, 0.70), "porte": (0.40, 0.18)},
    "duplex": {"sejour": (0.40, 0.35), "chambre": (0.70, 0.65), "porte": (0.40, 0.16)},
    "barres": {"sejour": (0.30, 0.50), "chambre": (0.70, 0.50), "porte": (0.50, 0.18)},
    "atrium": {"sejour": (0.50, 0.35), "patio": (0.50, 0.55), "porte": (0.50, 0.14)},
}
SLOTS["ailes_cour"] = SLOTS["ailes"]
SLOTS["rayess"] = SLOTS["ailes"]
SLOTS["rayess_parti"] = SLOTS["ailes"]
SLOTS["gao_tampon"] = SLOTS["tampon"]


def retrieve(name: str) -> dict:
    """Cherche dans nos 10 dispositions. Jamais data.mat / Data.zip."""
    key = (name or "").lower().replace("-", "_")
    if key in SLOTS:
        return SLOTS[key]
    for k, v in SLOTS.items():
        if k in key:
            return v
    return SLOTS["cour"]


def _close_poly(graph: dict, emprise: dict | None):
    if emprise and emprise.get("poly_m"):
        return list(emprise["poly_m"]), list(emprise.get("holes_m") or [])
    close = graph.get("close") or {}
    if close.get("poly"):
        return list(close["poly"]), list(close.get("holes") or close.get("holes_m") or [])
    w = float(close.get("w_m") or 24)
    h = float(close.get("h_m") or 16)
    return [[0.0, 0.0], [w, 0.0], [w, h], [0.0, h]], []


def _boundary(coords, size=256, margin=16):
    pts = np.asarray(coords, dtype=float)
    minx, miny = pts.min(axis=0)
    maxx, maxy = pts.max(axis=0)
    sx = (size - 2 * margin) / max(maxx - minx, 1e-6)
    sy = (size - 2 * margin) / max(maxy - miny, 1e-6)
    s = min(sx, sy)
    xy = (pts - np.array([minx, miny])) * s + margin
    n = len(xy)
    out = np.zeros((n, 4), dtype=float)
    for i in range(n):
        a, b = xy[i], xy[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        if abs(dx) >= abs(dy):
            d = 0 if dx >= 0 else 2
        else:
            d = 1 if dy >= 0 else 3
        out[i] = [a[0], a[1], d, 0]
    return out, (float(minx), float(miny), float(s), float(margin))


def _map_type(node: dict) -> int | None:
    typ = node.get("type") or node.get("id")
    if typ in AIR_TYPES or node.get("kind") == "air":
        return None
    if typ in RTYPE:
        return RTYPE[typ]
    kind = node.get("kind")
    if kind == "nuit":
        return 1
    if kind == "jour":
        return 0
    if kind == "service":
        return 11
    if kind == "seuil":
        return 10
    if kind in {"site", "jardin"}:
        return 13 if kind == "site" else 9
    return 11


def to_item(graph: dict, emprise: dict | None = None, disposition: str | None = None) -> dict:
    """KDA → schéma Graph2Plan (boundary, rType, rEdge, gtBox). patio = air, pas living."""
    disp = disposition or graph.get("id") or (graph.get("close") or {}).get("shape") or "cour"
    slots = retrieve(disp)
    coords, holes = _close_poly(graph, emprise)
    boundary, xform = _boundary(coords)
    minx, miny, scale, margin = xform

    nodes = list(graph.get("nodes") or [])
    rooms, airs = [], []
    for n in nodes:
        typ = n.get("type") or n.get("id")
        if typ in AIR_TYPES or n.get("kind") == "air":
            airs.append(n)
            continue
        if _map_type(n) is None:
            airs.append(n)
            continue
        rooms.append(n)

    boxes = []
    types = []
    names = []
    for n in rooms:
        typ = n.get("type") or n.get("id")
        cx, cy = slots.get(typ) or slots.get(n.get("id"), (0.5, 0.5))
        area = float(n.get("area_m2") or 10)
        side = max(14.0, min(48.0, (area ** 0.5) * 4.2))
        px = margin + cx * (256 - 2 * margin)
        py = margin + cy * (256 - 2 * margin)
        boxes.append([px - side / 2, py - side / 2, px + side / 2, py + side / 2])
        types.append(int(_map_type(n)))
        names.append(n.get("id") or typ)

    air_boxes = []
    for n in airs:
        typ = n.get("type") or n.get("id")
        cx, cy = slots.get(typ) or slots.get(n.get("id"), (0.5, 0.5))
        px = margin + cx * (256 - 2 * margin)
        py = margin + cy * (256 - 2 * margin)
        air_boxes.append({"id": n.get("id") or typ, "xy": (px, py), "kind": n.get("kind") or "air"})

    idx = {n.get("id"): i for i, n in enumerate(rooms)}
    edges = []
    for e in graph.get("edges") or []:
        a, b = e.get("a"), e.get("b")
        if a in idx and b in idx:
            edges.append([idx[a], idx[b], 0])

    holes_px = []
    for h in holes:
        hp = np.asarray(h, dtype=float)
        holes_px.append(((hp - np.array([minx, miny])) * scale + margin).tolist())

    return {
        "boundary": boundary,
        "rType": np.asarray(types, dtype=int) if types else np.zeros((0,), dtype=int),
        "rEdge": np.asarray(edges, dtype=int) if edges else np.zeros((0, 3), dtype=int),
        "gtBox": np.asarray(boxes, dtype=float) if boxes else np.zeros((0, 4), dtype=float),
        "names": names,
        "air": air_boxes,
        "holes_px": holes_px,
        "disposition": disp,
        "id": graph.get("id") or disp,
    }


def render(graph: dict, dest: Path, emprise: dict | None = None, result: dict | None = None, disposition: str | None = None) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    item = to_item(graph, emprise=emprise, disposition=disposition)
    if result is None:
        result = check(graph)
    fails = result.get("fails") or result.get("fail") or []
    ok = bool(result.get("ok"))
    title = f"{item['id']} · OK" if ok else f"{item['id']} · FAIL: {', '.join(fails)}"

    fig = get_figure(size=640, tight_layout=False)
    fig.patch.set_facecolor("#f7f3ea")
    ax = get_axes(size=640, xlim=[-8, 264], ylim=[-8, 264], fig=fig)
    ax.set_facecolor("#f7f3ea")
    boxes = item["gtBox"]
    types = item["rType"]
    edges = item["rEdge"]
    if len(boxes) == 0:
        boxes = np.array([[100.0, 100.0, 140.0, 140.0]])
        types = np.array([11])
        edges = np.zeros((0, 3), dtype=int)
    plot_graph(item["boundary"], boxes, types, edges, wall_thickness=5, with_boundary=True, ax=ax)

    for h in item["holes_px"]:
        if len(h) >= 3:
            poly = np.asarray(h)
            ax.fill(poly[:, 0], poly[:, 1], fc="#f7f3ea", ec="#319795", lw=1.6, ls="--", zorder=3)
    for a in item["air"]:
        x, y = a["xy"]
        ax.plot(x, y, "o", mec="#319795", mfc="none", mew=2.2, ms=22, zorder=4)
        ax.text(x, y + 14, a["id"], fontsize=8, ha="center", color="#319795", zorder=5)

    ax.set_title(title, fontsize=11, loc="left", pad=8)
    fig = ax.figure
    fig.text(
        0.04,
        0.02,
        "diagramme · schéma Graph2Plan · plot_graph Toolbox · patio=air · pas un plan",
        fontsize=8,
        color="#718096",
    )
    fig.savefig(dest, dpi=120, facecolor="#f7f3ea")
    plt.close(fig)
    return dest


def generate(src) -> dict:
    if isinstance(src, (str, Path)):
        data = json.loads(Path(src).read_text(encoding="utf-8"))
        stem = Path(src).stem
    else:
        data = src
        stem = data.get("id") or "diag"
    if "nodes" not in data:
        raise SystemExit("diagramme.py attend un graphe (nodes/edges), pas un lot")
    result = check(data)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    png = OUT_DIR / f"{data.get('id') or stem}_diag.png"
    svg = OUT_DIR / f"{data.get('id') or stem}_diag.svg"
    render(data, png, result=result)
    render(data, svg, result=result)
    return {"png": str(png.relative_to(ROOT)), "svg": str(svg.relative_to(ROOT)), "checker": {"ok": result["ok"], "fail": result["fails"]}}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: python -m kda_graphe.diagramme <graph.json>", file=sys.stderr)
        return 2
    out = generate(argv[0])
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
