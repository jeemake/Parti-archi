"""H1 — ≥50 seeds, checker importé, score §6, tampon mort par la forme."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kda_graphe.hybride import generate  # noqa: E402
from kda_graphe.parti import FAMILIES  # noqa: E402

FIX = ROOT / "fixtures"


def test_candidates_at_least_50():
    out = generate(FIX / "lot_demo.json")
    assert out["candidates_n"] >= 50


def test_demo_shown_ok_ranked():
    out = generate(FIX / "lot_demo.json")
    shown = out["shown"]
    assert shown, "lot_demo must yield at least one ok candidate"
    assert 1 <= len(shown) <= 20
    ranks = [s["rank"] for s in shown]
    assert ranks == list(range(1, len(shown) + 1))
    for s in shown:
        assert s["checker"]["ok"] is True
        assert s["checker"]["fail"] == []
        assert "total" in s["score"]
        assert s["svg"].startswith("out/h")
        assert (ROOT / s["svg"]).is_file()
    totals = [s["score"]["total"] for s in shown]
    assert totals == sorted(totals, reverse=True)


def test_tampon_shown_dead_by_form():
    out = generate(FIX / "lot_tampon.json")
    assert out["candidates_n"] >= 50
    if not out["shown"]:
        assert out["valid_n"] == 0
        return
    for s in out["shown"]:
        assert s["checker"]["ok"] is False
        assert "rectangle_close" in s["checker"]["fail"]


def test_parti_families_untouched():
    assert list(FAMILIES) == ["cour", "ailes", "barre"]
