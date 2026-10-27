#!/usr/bin/env python3
"""Parse EIA + NOAA downloads in data/raw into data/prices.json (no API keys).
Re-download raw files with: ./fetch_data.sh"""
import json, re, csv, pathlib, statistics
import pandas as pd
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

STATES = [("AL","Alabama"),("AK","Alaska"),("AZ","Arizona"),("AR","Arkansas"),("CA","California"),("CO","Colorado"),("CT","Connecticut"),
("DE","Delaware"),("DC","District of Columbia"),("FL","Florida"),("GA","Georgia"),("HI","Hawaii"),("ID","Idaho"),("IL","Illinois"),("IN","Indiana"),
("IA","Iowa"),("KS","Kansas"),("KY","Kentucky"),("LA","Louisiana"),("ME","Maine"),("MD","Maryland"),("MA","Massachusetts"),("MI","Michigan"),
("MN","Minnesota"),("MS","Mississippi"),("MO","Missouri"),("MT","Montana"),("NE","Nebraska"),("NV","Nevada"),("NH","New Hampshire"),("NJ","New Jersey"),
("NM","New Mexico"),("NY","New York"),("NC","North Carolina"),("ND","North Dakota"),("OH","Ohio"),("OK","Oklahoma"),("OR","Oregon"),("PA","Pennsylvania"),
("RI","Rhode Island"),("SC","South Carolina"),("SD","South Dakota"),("TN","Tennessee"),("TX","Texas"),("UT","Utah"),("VT","Vermont"),("VA","Virginia"),
("WA","Washington"),("WV","West Virginia"),("WI","Wisconsin"),("WY","Wyoming")]
# PADD regions used by EIA SHOPP (fallback when a state has no weekly price)
PADD = {**{s:"New England (PADD 1A)" for s in "CT ME MA NH RI VT".split()},
        **{s:"Central Atlantic (PADD 1B)" for s in "DE DC MD NJ NY PA".split()},
        **{s:"Lower Atlantic (PADD 1C)" for s in "FL GA NC SC VA WV".split()},
        **{s:"Midwest (PADD 2)" for s in "IL IN IA KS KY MI MN MO NE ND SD OH OK TN WI".split()},
        **{s:"Gulf Coast (PADD 3)" for s in "AL AR LA MS NM TX".split()},
        **{s:"Rocky Mountain (PADD 4)" for s in "CO ID MT UT WY".split()},
        **{s:"West Coast (PADD 5)" for s in "AK AZ CA HI NV OR WA".split()}}
NOAA = {n: i+1 for i, n in enumerate([x for _, x in STATES if x not in ("Alaska","District of Columbia","Hawaii")])}
NOAA["Alaska"] = 50

def elec():
    x = pd.read_excel(RAW / "table_5_06_b.xlsx", header=None)
    label = str(x.iloc[3, 1]).strip()  # e.g. "August 2026 YTD"
    out = {}
    for _, r in x.iterrows():
        n = str(r[0]).strip()
        if n in dict((b, a) for a, b in STATES):
            out[n] = float(r[1])
    return out, label

def gas():
    d = pd.read_excel(RAW / "NG_PRI_SUM_A_EPG0_PRS_DMCF_M.xls", sheet_name="Data 1", header=2)
    w = d[(d.Date >= "2025-11-01") & (d.Date <= "2026-03-31")]
    out = {}
    for c in d.columns[1:]:
        n = c.split(" Price of Natural Gas")[0]
        v = w[c].dropna()
        if len(v): out[n] = (round(float(v.mean()), 2), len(v))
    return out

def shopp(fname):
    d = pd.read_excel(RAW / fname, sheet_name="Data 1", header=2)
    last = d.iloc[-1]; date = last["Date"].strftime("%Y-%m-%d")
    out = {}
    for c in d.columns[1:]:
        n = re.sub(r"^(Weekly |U\.S\. )+", "", c)
        n = re.split(r"\s*(?:No\. 2|Propane)", n)[0].strip() or "U.S."
        if n.startswith("No. 2") or n == "": n = "U.S."
        if n == "PADD 2": n = "Midwest (PADD 2)"
        if pd.notna(last[c]): out[n] = float(last[c])
    return out, date

def hdd():
    rows = {}
    for line in open(RAW / "hddcst.txt"):
        code, el, yr = int(line[0:3]), line[4:6], int(line[6:10])
        vals = [float(v) for v in line[10:].split()]
        if el == "25" and 1991 <= yr <= 2020 and min(vals) >= 0:
            rows.setdefault(code, []).append(sum(vals))
    out = {n: (round(statistics.mean(rows[c])), "NOAA nClimDiv statewide heating degree days, 1991–2020 average") for n, c in NOAA.items() if c in rows}
    st = {"Hawaii": "USW00022521", "District of Columbia": "USW00013743", "Alaska": "USW00026451"}
    for n, sid in st.items():
        r = list(csv.DictReader(open(RAW / f"normals_{sid}.csv")))[0]
        out[n] = (round(float(r["ANN-HTDD-NORMAL"])), "NOAA 1991–2020 station normal, " + {"Hawaii": "Honolulu airport", "District of Columbia": "Washington Reagan airport", "Alaska": "Anchorage airport"}[n])
    return out

e, elabel = elec(); g = gas(); oil, odate = shopp("PET_PRI_WFR_A_EPD2F_PRS_DPGAL_W.xls"); pro, pdate = shopp("PET_PRI_WFR_A_EPLLPA_PRS_DPGAL_W.xls"); h = hdd()
states = []
for ab, n in STATES:
    def pick(tab):
        if n in tab: return tab[n], "state"
        if PADD[ab] in tab: return tab[PADD[ab]], PADD[ab]
        return tab["U.S."], "U.S. average"
    o, osrc = pick(oil); p, psrc = pick(pro)
    gm = g.get(n) or g["U.S."]
    states.append({"abbr": ab, "name": n, "slug": n.lower().replace(" ", "-"),
                   "elec": e[n], "gas_mcf": gm[0], "gas_therm": round(gm[0] / 10.36, 3), "gas_src": "state" if n in g else "U.S. average",
                   "oil": o, "oil_src": osrc, "propane": p, "propane_src": psrc, "hdd": h[n][0], "hdd_src": h[n][1]})
meta = {"elec_label": f"Residential average, January–August 2026 ({elabel})", "elec_us": e.get("U.S. Total"),
        "gas_label": "Residential average of monthly prices, November 2025–March 2026 (last heating season)", "gas_us": g["U.S."][0],
        "oil_date": odate, "propane_date": pdate, "oil_us": oil["U.S."], "propane_us": pro["U.S."]}
x = pd.read_excel(RAW / "table_5_06_b.xlsx", header=None)
for _, r in x.iterrows():
    if str(r[0]).strip() == "U.S. Total": meta["elec_us"] = float(r[1])
json.dump({"meta": meta, "states": states}, open(ROOT / "data" / "prices.json", "w"), indent=1)
print(meta); print(len(states))
for s in states: print(s["abbr"], s["elec"], s["gas_therm"], s["gas_src"], s["oil"], s["oil_src"], s["propane"], s["propane_src"], s["hdd"])
