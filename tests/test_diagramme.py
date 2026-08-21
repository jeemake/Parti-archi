"""Diagrammes via schéma Graph2Plan + Toolbox plot_graph. Pas de train."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from checker import check  # noqa: E402
from kda_graphe.diagramme import generate, to_item  # noqa: E402

FIX = ROOT / "fixtures"


def test_rayess_diagram_via_toolbox():
    out = generate(FIX / "rayess_parti.json")
    png = ROOT / out["png"]
    assert png.is_file() and png.stat().st_size > 500
    assert out["checker"]["ok"] is True
    g = json.loads((FIX / "rayess_parti.json").read_text(encoding="utf-8"))
    item = to_item(g)
    assert any(a["id"] == "patio" for a in item["air"])
    for name, t in zip(item["names"], item["rType"]):
        if name == "patio":
            raise AssertionError("patio must not be an rType room")
        if name == "sejour":
            assert int(t) == 0  # living
    # patio never mapped to living
    assert all(a["id"] != "sejour" for a in item["air"])


def test_tampon_drawn_and_fail():
    out = generate(FIX / "gao_tampon.json")
    png = ROOT / out["png"]
    assert png.is_file() and png.stat().st_size > 500
    r = check(json.loads((FIX / "gao_tampon.json").read_text(encoding="utf-8")))
    assert r["ok"] is False
    assert out["checker"]["ok"] is False
    assert "rectangle_close" in out["checker"]["fail"] or r["fails"]
