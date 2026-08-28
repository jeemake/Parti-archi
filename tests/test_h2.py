"""H2 — dures tropicales, score troué, poche, shown=3."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from checker import check  # noqa: E402
from kda_graphe.diagramme import generate as gen_diag, phrase_parti  # noqa: E402
from kda_graphe.hybride import generate  # noqa: E402

FIX = ROOT / "fixtures"
TROPICAL = {"cour", "ailes", "cour_services"}


def test_rayess_still_passes_with_tropical_fails():
    g = json.loads((FIX / "rayess_parti.json").read_text(encoding="utf-8"))
    r = check(g)
    assert r["ok"] is True
    assert r["fails"] == []


def test_gao_gains_tropical_fails():
    g = json.loads((FIX / "gao_tampon.json").read_text(encoding="utf-8"))
    r = check(g)
    assert r["ok"] is False
    assert {"rectangle_close", "ch_sde", "patio"} <= set(r["fails"])
    assert {"wing_depth", "no_traversante", "hall_leftover", "service_rue"} & set(r["fails"])


def test_demo_shown_three_tropical_ahead_of_barre():
    out = generate(FIX / "lot_demo.json")
    shown = out["shown"]
    assert len(shown) == 3
    assert [s["rank"] for s in shown] == [1, 2, 3]
    disps = {s["disposition"] for s in shown}
    assert disps & TROPICAL
    assert shown[0]["disposition"] in TROPICAL
    assert shown[0]["disposition"] != "barre"
    for s in shown:
        assert s["checker"]["ok"] is True
        assert s.get("parti")
        assert (ROOT / s["svg"]).is_file()
        text = (ROOT / s["svg"]).read_text(encoding="utf-8", errors="ignore")
        assert "patio=air" in text
        assert "plot_graph Toolbox" not in text
    more = out.get("more") or []
    assert len(more) <= 7


def test_tampon_still_dead_h2():
    out = generate(FIX / "lot_tampon.json")
    assert out["shown"] == []
    assert out["valid_n"] == 0


def test_poche_phrase_on_rayess():
    out = gen_diag(FIX / "rayess_parti.json")
    png = ROOT / out["png"]
    svg = ROOT / out["svg"]
    assert png.is_file() and png.stat().st_size > 400
    text = svg.read_text(encoding="utf-8", errors="ignore")
    assert "patio=air" in text
    assert "plot_graph Toolbox" not in text
    assert phrase_parti("cour")
