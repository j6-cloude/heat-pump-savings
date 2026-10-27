#!/usr/bin/env python3
"""Static site generator for Heat Pump Savings Check.
Usage: BASE_URL=https://j6-cloude.github.io/heat-pump-savings python3 src/build.py  -> writes ./public
Data: python3 src/build_data.py (parses EIA/NOAA downloads in data/raw into data/prices.json)
"""
import os, json, html, shutil, re, pathlib, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "public"
BASE = os.environ.get("BASE_URL", "https://j6-cloude.github.io/heat-pump-savings").rstrip("/")
PREFIX = urllib.parse.urlparse(BASE).path.rstrip("/")   # "/heat-pump-savings" on GitHub Pages project sites
SITE = "Heat Pump Savings Check"
TAGLINE = "Free calculator: will a heat pump cost less than your oil, propane, gas or electric heat? State prices from EIA"
AUTHOR = os.environ.get("AUTHOR_NAME", "j6")
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "liu04731@gmail.com")
UPDATED = "2026-10-28"; UPDATED_H = "October 28, 2026"
GOOGLE_VERIFY = os.environ.get("GOOGLE_SITE_VERIFICATION", ""); BING_VERIFY = os.environ.get("BING_SITE_VERIFICATION", "")
VERIFY_META = (f'<meta name="google-site-verification" content="{GOOGLE_VERIFY}">\n' if GOOGLE_VERIFY else "") + \
              (f'<meta name="msvalidate.01" content="{BING_VERIFY}">\n' if BING_VERIFY else "")
INDEXNOW_KEY = (ROOT / ".indexnow_key").read_text().strip()
DATA = json.loads((ROOT / "data" / "prices.json").read_text())
META, STATES = DATA["meta"], DATA["states"]
BY = {s["abbr"]: s for s in STATES}
# most common main heating fuel per state (EIA RECS 2020; src/build_heatfuel.py) -> calculator default on state pages
HEATFUEL = json.loads((ROOT / "data" / "heat_fuel.json").read_text())
for _s in STATES: _s["main_fuel"] = HEATFUEL[_s["abbr"]]["main"]; _s["fuel_shares"] = HEATFUEL[_s["abbr"]]["shares"]
LOW_NEED = 2e6   # Btu/yr of delivered heat; below this we say "little heating needed" instead of showing $0 rows (Hawaii: 0 HDD)
def low(r): return r["need"] < LOW_NEED
LOWTXT = "Little heating needed"

def u(p): return PREFIX + p

# ---------- calculator (mirrors assets/calc.js) ----------
BTU = {"oil": 138500, "propane": 91452, "gas": 100000, "elec": 3412}
UNIT = {"oil": "gallons", "propane": "gallons", "gas": "therms", "elec": "kWh"}
EFF = {"oil": 83, "propane": 90, "gas": 90, "elec": 100}
FAC = {"tight": 3, "avg": 4, "leaky": 5.5}
FNAME = {"oil": "Heating oil", "propane": "Propane", "gas": "Natural gas", "elec": "Electric baseboard"}
def climate(hdd): return 1.05 if hdd < 3000 else 1.0 if hdd < 5000 else 0.9 if hdd < 7000 else 0.8
def fprice(s, f): return {"oil": s["oil"], "propane": s["propane"], "gas": s["gas_therm"], "elec": s["elec"] / 100}[f]
def calc(state, fuel, sqft=2000, ins="avg", hspf2=8.5, cop=0, eff=None, mode="size", amount=0, fuel_price=None, elec_price=None):
    s = BY[state]; eff = eff or EFF[fuel]
    fp = fprice(s, fuel) if fuel_price is None else fuel_price
    ep = s["elec"] / 100 if elec_price is None else elec_price
    need = amount * BTU[fuel] * eff / 100 if mode == "usage" else sqft * s["hdd"] * FAC[ins]
    c = cop if cop > 0 else hspf2 / 3.412 * climate(s["hdd"])
    units = need / (BTU[fuel] * eff / 100); now = units * fp
    kwh = need / 3412 / c; hp = kwh * ep
    return {"need": need, "cop": c, "units": units, "now": now, "kwh": kwh, "hp": hp, "save": now - hp,
            "per_now": fp / (BTU[fuel] * eff / 100) * 1e6, "per_hp": ep / (3412 * c) * 1e6,
            "breakeven": fp / (BTU[fuel] * eff / 100) * 3412 * c}

def money(x): return ("-" if x < 0 else "") + "${:,.0f}".format(abs(x))
def diff(x): return f"{money(abs(x))} less" if x >= 0 else f"{money(abs(x))} more"
def cost_cells(r, be=True):
    """table cells: now / heat pump / difference (/ break-even); a single note when the climate needs almost no heat"""
    if low(r): return f'<td colspan="{4 if be else 3}"><em>{LOWTXT}</em> ({"warm climate: heating costs are close to $0" if r["now"] < 50 else "warm climate: about " + money(r["now"]) + " a year either way"})</td>'
    return f"<td>{money(r['now'])}</td><td>{money(r['hp'])}</td><td>{diff(r['save'])}</td>" + (f"<td>${r['breakeven']:.3f}</td>" if be else "")
def strip(s): return re.sub(r"<[^>]+>", "", s)

# ---------- sources (all opened and checked Oct 27, 2026) ----------
S_EPM = ("EIA Electric Power Monthly, Table 5.6.B: residential electricity price by state, year to date", "https://www.eia.gov/electricity/monthly/epm_table_grapher.php?t=epmt_5_6_b")
S_NG = ("EIA: Natural gas prices by state (residential, monthly)", "https://www.eia.gov/dnav/ng/ng_pri_sum_a_EPG0_PRS_DMcf_m.htm")
S_SHOPP = ("EIA Heating Oil and Propane Update (weekly residential prices)", "https://www.eia.gov/petroleum/heatingoilpropane/")
S_WFO = ("EIA Winter Fuels Outlook, October 2026", "https://www.eia.gov/outlooks/steo/report/perspectives/2026/10-winterfuels/article.php")
S_BTU = ("EIA: British thermal units (Btu) and fuel heat content", "https://www.eia.gov/energyexplained/units-and-calculators/british-thermal-units.php")
S_HDD = ("NOAA NCEI Climate at a Glance / nClimDiv statewide degree days", "https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/")
S_NORM = ("NOAA U.S. Climate Normals 1991–2020", "https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals")
S_IRSFAQ = ("IRS: FAQs on changes to 25C, 25D and other credits under the One Big Beautiful Bill (P.L. 119-21)", "https://www.irs.gov/newsroom/faqs-for-modification-of-sections-25c-25d-25e-30c-30d-45l-45w-and-179d-under-public-law-119-21-139-stat-72-july-4-2025-commonly-known-as-the-one-big-beautiful-bill-obbb")
S_25C = ("IRS: Energy Efficient Home Improvement Credit (25C)", "https://www.irs.gov/credits-deductions/energy-efficient-home-improvement-credit")
S_DOE = ("U.S. Department of Energy: Home Energy Rebates program", "https://www.energy.gov/scep/home-energy-rebates-programs")
S_PN262 = ("DOE Home Energy Rebates Program Notice 26-2 (HEAR/HEEHR changes)", "https://www.energy.gov/documents/program-notice-26-2")
S_NASEO = ("NASEO: Home Energy Rebates FAQ, September 2026", "https://www.naseo.org/Data/Sites/1/media/tknaseo/home-energy-rebates-faq-september-2026.pdf")
S_ESHEAR = ("ENERGY STAR: State and Tribal rebate programs (HEAR)", "https://www.energystar.gov/partner-resources/state-and-tribal-rebate-programs/hear-program")
S_ESASHP = ("ENERGY STAR: Air-source heat pumps", "https://www.energystar.gov/products/air_source_heat_pumps")
S_ESMINI = ("ENERGY STAR: Ductless heating and cooling (mini-splits)", "https://www.energystar.gov/products/ductless_heating_cooling")
S_NEEP = ("NEEP: Cold-climate air-source heat pump product list", "https://neep.org/heating-electrification/ccashp-specification-product-list")
S_AHRI = ("AHRI Directory of certified product performance", "https://www.ahridirectory.org/")
S_RECS = ("EIA Residential Energy Consumption Survey (RECS) 2020: main space heating fuel by state", "https://www.eia.gov/consumption/residential/data/2020/state/pdf/State%20Space%20Heating%20Fuels.pdf")
PRICE_SRC = [S_EPM, S_NG, S_SHOPP, S_WFO, S_BTU, S_HDD]

# ---------- layout ----------
NAV = [("/", "Calculator"), ("/states/", "By state"), ("/heat-pump-rebates-2026/", "Rebates 2026"), ("/heat-pump-cost/", "Payback"), ("/methodology/", "How it works")]
LOGO = '<svg class="logo" viewBox="0 0 32 32" width="30" height="30" aria-hidden="true"><rect width="32" height="32" rx="9" fill="#c8551f"/><path d="M16 7c3 4 6 6 6 11a6 6 0 0 1-12 0c0-3 2-5 3-7 1 2 2 3 3 3-1-3-1-5 0-7z" fill="#fff"/></svg>'
NEXT = {
 "/": ("/heat-pump-rebates-2026/", "See what rebates are left in 2026", "The 25C tax credit ended. Here is what you can still get."),
 "/heat-pump-rebates-2026/": ("/heat-pump-cost/", "Work out your payback", "Put in your quote and rebates. See how many years it takes."),
 "/heat-pump-cost/": ("/mini-split-size-calculator/", "Check what size you need", "A rough size so you can compare quotes."),
 "/mini-split-size-calculator/": ("/heat-pump-rebates-2026/", "Find rebates before you buy", "Check your state and utility before you sign."),
 "/heat-pump-tax-credit-2026/": ("/heat-pump-rebates-2026/", "See rebates that still exist", "State, utility and DOE rebates in one place."),
}
DEFAULT_NEXT = ("/", "Run your own numbers", "Pick your state and fuel. It takes 30 seconds.")
ORG = {"@type": "Organization", "@id": BASE + "/#org", "name": SITE, "url": BASE + "/", "description": TAGLINE, "email": CONTACT_EMAIL}
INDEP = "Independent free tool. Not affiliated with any government agency, utility or heat pump manufacturer."

def faq_ld(faqs):
    return {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": html.unescape(strip(a))}} for q, a in faqs]}
def faq_html(faqs): return '<section id="faq"><h2>Questions people ask</h2>' + "".join(f"<h3>{q}</h3><p>{a}</p>" for q, a in faqs) + "</section>"

PAGES = []
def page(path, title, desc, body, ld=None, faqs=None, h1=None, sources=None, hero=None, crumbs=None, scripts=False, og="/assets/og/og.png", og_alt=None):
    url = BASE + path
    og_alt = og_alt or f"{SITE}: free heat pump savings calculator with EIA prices for all 50 states"
    graph = [ORG, {"@type": "WebSite", "@id": BASE + "/#site", "url": BASE + "/", "name": SITE, "publisher": {"@id": BASE + "/#org"}},
             {"@type": "WebPage", "@id": url, "url": url, "name": title, "description": desc, "dateModified": UPDATED, "inLanguage": "en-US",
              "isPartOf": {"@id": BASE + "/#site"}, "author": {"@type": "Person", "name": AUTHOR, "url": BASE + "/about/"}}]
    if path != "/":
        items = [("Home", "/")] + (crumbs or []) + [(h1 or title, path)]
        graph.append({"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": BASE + p} for i, (n, p) in enumerate(items)]})
    if ld: graph += ld if isinstance(ld, list) else [ld]
    if faqs: graph.append(faq_ld(faqs)); body += faq_html(faqs)
    if sources:
        body += '<section class="sources"><h2>Sources</h2><ul>' + "".join(f'<li><a href="{x}" rel="noopener">{t}</a></li>' for t, x in sources) + "</ul></section>"
    nx = NEXT.get(path, DEFAULT_NEXT)
    if nx[0] == path: nx = ("/heat-pump-rebates-2026/", "See 2026 rebates", "What is left after the 25C tax credit ended.")
    body += f'<aside class="next" aria-label="Next step"><div class="lbl">Next step</div><a class="btn" href="{u(nx[0])}">{nx[1]} <span aria-hidden="true">&rarr;</span></a><p>{nx[2]}</p></aside>'
    nav = "".join(f'<a href="{u(h)}"{" aria-current=page" if h == path else ""}>{t}</a>' for h, t in NAV)
    js = f'<script src="{u("/assets/prices.js")}"></script><script src="{u("/assets/calc.js")}" defer></script>' if scripts else ""
    doc = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<meta name="author" content="{AUTHOR}">
<meta property="og:type" content="website"><meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}"><meta property="og:url" content="{url}"><meta property="og:site_name" content="{SITE}">
<meta property="og:image" content="{BASE}{og}"><meta property="og:image:type" content="image/png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="{html.escape(og_alt)}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{html.escape(title)}"><meta name="twitter:description" content="{html.escape(desc)}"><meta name="twitter:image" content="{BASE}{og}"><meta name="twitter:image:alt" content="{html.escape(og_alt)}"><meta name="theme-color" content="#c8551f">
{VERIFY_META}<link rel="alternate" type="text/plain" title="llms.txt" href="{u('/llms.txt')}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='9' fill='%23c8551f'/%3E%3C/svg%3E">
<link rel="stylesheet" href="{u('/assets/style.css')}">
<!-- AdSense placeholder: no ad code yet. Paste the approved adsbygoogle.js tag here only after approval. -->
<script type="application/ld+json">{json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)}</script>
{js}
</head><body>
<header><a class="brand" href="{u('/')}">{LOGO}<span>{SITE}</span></a><nav aria-label="Main">{nav}</nav></header>
<p class="indep">{INDEP} Prices from the U.S. Energy Information Administration (EIA).</p>
<main>
{hero or f'<h1>{h1 or title}</h1>'}
<p class="meta">By <a href="{u('/about/')}">{AUTHOR}</a> · Updated <time datetime="{UPDATED}">{UPDATED_H}</time> · Prices from EIA (dates on each page) · Estimates, not quotes</p>
{body}
<div class="ad-slot" data-ad-slot="bottom" aria-hidden="true"></div>
</main>
<footer><p><a href="{u('/about/')}">About</a> · <a href="{u('/contact/')}">Contact</a> · <a href="{u('/privacy/')}">Privacy</a> · <a href="{u('/disclaimer/')}">Disclaimer</a> · <a href="{u('/sources/')}">Sources</a> · <a href="{u('/sitemap.xml')}">Sitemap</a> · <a href="{u('/llms.txt')}">llms.txt</a></p>
<p>{SITE} is an independent tool by {AUTHOR}. It is not affiliated with the EIA, IRS, Department of Energy, ENERGY STAR, any state energy office, any utility, or any heat pump maker or installer. Numbers are estimates for planning, not quotes or advice.</p></footer>
</body></html>"""
    d = OUT / path.strip("/"); d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(doc)
    PAGES.append((path, title, desc, strip(body)))

# ---------- calculator widget ----------
def calc_form(state="MA", fuel="oil", title="Your numbers"):
    return f"""<form class="card hp-calc" data-state="{state}" data-fuel="{fuel}" onsubmit="return false" aria-label="Heat pump savings calculator">
<h2 style="margin-top:0">{title}</h2>
<div class="grid">
<label>Your state<select name="state"></select></label>
<label>How you heat now<select name="fuel"><option value="oil">Heating oil</option><option value="propane">Propane</option><option value="gas">Natural gas</option><option value="elec">Electric baseboard or furnace</option></select></label>
</div>
<div class="lbl" style="margin-top:1rem">How much heat does your home need?</div>
<div class="seg" role="radiogroup"><label><input type="radio" name="mode" value="size" checked> Use home size</label><label><input type="radio" name="mode" value="usage"> I know last winter's fuel use</label></div>
<div class="grid m-size"><label>Home size (sq ft)<input name="sqft" type="number" inputmode="numeric" min="200" max="20000" value="2000"></label>
<label>Insulation<select name="ins"><option value="tight">Good (newer or upgraded)</option><option value="avg" selected>Average</option><option value="leaky">Drafty (older, little insulation)</option></select></label></div>
<div class="grid m-usage" hidden><label><span>Fuel used in a year (<span class="unit">gallons</span>)</span><input name="amount" type="number" inputmode="decimal" min="0" value="700"><span class="hint">From your bills or delivery slips, for heating only.</span></label></div>
<details class="adv" open><summary>Prices and heat pump (prefilled for your state)</summary>
<div class="grid">
<label><span>Fuel price ($ <span class="punit">per gallon</span>)</span><input name="fuelPrice" type="number" inputmode="decimal" step="any" min="0"></label>
<label>Electricity price ($ per kWh)<input name="elecPrice" type="number" inputmode="decimal" step="any" min="0"></label>
<label>Current system efficiency (%)<input name="eff" type="number" inputmode="numeric" min="40" max="100"><span class="hint">Oil 83, gas/propane 90 by default. Older systems: try 75–80.</span></label>
<label>Heat pump HSPF2<input name="hspf2" type="number" inputmode="decimal" step="0.1" min="5" max="14" value="8.5"><span class="hint">On the spec sheet or AHRI certificate.</span></label>
<label>Or enter COP (optional)<input name="cop" type="number" inputmode="decimal" step="0.1" min="0" max="6" placeholder="auto"><span class="hint">Leave blank to estimate from HSPF2 and your climate.</span></label>
</div></details>
<div class="out" aria-live="polite"><p class="verdict"></p><div class="big"></div><p class="sentence"></p>
<div class="kpis"><div class="kpi"><span>Now, per year</span><b class="k-now"></b></div><div class="kpi"><span>Heat pump, per year</span><b class="k-hp"></b></div>
<div class="kpi"><span>Fuel you'd stop buying</span><b class="k-units"></b></div><div class="kpi"><span>Extra electricity</span><b class="k-kwh"></b></div>
<div class="kpi"><span>Heat pump COP used</span><b class="k-cop"></b></div><div class="kpi"><span>Break-even power price</span><b class="k-be"></b></div>
<div class="kpi"><span>Cost per million Btu of heat (now vs heat pump)</span><b class="k-per"></b></div><div class="kpi"><span>Heat needed per year</span><b class="k-need"></b></div></div>
<p class="small">Break-even: if your electricity costs less than this per kWh, the heat pump is cheaper to run. Running cost only; it does not include buying or installing the system.</p></div>
<section class="share" hidden aria-label="Share your result"><h3>Share your result</h3>
<p class="small">Your card is made in your browser. Nothing you type is sent to us. The link fills in these same numbers for whoever opens it.</p>
<img class="share-img" alt="Your heat pump savings result card" width="1200" height="630">
<div class="share-btns">
<a class="sbtn s-dl" download="heat-pump-savings.png" href="#">Download image</a>
<button type="button" class="sbtn s-native" hidden>Share…</button>
<a class="sbtn s-fb" href="#" target="_blank" rel="noopener">Facebook</a>
<a class="sbtn s-sms" href="#">Text message</a>
<a class="sbtn s-wa" href="#" target="_blank" rel="noopener">WhatsApp</a>
<button type="button" class="sbtn s-copy">Copy link</button>
</div><p class="small s-status" role="status"></p>
<label class="s-link-l">Link to these numbers<input class="s-link" type="text" readonly></label></section>
<div class="affil-slot" data-slot="quotes" aria-hidden="true"></div>
</form>"""

def price_line():
    return (f'<p class="small">Prices: electricity = {META["elec_label"]} (EIA Table 5.6.B). Natural gas = {META["gas_label"]} (EIA). '
            f'Heating oil and propane = EIA weekly residential price, week of {META["oil_date"]}; states EIA doesn\'t survey use the regional or U.S. price. '
            f'Climate = NOAA heating degree days. You can type your own prices.</p>')

GLOSS = """<div class="card"><h3 style="margin-top:0">Words on this page</h3><ul>
<li><strong>Heat pump:</strong> an electric system that moves heat from outside air into your home. It also cools in summer.</li>
<li><strong>COP:</strong> how many units of heat you get for each unit of electricity. COP 2.5 means 2.5 times more heat than a space heater on the same power.</li>
<li><strong>HSPF2:</strong> a heat pump's heating rating over a season. Higher is better. HSPF2 ÷ 3.412 ≈ average COP in a mild climate.</li>
<li><strong>Btu:</strong> a unit of heat. One gallon of heating oil holds about 138,500 Btu (EIA).</li></ul></div>"""

# ---------- home ----------
us = {"elec": META["elec_us"], "oil": META["oil_us"], "propane": META["propane_us"]}
ma = calc("MA", "oil"); pa = calc("PA", "propane"); oh = calc("OH", "gas")
hero = f"""<div class="hero"><h1>Will a heat pump cost less than your heat now?</h1>
<p class="sub">Pick your state and how you heat. We use this winter's prices from the U.S. Energy Information Administration (EIA) to show what a heat pump would cost to run. Free, no sign-up.</p></div>"""
home = calc_form("MA", "oil", "Check your savings") + price_line() + f"""
<h2>The short answer</h2>
<div class="answer"><p><strong>If you heat with oil or propane, a heat pump usually costs less to run.</strong> If you heat with natural gas, it often costs about the same or more, unless your electricity is cheap. If you heat with electric baseboards, a heat pump almost always costs less.</p></div>
<p>Why? Heating oil costs about <strong>${META['oil_us']:.2f} a gallon</strong> in the U.S. this month (EIA, week of {META['oil_date']}). EIA expects homes that heat with oil to spend about <strong>$2,115</strong> this winter (Nov–Mar), up 21%. Homes on natural gas: about <strong>$640</strong>, down 9% (<a href="{S_WFO[1]}" rel="noopener">EIA Winter Fuels Outlook</a>).</p>
<h2>Example homes (2,000 sq ft, average insulation, HSPF2 8.5)</h2>
<table><thead><tr><th>Home</th><th>Now, per year</th><th>Heat pump, per year</th><th>Heat pump costs</th></tr></thead><tbody>
<tr><td>Massachusetts, heating oil</td><td>{money(ma['now'])}</td><td>{money(ma['hp'])}</td><td>{diff(ma['save'])}</td></tr>
<tr><td>Pennsylvania, propane</td><td>{money(pa['now'])}</td><td>{money(pa['hp'])}</td><td>{diff(pa['save'])}</td></tr>
<tr><td>Ohio, natural gas</td><td>{money(oh['now'])}</td><td>{money(oh['hp'])}</td><td>{diff(oh['save'])}</td></tr>
</tbody></table>
<p class="small">These are running costs only. Your real numbers depend on your home, your system and the weather. See <a href="{u('/methodology/')}">how it works</a>.</p>
<h2>Popular comparisons</h2>
<ul class="cards"><li><a href="{u('/heating-oil-vs-heat-pump/')}">Heating oil vs heat pump</a></li><li><a href="{u('/propane-vs-heat-pump/')}">Propane vs heat pump</a></li>
<li><a href="{u('/natural-gas-vs-heat-pump/')}">Natural gas vs heat pump</a></li><li><a href="{u('/electric-baseboard-vs-heat-pump/')}">Electric baseboard vs heat pump</a></li>
<li><a href="{u('/states/')}">Prices and savings in all 50 states + DC</a></li><li><a href="{u('/heat-pump-tax-credit-2026/')}">Is there still a heat pump tax credit? (No: 25C ended)</a></li></ul>
{GLOSS}"""
page("/", "Heat Pump Savings Calculator 2026: Oil, Propane, Gas vs Heat Pump by State", "Free heat pump savings calculator with this winter's EIA prices for all 50 states. Compare heating oil, propane, natural gas or electric heat to a heat pump.",
     home, hero=hero, scripts=True, sources=PRICE_SRC,
     ld={"@type": "WebApplication", "name": SITE, "url": BASE + "/", "applicationCategory": "UtilitiesApplication", "operatingSystem": "Any", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}},
     faqs=[("Does a heat pump save money over oil?", f"Usually yes. At ${META['oil_us']:.2f} a gallon (EIA U.S. average, week of {META['oil_date']}), oil heat costs much more per unit of heat than a heat pump in most states. Check your state's electricity price in the calculator."),
           ("Does a heat pump save money over natural gas?", "Often not by much. Gas is cheap in many states this winter. A heat pump can still win where electricity is cheap or where you'd also replace an air conditioner."),
           ("Do heat pumps work in cold climates?", "Yes, but they make less heat and use more power when it is very cold. Cold-climate models keep working below 0°F. Our calculator lowers the efficiency for colder states."),
           ("Is there still a federal tax credit for heat pumps?", f"No. The 25C credit (30%, up to $2,000) does not apply to equipment placed in service after December 31, 2025, per the <a href=\"{S_IRSFAQ[1]}\" rel=\"noopener\">IRS</a>. Some state and utility rebates still exist.")])

# ---------- state pages ----------
def rank(key, s, rev=False):
    vals = sorted([x[key] for x in STATES], reverse=rev); return vals.index(s[key]) + 1
def src_note(v): return "state price" if v == "state" else f"{v} price (EIA has no weekly price for this state)"
for s in STATES:
    res = {f: calc(s["abbr"], f) for f in ("oil", "propane", "gas", "elec")}
    best = min(res, key=lambda f: res[f]["now"])
    cop = res["oil"]["cop"]; er = rank("elec", s)
    pdiff = (s["elec"] / META["elec_us"] - 1) * 100
    win = [FNAME[f].lower() for f in ("oil", "propane", "gas", "elec") if res[f]["save"] > 0.1 * res[f]["now"]]
    rows = "".join(f"<tr><td>{FNAME[f]}</td>{cost_cells(res[f])}</tr>" for f in ("oil", "propane", "gas", "elec"))
    mf = s["main_fuel"]; msh = s["fuel_shares"][mf]
    mf_name = {"oil": "heating oil", "propane": "propane", "gas": "natural gas", "elec": "electricity (this includes homes that already have a heat pump)"}[mf]
    low_s = low(res["oil"])
    cold = "very cold" if s["hdd"] >= 7000 else "cold" if s["hdd"] >= 5000 else "mild" if s["hdd"] >= 3000 else "warm"
    short = (f"{s['name']} has a warm climate, so most homes need very little heating. Heating costs are small whichever system you use; a heat pump matters more here for cooling." if low_s else
             "at this winter's prices, a heat pump " + ((('costs less to run than ' + (' and '.join(win) if len(win)<3 else ', '.join(win[:-1]) + ' and ' + win[-1])) if win else 'does not clearly beat any fuel on running cost') + " in a typical 2,000 sq ft home."))
    body = f"""<div class="answer"><p><strong>Short answer for {s['name']}:</strong> {short}
Electricity here averages <strong>{s['elec']:.2f}¢ per kWh</strong>, {abs(pdiff):.0f}% {"above" if pdiff > 0 else "below"} the U.S. average of {META['elec_us']:.2f}¢ (#{er} cheapest of 51).</p></div>
<h2>{s['name']} heating prices this winter</h2>
<table><thead><tr><th>Fuel</th><th>Price</th><th>Cost per million Btu of heat</th><th>Source</th></tr></thead><tbody>
<tr><td>Electricity</td><td>{s['elec']:.2f}¢/kWh</td><td>${res['oil']['per_hp']:.2f} with a heat pump (COP {cop:.2f}); ${res['elec']['per_now']:.2f} with baseboards</td><td>EIA, Jan–Aug 2026 average</td></tr>
<tr><td>Heating oil</td><td>${s['oil']:.2f}/gal</td><td>${res['oil']['per_now']:.2f} (83% efficient)</td><td>EIA weekly, {META['oil_date']}, {src_note(s['oil_src'])}</td></tr>
<tr><td>Propane</td><td>${s['propane']:.2f}/gal</td><td>${res['propane']['per_now']:.2f} (90% efficient)</td><td>EIA weekly, {META['propane_date']}, {src_note(s['propane_src'])}</td></tr>
<tr><td>Natural gas</td><td>${s['gas_therm']:.2f}/therm (${s['gas_mcf']:.2f}/Mcf)</td><td>${res['gas']['per_now']:.2f} (90% efficient)</td><td>EIA, Nov 2025–Mar 2026 average{'' if s['gas_src']=='state' else ' (U.S.)'}</td></tr>
</tbody></table>
<h2>Yearly cost: your fuel vs a heat pump</h2>
<p>For a 2,000 sq ft home with average insulation in {s['name']}'s {cold} climate ({s['hdd']:,} heating degree days a year), with a heat pump rated HSPF2 8.5 (we use COP {cop:.2f} here):</p>
<table><thead><tr><th>Heating now</th><th>Now, per year</th><th>Heat pump, per year</th><th>Heat pump costs</th><th>Break-even power price</th></tr></thead><tbody>{rows}</tbody></table>
<p class="small">{'' if low_s else f"Cheapest to run today in this example: <strong>{('a heat pump' if res[best]['now'] > res['oil']['hp'] else FNAME[best].lower())}</strong>. "}Break-even means: if you pay less than this per kWh, the heat pump is cheaper than that fuel.</p>
<p>The calculator below starts with <strong>{mf_name}</strong>, the most common main heating fuel in {s['name']} ({msh}% of homes, <a href="{S_RECS[1]}" rel="noopener">EIA RECS 2020</a>). Change it to match your home.</p>
{calc_form(s['abbr'], mf, 'Run it for your home in ' + s['name'])}
<h2>Rebates in {s['name']}</h2>
<p>The federal 25C tax credit for heat pumps ended for equipment placed in service after Dec 31, 2025 (<a href="{S_IRSFAQ[1]}" rel="noopener">IRS</a>). Federal Home Energy Rebates (HEAR/HOMES) are run by each state, and many states have not opened. Since Sept 1, 2026, new HEAR rebates can't pay to replace oil, propane or gas heat unless the old system stays in place (<a href="{S_PN262[1]}" rel="noopener">DOE Program Notice 26-2</a>). Check your state energy office and your electric utility. <a href="{u('/heat-pump-rebates-2026/')}">Full 2026 rebate guide</a>.</p>
<div class="affil-slot" data-slot="state-installers" aria-hidden="true"></div>
<p><a href="{u('/states/')}">See all states</a></p>"""
    page(f"/state/{s['slug']}/", f"Heat Pump vs Oil, Propane and Gas in {s['name']} (2026 Prices)",
         f"Will a heat pump save money in {s['name']}? This winter's EIA prices: electricity {s['elec']:.1f}¢/kWh, oil ${s['oil']:.2f}, propane ${s['propane']:.2f}, gas ${s['gas_therm']:.2f}/therm. Free calculator.",
         body, h1=f"Heat pump savings in {s['name']}", crumbs=[("States", "/states/")], scripts=True, sources=PRICE_SRC + [S_RECS, S_IRSFAQ, S_PN262],
         og=f"/assets/og/state/{s['slug']}.png", og_alt=f"Heat pump vs oil, propane, gas and electric heat in {s['name']}: yearly running cost at 2026 EIA prices",
         faqs=[(f"Is a heat pump cheaper than oil in {s['name']}?", (f"{s['name']} needs very little heating, so the yearly difference is small either way. The heat pump is cheaper to run if your electricity costs less than ${res['oil']['breakeven']:.3f} per kWh." if low_s else f"In our example home, oil costs about {money(res['oil']['now'])} a year and a heat pump about {money(res['oil']['hp'])}. The heat pump wins if your electricity costs less than ${res['oil']['breakeven']:.3f} per kWh.")),
               (f"Is a heat pump cheaper than natural gas in {s['name']}?", (f"With so little heating needed in {s['name']}, the yearly difference is small. The break-even electricity price is ${res['gas']['breakeven']:.3f} per kWh." if low_s else f"In our example, gas costs about {money(res['gas']['now'])} a year and a heat pump about {money(res['gas']['hp'])}. The break-even electricity price is ${res['gas']['breakeven']:.3f} per kWh.")),
               (f"What is the most common way to heat a home in {s['name']}?", f"{mf_name[0].upper() + mf_name[1:]}: {msh}% of homes use it as their main heating fuel, per EIA's 2020 Residential Energy Consumption Survey."),
               (f"What does electricity cost in {s['name']}?", f"{s['elec']:.2f} cents per kWh on average for homes, January–August 2026 (EIA Electric Power Monthly, Table 5.6.B). Your utility's rate may differ.")])

lis = "".join(f'<li><a href="{u("/state/" + s["slug"] + "/")}">{s["name"]}</a></li>' for s in STATES)
tbl = "".join(f'<tr><td><a href="{u("/state/" + s["slug"] + "/")}">{s["name"]}</a></td><td>{s["elec"]:.2f}¢</td><td>${s["oil"]:.2f}{"" if s["oil_src"]=="state" else "*"}</td><td>${s["propane"]:.2f}{"" if s["propane_src"]=="state" else "*"}</td><td>${s["gas_therm"]:.2f}</td><td>{LOWTXT if low(calc(s["abbr"],"oil")) else diff(calc(s["abbr"],"oil")["save"])}</td></tr>' for s in STATES)
page("/states/", "Heat Pump Savings by State: 2026 Electricity, Oil, Propane and Gas Prices", "Compare heat pump running costs in all 50 states and DC with this winter's EIA prices for electricity, heating oil, propane and natural gas.",
     f"""<p>Pick your state for a full page with prices, yearly costs and a calculator set for your state.</p><ul class="statelist">{lis}</ul>
<h2>All states at a glance</h2><table><thead><tr><th>State</th><th>Electricity (per kWh)</th><th>Heating oil (per gal)</th><th>Propane (per gal)</th><th>Gas (per therm)</th><th>Heat pump vs oil, per year*</th></tr></thead><tbody>{tbl}</tbody></table>
<p class="small">* Regional or U.S. price used where EIA has no weekly state price. Savings: 2,000 sq ft home, average insulation, 83% oil system, heat pump HSPF2 8.5, adjusted for climate.</p>{price_line()}""",
     h1="Heat pump savings by state", sources=PRICE_SRC)

# ---------- fuel comparison pages ----------
def fuel_page(fuel, slug, title, h1, desc, intro, faqs):
    rows = sorted(STATES, key=lambda s: (low(calc(s["abbr"], fuel)), -calc(s["abbr"], fuel)["save"]))
    t = "".join(f'<tr><td><a href="{u("/state/" + s["slug"] + "/")}">{s["name"]}</a></td>{cost_cells(calc(s["abbr"],fuel))}</tr>' for s in rows)
    body = f"""{intro}{calc_form('MA' if fuel in ('oil','elec') else 'PA' if fuel=='propane' else 'OH', fuel, 'Check your home')}{price_line()}
<h2>{FNAME[fuel]} vs heat pump in every state</h2><p>Example: 2,000 sq ft, average insulation, heat pump HSPF2 8.5. Sorted by savings. States with almost no heating season are listed last.</p>
<table><thead><tr><th>State</th><th>{FNAME[fuel]}, per year</th><th>Heat pump, per year</th><th>Heat pump costs</th><th>Break-even power price</th></tr></thead><tbody>{t}</tbody></table>{GLOSS}"""
    page(slug, title, desc, body, h1=h1, faqs=faqs, scripts=True, sources=PRICE_SRC + [S_ESASHP, S_NEEP])

o_ma = calc("MA", "oil")
fuel_page("oil", "/heating-oil-vs-heat-pump/", "Heating Oil vs Heat Pump 2026: Cost Calculator by State", "Heating oil vs heat pump",
  f"Heating oil is ${META['oil_us']:.2f} a gallon this month (EIA). Compare oil heat to a heat pump in your state with this winter's prices.",
  f"""<div class="answer"><p><strong>Heating oil costs about ${META['oil_us']:.2f} a gallon</strong> in the U.S. (EIA, week of {META['oil_date']}). EIA expects oil-heated homes to spend about $2,115 this winter, 21% more than last winter. In most states a heat pump costs less to run than an oil furnace or boiler.</p></div>
<p>One gallon of oil gives about 138,500 Btu of heat, and an 83% efficient boiler delivers about 115,000 Btu. To make the same heat, a heat pump with a COP of 2.5 uses about 13.5 kWh. So if your electricity costs less than <strong>${META['oil_us']/13.5:.2f} per kWh</strong>, the heat pump wins. In Massachusetts, our example home would spend {money(o_ma['now'])} on oil and {money(o_ma['hp'])} with a heat pump.</p>
<p>Many oil homes keep the boiler as a backup for the coldest days. That is allowed under the new federal HEAR rules (see <a href="{u('/heat-pump-rebates-2026/')}">rebates</a>).</p>""",
  [("How many kWh equals a gallon of heating oil?", "A gallon of heating oil holds about 138,500 Btu (EIA), which equals about 40.6 kWh of electricity. A heat pump with COP 2.5 makes the useful heat of a gallon burned at 83% efficiency with about 13.5 kWh."),
   ("Should I keep my oil boiler?", "Many people keep it as backup for very cold days. You can choose that in your plan. Since Sept 1, 2026, keeping the old system is required if you want a federal HEAR rebate for the heat pump."),
   ("Why did oil heat get more expensive this winter?", f"EIA's Winter Fuels Outlook expects higher heating oil prices this winter. Weekly residential oil was ${META['oil_us']:.2f} a gallon on {META['oil_date']}.")])
_ps=[x for x in STATES if x["propane_src"]=="state"]; lo=min(_ps,key=lambda x:x["propane"]); hi=max(_ps,key=lambda x:x["propane"])
fuel_page("propane", "/propane-vs-heat-pump/", "Propane vs Heat Pump 2026: Which Costs Less to Heat Your Home?", "Propane vs heat pump",
  f"Propane is ${META['propane_us']:.2f} a gallon (EIA U.S. average). Compare propane heat to a heat pump in your state with this winter's prices.",
  f"""<div class="answer"><p><strong>Propane averages ${META['propane_us']:.2f} a gallon</strong> in the U.S. (EIA, week of {META['propane_date']}), but prices vary a lot: from about ${lo['propane']:.2f} in {lo['name']} to about ${hi['propane']:.2f} in {hi['name']} (state prices EIA surveys). Where propane is costly, a heat pump usually wins. In the Midwest, where propane is cheap, it can be close.</p></div>
<p>One gallon of propane holds about 91,452 Btu (EIA). A 90% furnace delivers about 82,000 Btu. A heat pump with COP 2.5 makes that with about 9.6 kWh. So the heat pump wins if your power costs less than about <strong>${META['propane_us']/9.65:.2f} per kWh</strong> at the U.S. average propane price.</p>""",
  [("Is propane or a heat pump cheaper?", "It depends on your state. With propane above about $3 a gallon, a heat pump usually costs less to run. With propane under $2, it is often close."),
   ("How many kWh equals a gallon of propane?", "About 26.8 kWh of energy (91,452 Btu ÷ 3,412). With a COP 2.5 heat pump, about 9.6 kWh makes the same useful heat as a gallon burned at 90%.")])
fuel_page("gas", "/natural-gas-vs-heat-pump/", "Natural Gas vs Heat Pump 2026: Running Cost by State", "Natural gas vs heat pump",
  "Is a heat pump cheaper than a gas furnace? Compare with this winter's EIA gas and electricity prices for your state.",
  f"""<div class="answer"><p><strong>Natural gas is the cheapest heat in most states this winter.</strong> EIA expects gas-heated homes to spend about $640 this winter, 9% less than last winter. A heat pump beats gas mainly where electricity is cheap or gas is costly.</p></div>
<p>A therm of gas is 100,000 Btu. A 90% furnace delivers 90,000 Btu. A heat pump with COP 2.5 uses about 10.6 kWh to make that heat. So at $1.50 a therm, the heat pump wins only if power costs under about $0.14 per kWh. Many people still choose a heat pump to replace an old air conditioner, since it cools too.</p>""",
  [("Will a heat pump lower my gas bill?", "It removes the gas heating bill but adds electricity. In many states the total is about the same or higher at today's prices. Check yours."),
   ("What is a dual-fuel system?", "A heat pump plus a gas furnace. The heat pump heats on mild days, and the furnace takes over when it's very cold or when gas is cheaper.")])
fuel_page("elec", "/electric-baseboard-vs-heat-pump/", "Electric Baseboard vs Heat Pump: How Much Can You Save? (2026)", "Electric baseboard vs heat pump",
  "Switching from electric baseboard or resistance heat to a heat pump cuts heating power use by more than half. See savings in your state.",
  f"""<div class="answer"><p><strong>A heat pump uses about 50–70% less electricity than baseboard heat</strong> for the same warmth, because it moves heat instead of making it. Baseboards have a COP of 1. A heat pump with COP 2.5 uses 60% less.</p></div>
<p>This is the switch that still qualifies for federal HEAR rebates after Sept 1, 2026: replacing electric equipment with more efficient electric equipment (<a href="{S_PN262[1]}" rel="noopener">DOE Program Notice 26-2</a>), where your state has opened its program.</p>""",
  [("How much does a heat pump save over baseboard heat?", "With COP 2.5, about 60% of the heating electricity. With COP 2, about 50%. The calculator shows dollars for your state."),
   ("Are ductless mini-splits good for baseboard homes?", "Yes. Many baseboard homes have no ducts, so mini-splits are a common fit.")])

# ---------- rebates & tax credit ----------
reb = f"""<div class="answer"><p><strong>Short answer:</strong> the federal 30% heat pump tax credit (25C, up to $2,000 a year) is gone for equipment placed in service after Dec 31, 2025. Federal Home Energy Rebates still exist in some states, but since Sept 1, 2026 they can't pay to replace oil, propane or gas heat with a heat pump unless you keep the old system. State and utility rebates are separate and may still help.</p></div>
<h2>What changed</h2>
<table><thead><tr><th>Program</th><th>Status in 2026</th><th>Source</th></tr></thead><tbody>
<tr><td>25C Energy Efficient Home Improvement Credit (heat pumps: 30%, up to $2,000/yr)</td><td>No credit for property placed in service after Dec 31, 2025</td><td><a href="{S_IRSFAQ[1]}" rel="noopener">IRS FAQ</a></td></tr>
<tr><td>25D Residential Clean Energy Credit (geothermal heat pumps, solar)</td><td>No credit for expenses made after Dec 31, 2025</td><td><a href="{S_IRSFAQ[1]}" rel="noopener">IRS FAQ</a></td></tr>
<tr><td>HEAR / HEEHR (electric appliance rebates, up to $14,000 per home)</td><td>Run by states; only in some states. New reservations since Sept 1, 2026: no fuel switching; electric-to-electric upgrades and new construction allowed; may need insulation and air sealing first</td><td><a href="{S_PN262[1]}" rel="noopener">DOE Notice 26-2</a>, <a href="{S_DOE[1]}" rel="noopener">DOE</a></td></tr>
<tr><td>HOMES (whole-home savings rebates, up to $8,000)</td><td>Run by states; rules vary by state</td><td><a href="{S_DOE[1]}" rel="noopener">DOE</a></td></tr>
<tr><td>Utility and state programs</td><td>Separate from federal rules. Many still offer heat pump rebates</td><td>Your utility / state energy office</td></tr>
</tbody></table>
<h2>If you heat with oil, propane or gas</h2>
<p>Under DOE's new guidance, a HEAR rebate can still help with a heat pump <strong>if the existing fossil-fuel system stays in place and is not taken out</strong>. The heat pump no longer has to be your main heat (<a href="{S_NASEO[1]}" rel="noopener">NASEO FAQ, Sept 2026</a>). Rebates reserved on or before Aug 31, 2026 follow the old rules.</p>
<h2>If you heat with electric baseboards or an old heat pump</h2><p>This is the main case HEAR covers now: replacing electric equipment with more efficient electric equipment.</p>
<h2>How to check what you can get</h2><ol class="big"><li>Check your <strong>state energy office</strong> page for HEAR/HOMES status (the <a href="{S_ESHEAR[1]}" rel="noopener">ENERGY STAR HEAR page</a> lists state programs).</li>
<li>Check your <strong>electric utility's</strong> rebate page. These are often the biggest rebates left.</li>
<li>Ask installers which rebates they process. Get the rebate amount in writing before you sign.</li>
<li>Use our <a href="{u('/heat-pump-cost/')}">payback calculator</a> with the quote and rebate.</li></ol>
<div class="card warn"><p><strong>Watch out:</strong> some ads still promise a "30% federal tax credit" on heat pumps. That credit doesn't apply to systems installed in 2026.</p></div>
<div class="affil-slot" data-slot="rebate-finder" aria-hidden="true"></div>"""
page("/heat-pump-rebates-2026/", "Heat Pump Rebates 2026: What's Left After the 25C Tax Credit Ended", "The 25C heat pump tax credit ended Dec 31, 2025. What federal HEAR rebates, state and utility programs still cover in 2026, with official sources.",
     reb, h1="Heat pump rebates and credits in 2026", sources=[S_IRSFAQ, S_25C, S_DOE, S_PN262, S_NASEO, S_ESHEAR],
     faqs=[("Is there a federal tax credit for heat pumps in 2026?", "No. The IRS says the 25C credit does not apply to property placed in service after December 31, 2025."),
           ("Can I get a HEAR rebate to replace my oil furnace with a heat pump?", "Not for new reservations since Sept 1, 2026, unless the oil system stays in place. Rules come from DOE Program Notice 26-2; your state runs the program."),
           ("What is the biggest heat pump rebate left?", "It depends on where you live. Check your electric utility and your state energy office first.")])
page("/heat-pump-tax-credit-2026/", "Heat Pump Tax Credit 2026: Did 25C End? (Yes — Here's What Remains)", "The 25C heat pump tax credit ended for systems placed in service after Dec 31, 2025, per the IRS. What it was, who can still claim it, and what replaced it.",
     f"""<div class="answer"><p><strong>Yes, it ended.</strong> The 2025 tax law (Public Law 119-21) ended the 25C Energy Efficient Home Improvement Credit for property placed in service after December 31, 2025 (<a href="{S_IRSFAQ[1]}" rel="noopener">IRS</a>).</p></div>
<h2>What it was</h2><p>25C gave 30% of the cost of a qualifying heat pump, up to $2,000 a year. It applied to heat pumps placed in service from 2023 through 2025.</p>
<h2>Who can still claim it</h2><p>If your heat pump was <strong>placed in service in 2025</strong>, you claim it on your 2025 tax return using IRS Form 5695. A system installed in 2026 doesn't qualify.</p>
<h2>What's left</h2><p>State and utility rebates, and federal HEAR/HOMES rebates in states that run them. See the <a href="{u('/heat-pump-rebates-2026/')}">2026 rebate guide</a>.</p>""",
     h1="Is there still a heat pump tax credit?", sources=[S_IRSFAQ, S_25C],
     faqs=[("Can I claim 25C for a heat pump installed in January 2026?", "No. The IRS says no credit is allowed for property placed in service after December 31, 2025."),
           ("I paid in 2025 but it was installed in 2026. Do I qualify?", "25C depends on when the property is placed in service. Check the IRS FAQ and a tax professional.")])

# ---------- payback, sizing, portable, hspf2 ----------
page("/heat-pump-cost/", "Heat Pump Payback Calculator: How Long Until It Pays for Itself?", "Enter your heat pump quote, rebates and yearly savings to see the payback time in years. Get your yearly savings from our free state calculator.",
     f"""<p>A heat pump costs money up front. This tells you how many years of lower bills it takes to pay that back. Get your yearly savings from the <a href="{u('/')}">savings calculator</a> first.</p>
<form class="card hp-pay" onsubmit="return false"><div class="grid"><label>Installed price from your quote ($)<input name="cost" type="number" inputmode="numeric" value="15000"></label>
<label>Rebates you will get ($)<input name="rebate" type="number" inputmode="numeric" value="0"></label><label>Yearly savings ($)<input name="save" type="number" inputmode="numeric" value="{round(ma['save'])}"></label></div>
<div class="out" aria-live="polite"><div class="lbl">Simple payback</div><div class="big"></div><p class="sentence"></p></div></form>
<p class="small">The starting numbers are examples only. Use your own quote. The yearly savings start at our Massachusetts oil example ({money(ma['save'])}).</p>
<h2>Things that change the answer</h2><ul><li><strong>Replacing an air conditioner too?</strong> A heat pump also cools, so compare against the cost of a new AC plus a new furnace, not zero.</li>
<li><strong>Rebates:</strong> utility rebates can be large. Get them in writing.</li><li><strong>Fuel prices:</strong> oil prices change a lot from year to year (EIA).</li><li><strong>Insulation:</strong> sealing air leaks first lowers the size and cost of the system.</li></ul>
<div class="affil-slot" data-slot="quotes" aria-hidden="true"></div>""", h1="Heat pump payback calculator", scripts=True, sources=[S_WFO, S_DOE, S_ESASHP],
     faqs=[("How much does a heat pump cost?", "It varies by home size, ducts, brand and region. Get at least three written quotes. We don't publish price averages we can't verify."),
           ("What is a good payback time?", "Shorter is better. Many people also count comfort, summer cooling and replacing old equipment, not just the payback years.")])
page("/mini-split-size-calculator/", "Mini Split Size Calculator: What Size Heat Pump Do I Need?", "Rough heat pump and mini-split size (Btu/hr and tons) from your space, insulation and coldest winter temperature. Free, plain-language.",
     f"""<p>This gives a <strong>rough size</strong> to help you compare quotes. A good installer should do a room-by-room load calculation (called Manual J) before you buy.</p>
<form class="card hp-size" onsubmit="return false"><div class="grid"><label>Area to heat (sq ft)<input name="sqft" type="number" inputmode="numeric" value="1000"></label>
<label>Insulation<select name="ins"><option value="tight">Good</option><option value="avg" selected>Average</option><option value="leaky">Drafty</option></select></label>
<label>Coldest normal winter temperature (°F)<input name="t" type="number" inputmode="numeric" value="5"></label></div>
<div class="out" aria-live="polite"><div class="lbl">Heat needed on the coldest days</div><div class="big"></div><p class="sentence"></p></div></form>
<h2>How we estimate it</h2><p>We use the same heat-loss assumption as our savings calculator (3, 4 or 5.5 Btu per sq ft per degree day for good, average or drafty homes). Heat loss per hour = that number × area ÷ 24 × (65°F − outdoor temperature). It's a planning number, not a design.</p>
<h2>Why the cold-temperature number matters</h2><p>Heat pumps make less heat when it's colder. Check how much heat a model makes at 5°F on the <a href="{S_NEEP[1]}" rel="noopener">NEEP cold-climate list</a> or its spec sheet, not just its name ("12k", "18k").</p>
<div class="affil-slot" data-slot="mini-split" aria-hidden="true"></div>""", h1="Mini-split size calculator", scripts=True, sources=[S_NEEP, S_ESMINI, S_AHRI],
     faqs=[("How many square feet does a 12,000 Btu mini split heat?", "It depends on insulation and climate. In our average-insulation example at 5°F outdoors, 12,000 Btu/hr covers about 1,200 sq ft. Drafty homes need more."),
           ("Is a bigger heat pump better?", "No. Too big can short-cycle and feel less comfortable. Size it to your home's heat loss.")])
pc = BY["NY"]["elec"] / 100
page("/portable-heat-pump/", "Portable and Window Heat Pumps: Running Cost vs a Space Heater", "Do portable or window heat pumps save money over a space heater? Simple math with your state's 2026 electricity price.",
     f"""<p>A space heater turns 1 kWh of power into 3,412 Btu of heat (COP 1). A small window or portable heat pump can make 2 or more times that much heat from the same power, when it isn't too cold outside.</p>
<table><thead><tr><th>Heater (making 5,000 Btu/hr)</th><th>Power used</th><th>Cost per hour at {pc*100:.1f}¢/kWh (NY avg)</th></tr></thead><tbody>
<tr><td>Space heater (COP 1)</td><td>{5000/3412:.2f} kW</td><td>${5000/3412*pc:.2f}</td></tr>
<tr><td>Window/portable heat pump (COP 2)</td><td>{5000/3412/2:.2f} kW</td><td>${5000/3412/2*pc:.2f}</td></tr>
<tr><td>Window/portable heat pump (COP 2.5)</td><td>{5000/3412/2.5:.2f} kW</td><td>${5000/3412/2.5*pc:.2f}</td></tr></tbody></table>
<h2>Things to know</h2><ul><li>Portable units with one hose can pull cold air into the room, which lowers real savings.</li><li>Window heat pumps are popular for apartments where you can't install a mini-split.</li>
<li>Look for the heating capacity at low temperatures on the spec sheet.</li><li>During a power outage, no electric heater works without backup power. See <a href="https://www.ready.gov/power-outages" rel="noopener">Ready.gov</a>.</li></ul>
<div class="affil-slot" data-slot="window-hp" aria-hidden="true"></div>""", h1="Portable and window heat pumps", sources=[S_EPM, S_BTU, S_ESASHP, ("Ready.gov: Power outages", "https://www.ready.gov/power-outages")],
     faqs=[("Is a window heat pump cheaper than a space heater?", "Yes, when it's working as a heat pump. At COP 2 it uses about half the electricity for the same heat.")])
page("/hspf2-to-cop/", "HSPF2 to COP Converter (and What a Good HSPF2 Is)", "Convert a heat pump's HSPF2 rating to an average COP. Plain-language guide to HSPF2, HSPF and cold-climate performance.",
     f"""<form class="card hp-cop" onsubmit="return false"><label>HSPF2 rating<input name="h" type="number" step="0.1" inputmode="decimal" value="8.5"></label><div class="out"><div class="lbl">Average seasonal COP</div><div class="big"></div></div></form>
<p><strong>The math:</strong> HSPF2 is Btu of heat per watt-hour of electricity over a test season. One watt-hour = 3.412 Btu. So COP ≈ HSPF2 ÷ 3.412. An HSPF2 of 8.5 ≈ COP 2.49.</p>
<p>The HSPF2 test season represents a moderate climate. In colder states, real COP is lower. Our calculator lowers it by 10% for states with 5,000–7,000 heating degree days and 20% above 7,000. This is our planning assumption, not a test result.</p>
<p>Compare real models on the <a href="{S_AHRI[1]}" rel="noopener">AHRI directory</a> and the <a href="{S_NEEP[1]}" rel="noopener">NEEP cold-climate list</a>.</p>""",
     h1="HSPF2 to COP converter", scripts=True, sources=[S_AHRI, S_NEEP, S_ESASHP, S_BTU])

# ---------- methodology / sources / trust ----------
page("/methodology/", "How the Heat Pump Savings Calculator Works", "Formulas, prices, climate data and assumptions behind Heat Pump Savings Check.",
     f"""<h2>The steps</h2><ol class="big">
<li><strong>Heat your home needs per year.</strong> Home-size mode: square feet × your state's heating degree days × 3, 4 or 5.5 Btu (good, average, drafty insulation). Usage mode: last winter's fuel × its heat content × your system's efficiency.</li>
<li><strong>Cost now:</strong> heat needed ÷ (fuel heat content × efficiency) × price.</li>
<li><strong>Heat pump cost:</strong> heat needed ÷ 3,412 Btu/kWh ÷ COP × electricity price.</li>
<li><strong>COP:</strong> the COP you enter, or HSPF2 ÷ 3.412, adjusted for climate: ×1.05 below 3,000 heating degree days, ×1.0 for 3,000–5,000, ×0.9 for 5,000–7,000, ×0.8 above 7,000.</li></ol>
<h2>Fixed numbers</h2><table><tbody><tr><td>Heating oil</td><td>138,500 Btu/gal (EIA)</td></tr><tr><td>Propane</td><td>91,452 Btu/gal (EIA)</td></tr><tr><td>Natural gas</td><td>100,000 Btu/therm; 1,036 Btu per cubic foot, so 1 Mcf ≈ 10.36 therms (EIA)</td></tr><tr><td>Electricity</td><td>3,412 Btu/kWh (EIA)</td></tr>
<tr><td>Default efficiency</td><td>Oil 83%, propane and gas 90%, electric resistance 100% (you can change these)</td></tr></tbody></table>
<h2>Prices</h2>{price_line()}<p>Why these periods? Electricity uses the newest year-to-date average so it includes winter months. Gas uses last winter's months because summer gas prices per unit are much higher and don't reflect heating bills. Oil and propane use EIA's newest weekly survey, which runs October through March.</p>
<h2>Our assumptions (not official numbers)</h2><p>The heat-loss factors and the climate adjustment for COP are our own planning assumptions, chosen to give typical results. They are not from a government source. Usage mode, with your real fuel use, is more accurate.</p>
<h2>Limits</h2><ul><li>Running costs only. No purchase, install, maintenance or demand charges.</li><li>Doesn't model backup heat strips, dual-fuel or time-of-use rates.</li><li>State averages hide big local differences. Use your own bill prices when you can.</li></ul>""",
     h1="How it works", sources=PRICE_SRC + [S_NORM])
page("/sources/", "Sources and Data", "Every data source used by Heat Pump Savings Check, with dates.",
     f"""<p>All prices come from free public downloads from the U.S. Energy Information Administration. No API keys or paid data. We re-check when EIA publishes new data.</p>{price_line()}
<ul>{''.join(f'<li><a href="{x}" rel="noopener">{t}</a></li>' for t, x in PRICE_SRC + [S_NORM, S_RECS, S_IRSFAQ, S_25C, S_DOE, S_PN262, S_NASEO, S_ESHEAR, S_ESASHP, S_ESMINI, S_NEEP, S_AHRI])}</ul>
<p>Hawaii, Alaska and DC climate use NOAA 1991–2020 airport station normals (Honolulu, Anchorage, Washington Reagan) because the statewide series doesn't cover them. All other states use NOAA nClimDiv statewide heating degree days, 1991–2020 average.</p>""", h1="Sources and data")
page("/about/", f"About {SITE}", f"Who runs {SITE} and how we keep it accurate.",
     f"""<p>{SITE} is a free, independent calculator that helps people see if a heat pump would lower their heating bill. It uses public data from the EIA, NOAA, the IRS and the U.S. Department of Energy.</p>
<p><strong>{INDEP}</strong> We don't sell heat pumps or installs.</p>
<h2>Editorial policy</h2><ul><li>Official sources first. Each page lists its sources and its update date.</li><li>We show our formulas and assumptions.</li><li>No paid placements in results. If we ever add affiliate links or ads, they will be clearly labeled.</li>
<li>Corrections: <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a>.</li></ul><h2>Author</h2><p>Built by {AUTHOR}. Not a licensed engineer, contractor or tax adviser. Nothing here is professional advice.</p>""", h1=f"About {SITE}")
page("/contact/", f"Contact {SITE}", "Send corrections or questions.", f'<p>Email: <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></p><p>We can\'t give quotes, recommend installers or give tax advice.</p>', h1="Contact")
page("/privacy/", "Privacy Policy", f"{SITE} privacy policy.", f"""<p>Last updated {UPDATED_H}.</p><h2>Calculator data</h2><p>All math runs in your browser. We don't receive or store what you type. We use no cookies, analytics or trackers.</p>
<h2>Share cards and links</h2><p>The result image is drawn in your browser. The share link puts your calculator inputs (state, fuel, home size, prices) in the web address so the calculator can fill them in for whoever opens it. The share buttons are plain links to Facebook, WhatsApp or your text app; we don't load their scripts. Once you share, that service's own privacy policy applies.</p>
<h2>Ads and cookies</h2><p>We don't show ads today. If we add them later (for example Google AdSense), third-party vendors including Google may use cookies to serve ads based on your visits to this and other sites. You'll be able to opt out at <a href="https://www.google.com/settings/ads">Google Ads Settings</a>. We will update this page first.</p>
<h2>Affiliate links</h2><p>None today. If added, they will be labeled.</p><h2>Contact</h2><p><a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></p>""", h1="Privacy Policy")
page("/disclaimer/", "Disclaimer", "Estimates only; not professional, tax or financial advice.",
     f"<p>Results are estimates for planning. Real costs depend on your home, equipment, installation, weather and rates. This is not engineering, tax or financial advice. Rebate rules change; confirm with your state energy office, utility and the IRS. {INDEP}</p>", h1="Disclaimer")

# ---------- assets ----------
A = OUT / "assets"; A.mkdir(parents=True, exist_ok=True)
shutil.copy(ROOT / "src" / "style.css", A / "style.css"); shutil.copy(ROOT / "src" / "calc.js", A / "calc.js")
(A / "prices.js").write_text("window.HPS=" + json.dumps(DATA, separators=(",", ":")) + ";\n")
shutil.copy(ROOT / "data" / "prices.json", A / "prices.json")
(OUT / "404.html").write_text(f'<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Not found – {SITE}</title><link rel=stylesheet href="{u("/assets/style.css")}"><main><h1>Page not found</h1><p><a href="{u("/")}">Go to the heat pump savings calculator</a></p></main></html>')
bots = ["Googlebot", "Bingbot", "GPTBot", "OAI-SearchBot", "ChatGPT-User", "PerplexityBot", "Perplexity-User", "ClaudeBot", "Claude-User", "Claude-SearchBot",
        "Google-Extended", "Applebot", "Applebot-Extended", "CCBot", "DuckDuckBot", "Amazonbot", "meta-externalagent", "MistralAI-User"]
(OUT / "robots.txt").write_text("".join(f"User-agent: {b}\nAllow: /\n\n" for b in bots) + f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")
(OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
     "".join(f"  <url><loc>{BASE}{p}</loc><lastmod>{UPDATED}</lastmod></url>\n" for p, *_ in PAGES) + "</urlset>\n")
trust = ("/about/", "/contact/", "/privacy/", "/disclaimer/")
core = [x for x in PAGES if x[0] not in trust and not x[0].startswith("/state/")]
llms = (f"# {SITE}\n\n> {TAGLINE}. Independent, free, no sign-up. Last updated {UPDATED}.\n\n"
        f"Author: {AUTHOR} ({BASE}/about/). Contact: {CONTACT_EMAIL}. {INDEP}\n\n"
        f"Key facts (Oct 2026): U.S. residential heating oil ${META['oil_us']:.2f}/gal and propane ${META['propane_us']:.2f}/gal (EIA weekly, {META['oil_date']}); "
        f"U.S. residential electricity {META['elec_us']:.2f}¢/kWh (EIA, Jan–Aug 2026). EIA Winter Fuels Outlook (Oct 2026) expects Nov–Mar spending of about $2,115 for oil-heated homes (+21%), $1,246 propane (−3%), $1,196 electricity (+4%), $640 natural gas (−9%). "
        f"The federal 25C heat pump tax credit does not apply to property placed in service after Dec 31, 2025 (IRS). Since Sept 1, 2026, new federal HEAR rebate reservations can't fund fuel switching unless the existing fossil system stays (DOE Program Notice 26-2).\n\n"
        f"Formula: heat pump yearly cost = heat needed (Btu) / 3412 / COP × $/kWh; COP ≈ HSPF2/3.412 with a climate adjustment. Details: {BASE}/methodology/. Machine-readable prices: {BASE}/assets/prices.json\n\n"
        f"Prefilled links: the calculator reads URL parameters, e.g. {BASE}/?state=ME&fuel=oil&sqft=1800&ins=avg (state = 2-letter code; fuel = oil|propane|gas|elec; mode=usage&amount=N for last winter's fuel use; optional eff, hspf2, cop, fp = fuel price, ep = $/kWh). It runs on open.\n\n## Tools and guides\n\n" +
        "".join(f"- [{t}]({BASE}{p}): {d}\n" for p, t, d, _ in core) +
        "\n## State pages\n\n" + "".join(f"- [{s['name']}]({BASE}/state/{s['slug']}/): electricity {s['elec']:.2f}¢/kWh, oil ${s['oil']:.2f}, propane ${s['propane']:.2f}, gas ${s['gas_therm']:.2f}/therm\n" for s in STATES) +
        "\n## About\n\n" + "".join(f"- [{t}]({BASE}{p}): {d}\n" for p, t, d, _ in PAGES if p in trust) +
        f"\n## Optional\n\n- [Full text of all pages]({BASE}/llms-full.txt)\n")
(OUT / "llms.txt").write_text(llms)
(OUT / "llms-full.txt").write_text(f"# {SITE} – full text\n\nSource: {BASE}/ · Updated {UPDATED}\n\n" + "\n\n".join(f"## {t}\nURL: {BASE}{p}\n\n" + " ".join(b.split()) for p, t, d, b in PAGES))
(OUT / f"{INDEXNOW_KEY}.txt").write_text(INDEXNOW_KEY)
import og_images
og_images.build(OUT / "assets" / "og", STATES, META, calc, money, low, BASE)
(OUT / ".nojekyll").write_text("")
print(f"Built {len(PAGES)} pages to {OUT} for {BASE} (prefix {PREFIX!r})")
