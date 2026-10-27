#!/usr/bin/env python3
"""Parse EIA RECS 2020 'Highlights for space heating fuel in U.S. homes by state' (pdftotext -layout)
into data/heat_fuel.json: share of homes by main heating fuel, and the most common one per state.
Source: https://www.eia.gov/consumption/residential/data/2020/state/pdf/State%20Space%20Heating%20Fuels.pdf"""
import json, re, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
txt = (ROOT / "data/raw/recs2020_state_space_heating_fuels.txt").read_text()
txt = txt.split("Relative standard errors")[0]
names = {s["name"]: s["abbr"] for s in json.loads((ROOT / "data/prices.json").read_text())["states"]}
out = {}
for line in txt.splitlines():
    m = re.match(r"^([A-Z][A-Za-z .]+?)\s{2,}(.*)$", line.strip())
    if not m or m.group(1) not in names: continue
    t = m.group(2).split()
    if len(t) != 9: raise SystemExit(f"bad row: {line}")
    pct = lambda v: 0 if v in ("Q", "N") else int(v.rstrip("%"))
    sh = {"elec": pct(t[2]), "gas": pct(t[4]), "propane": pct(t[6]), "oil": pct(t[8])}
    out[names[m.group(1)]] = {"shares": sh, "main": max(sh, key=sh.get)}
assert len(out) == 51, len(out)
(ROOT / "data/heat_fuel.json").write_text(json.dumps(out, indent=1))
from collections import Counter; print(Counter(v["main"] for v in out.values()), {k: v["main"] for k, v in out.items() if v["main"] in ("oil", "propane")})
