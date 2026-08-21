"""Slice 1 — exactement 3 familles, checker importé, tampon jamais ok."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kda_graphe.parti import FAMILIES, generate  # noqa: E402

FIX = ROOT / "fixtures"


def test_three_families_in_order():
    out = generate(FIX / "lot_demo.json")
    ids = [o["id"] for o in out["options"]]
    assert len(out["options"]) == 3
    assert ids == ["cour", "ailes", "barre"] == list(FAMILIES)


def test_ok_never_if_rectangle_close():
    for name in ("lot_demo.json", "lot_tampon.json"):
        out = generate(FIX / name)
        for o in out["options"]:
            fails = o["checker"]["fail"]
            if "rectangle_close" in fails:
                assert o["checker"]["ok"] is False


def test_demo_cour_ailes_ok():
    out = generate(FIX / "lot_demo.json")
    by = {o["id"]: o for o in out["options"]}
    assert by["cour"]["checker"]["ok"] is True
    assert by["ailes"]["checker"]["ok"] is True
    assert by["barre"]["id"] == "barre"
    assert isinstance(by["barre"]["checker"]["fail"], list)


def test_tampon_all_fail():
    out = generate(FIX / "lot_tampon.json")
    assert len(out["options"]) == 3
    need = {"rectangle_close", "patio", "broken_collar"}
    for o in out["options"]:
        assert o["checker"]["ok"] is False
        assert need & set(o["checker"]["fail"])
