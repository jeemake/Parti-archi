"""Slice 0 — GAO tampon rouge, Rayess-parti vert, aucun rectangle packé ok."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from checker import check, write_svg  # noqa: E402

FIXTURES = ROOT / "fixtures"
OUT = ROOT / "out"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_gao_tampon_fails():
    r = check(_load("gao_tampon.json"))
    assert r["ok"] is False
    assert {"broken_collar", "patio", "rectangle_close", "ch_sde"} <= set(r["fails"])


def test_rayess_parti_passes():
    r = check(_load("rayess_parti.json"))
    assert r["ok"] is True
    assert r["fails"] == []


def test_svg_writes():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("gao_tampon.json", "rayess_parti.json"):
        g = _load(name)
        dest = OUT / f"{g['id']}.svg"
        write_svg(g, check(g), dest)
        text = dest.read_text(encoding="utf-8")
        assert dest.stat().st_size > 0
        assert "svg" in text


def _packed_nodes_edges():
    nodes = [
        {"id": "rue", "kind": "site", "type": "rue"},
        {"id": "parking", "kind": "site", "type": "parking"},
        {"id": "entree_site", "kind": "site", "type": "entree_site"},
        {"id": "porte", "kind": "seuil", "type": "porte"},
        {"id": "galerie", "kind": "seuil", "type": "galerie"},
        {"id": "sejour", "kind": "jour", "type": "sejour"},
        {"id": "jardin", "kind": "jardin", "type": "jardin"},
        {"id": "sam", "kind": "jour", "type": "sam"},
        {"id": "cuisine", "kind": "jour", "type": "cuisine"},
        {"id": "cellier", "kind": "jour", "type": "cellier"},
        {"id": "guerite", "kind": "service", "type": "guerite"},
        {"id": "sdb", "kind": "nuit", "type": "sdb"},
        {"id": "chambre", "kind": "nuit", "type": "chambre"},
        {"id": "ext", "kind": "site", "type": "ext"},
        {"id": "garage", "kind": "service", "type": "garage"},
        {"id": "local_ge", "kind": "service", "type": "local_ge"},
    ]
    edges = [
        {"a": "rue", "b": "parking", "rel": "must"},
        {"a": "parking", "b": "entree_site", "rel": "must"},
        {"a": "entree_site", "b": "porte", "rel": "must"},
        {"a": "porte", "b": "galerie", "rel": "must"},
        {"a": "galerie", "b": "sejour", "rel": "must"},
        {"a": "sejour", "b": "jardin", "rel": "must_face"},
        {"a": "cuisine", "b": "sam", "rel": "must"},
        {"a": "sam", "b": "sejour", "rel": "must"},
        {"a": "cuisine", "b": "cellier", "rel": "must"},
        {"a": "cuisine", "b": "ext", "rel": "must_face"},
        {"a": "sdb", "b": "chambre", "rel": "must"},
        {"a": "guerite", "b": "rue", "rel": "must"},
        {"a": "garage", "b": "rue", "rel": "near"},
        {"a": "local_ge", "b": "rue", "rel": "near"},
    ]
    return nodes, edges


def test_packed_rectangle_never_ok():
    """No packed rectangle is ok — even with a complete collar + musts.
    No shape=rectangle flag: form is a 20×12 poly."""
    nodes, edges = _packed_nodes_edges()
    g = {
        "id": "packed_rect",
        "close": {
            "poly": [[0, 0], [20000, 0], [20000, 12000], [0, 12000]],
            "filled": True,
        },
        "nodes": nodes,
        "edges": edges,
    }
    assert "shape" not in g["close"]
    r = check(g)
    assert r["ok"] is False
    assert "rectangle_close" in r["fails"]


def test_tampon_sans_flag():
    """w×h filled, no shape key — still rectangle_close."""
    nodes, edges = _packed_nodes_edges()
    g = {
        "id": "tampon_sans_flag",
        "close": {"w_m": 20, "h_m": 12, "filled": True},
        "nodes": nodes,
        "edges": edges,
    }
    assert "shape" not in g["close"]
    r = check(g)
    assert r["ok"] is False
    assert "rectangle_close" in r["fails"]
