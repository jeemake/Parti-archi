# kda-graphe — slice 0

Graphe de pièces + loi en dur + checker. Pas un plan. Pas Finch.

Idris → Kenan · 21 août 2026. Le tampon C-2608-GAO ESQ 20×12 (couloir d'hôtel, CH+SDE, zéro patio-air) est le fail figé. Un L qui remplit encore un rectangle est un refus.

## Où

```
/workspace/kda-graphe/
  checker.py              # lib + CLI
  fixtures/gao_tampon.json
  fixtures/rayess_parti.json
  tests/test_slice0.py
  out/<id>.svg            # bubble, pas un plan
```

La lib CAD (`/home/box/agent-data/workflows/plans-architecturaux/`) n'est pas touchée.

## Run

```
cd /workspace/kda-graphe
python3 -m pip install -r requirements.txt
python3 -m pytest -q
```

Sur cette box (PEP 668), pytest est dans `/workspace/.venv` :

```
/workspace/.venv/bin/pip install -r requirements.txt
/workspace/.venv/bin/pytest -q
```

CLI (JSON sur stdout, SVG dans `out/`, exit 0 toujours — pytest est la gate) :

```
python3 checker.py fixtures/gao_tampon.json
python3 checker.py fixtures/rayess_parti.json
```

`check(graph) → {ok, fails, detail}`. Fails nommés, dans l'ordre : `broken_collar`, `must`, `forbid`, `patio`, `rectangle_close`, `hall_width`, `ch_sde`.

Collier (chemin, pas une adjacence) : `rue → parking → entree_site → porte → galerie → sejour → jardin`. Un hall qui coud porte→sejour n'est pas un maillon.

## Ce qui est encore fake

- Pas de solveur géométrique. `poly` mm est lu et ignoré.
- Pas de DXF. Laki dessine. Slice 0 n'écrit pas de plan.
- Pas de packer, treemap, GAN, Graph2Plan, réseau.
- Les aires « qui matchent » ne sauvent pas un rectangle rempli.
- Slice 1 est le constructeur 3 familles (voir plus bas). Le checker de slice 0 reste la loi.

Stdlib only + pytest. Zéro networkx, zéro réseau de neurones.

## Slice 1 — 3 partis

Lot + programme + reculs → exactement 3 options (`cour`, `ailes`, `barre`), dans cet ordre. Pas un top-k, pas un catalogue, pas un GAN.

```
/workspace/kda-graphe/
  checker.py                  # slice 0 — importé, loi non recopiée
  kda_graphe/
    __init__.py
    parti.py                  # constructeur
    templates/cour.json ailes.json barre.json
  fixtures/lot_demo.json      # lot ouvert (pentagone + reculs)
  fixtures/lot_tampon.json    # 20×12, reculs 0 — fail figé
  tests/test_slice0.py
  tests/test_parti.py
  out/cour.svg ailes.svg barre.svg
  out/parti.json
```

```
cd /workspace/kda-graphe
.venv/bin/python -m kda_graphe.parti fixtures/lot_demo.json
.venv/bin/python -m pytest -q tests/test_slice0.py tests/test_parti.py
```

Sortie : JSON 3 options (graphe + emprise + checker + svg) + bulles. Zéro DXF. Pas de repo GitHub.

Encore fake : slots bulles ≠ murs ; pas de R+1 ; reculs en entrée (pas d’API CU) ; pas de DXF ; pas de GitHub.

## H1 — hybride (Recherche, 100 % algo)

Seeds ≥50 (cour / ailes / barre / cour_services × orientations / miroirs / affectations) → checker slice 0 → score §6 → top 10. `parti.py` intact. Zéro neurone, zéro DXF.

```
cd /workspace/kda-graphe
.venv/bin/python -m kda_graphe.hybride fixtures/lot_demo.json
.venv/bin/python -m pytest -q
```

Sortie : `out/hybride.json` + `out/h01.svg` … `out/h10.svg`. Tampon 20×12 : `shown` vide (meurt par `rectangle_close`).

Encore fake : bulles ≠ murs ; lumière/vent = proxy graphe ; seeds = templates, pas un échantillonneur libre.

## Diagrammes — Graph2Plan schéma + RPLAN-Toolbox

Vendor : `vendor/Graph2plan` et `vendor/RPLAN-Toolbox` (clone, pas un fork produit). Adapter : `kda_graphe/diagramme.py`. Pas de Data.zip, pas de train, pas de poids, pas de Matlab. Retrieval = nos 10 dispositions. patio ≠ living.

```
.venv/bin/python -m kda_graphe.diagramme fixtures/rayess_parti.json
```

`hybride` dessine `out/h01.svg`… via cet adapter (`plot_graph`, pas `plot_fp`).
