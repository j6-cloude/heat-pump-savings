"""Static 1200x630 Open Graph preview PNGs, built at build time with Pillow (generic + one per state)."""
from PIL import Image, ImageDraw, ImageFont
import pathlib, glob

W, H = 1200, 630
BG, INK, MUTED, ACC, ACCD, TEAL, TEALS, SOFT, LINE = "#fbf7f1", "#1f2328", "#575d66", "#c8551f", "#a3431a", "#0f6b63", "#eaf5f3", "#fdefe6", "#e7e2da"
GOOD, BAD = "#0b5a3c", "#8a2d10"
_NOTO = (glob.glob("/usr/share/fonts/truetype/sand-box/google/Noto Sans/NotoSans-VariableFont_wdth,wght.ttf") or [None])[0]

def font(size, bold=False):
    if _NOTO:
        try:
            f = ImageFont.truetype(_NOTO, size)
            f.set_variation_by_axes([800 if bold else 420, 100])
            return f
        except Exception:
            pass
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else ""), size)

def logo(d, x, y, s):
    d.rounded_rectangle([x, y, x + s, y + s], radius=int(s * 9 / 32), fill=ACC)
    k = s / 32  # flame from the site's SVG logo, approximated as a polygon
    pts = [(16, 7), (19, 10.5), (22, 14), (22, 18), (21.2, 21), (19, 23.2), (16, 24), (13, 23.2), (10.8, 21), (10, 18), (10.8, 14.5), (13, 11), (14.2, 12.6), (16, 14), (15.3, 10.5)]
    d.polygon([(x + a * k, y + b * k) for a, b in pts], fill="#fff")

def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    return lines + ([cur] if cur else [])

def frame(base_url):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 14, H], fill=ACC)
    logo(d, 64, 48, 60)
    d.text((140, 56), "Heat Pump Savings Check", font=font(34, True), fill=INK)
    host = base_url.split("://", 1)[-1]
    d.rectangle([0, H - 74, W, H], fill=TEALS)
    d.text((64, H - 54), host, font=font(28, True), fill=TEAL)
    t = "Free · independent · EIA prices"
    f = font(24); d.text((W - 64 - d.textlength(t, font=f), H - 51), t, font=f, fill=MUTED)
    return im, d

def generic(path, META, calc, money, base_url):
    im, d = frame(base_url)
    y = 150
    for ln in wrap(d, "Will a heat pump cost less than your heat now?", font(68, True), 1060):
        d.text((64, y), ln, font=font(68, True), fill=INK); y += 82
    y += 14
    d.text((64, y), "Oil, propane, gas or electric heat vs a heat pump,", font=font(32), fill=MUTED); y += 44
    d.text((64, y), "with this winter's prices for all 50 states + DC.", font=font(32), fill=MUTED); y += 66
    r = calc("MA", "oil")
    d.rounded_rectangle([64, y, 1136, y + 100], radius=22, fill=SOFT)
    d.text((92, y + 18), f"Example: Massachusetts oil home could save {money(r['save'])}/year", font=font(34, True), fill=ACCD)
    d.text((92, y + 62), f"2,000 sq ft · heat pump HSPF2 8.5 · heating oil ${META['oil_us']:.2f}/gal (EIA, week of {META['oil_date']})", font=font(22), fill=MUTED)
    im.quantize(colors=128, method=Image.Quantize.MEDIANCUT).save(path, optimize=True)

def state(path, s, META, calc, money, low, base_url):
    im, d = frame(base_url)
    d.text((64, 140), f"Heat pump savings in {s['name']}", font=font(58 if len(s['name']) < 15 else 50, True), fill=INK)
    d.text((64, 216), "Yearly running cost, 2,000 sq ft home, heat pump HSPF2 8.5", font=font(26), fill=MUTED)
    names = {"oil": "Heating oil", "propane": "Propane", "gas": "Natural gas", "elec": "Electric baseboard"}
    y = 268
    for f in ("oil", "propane", "gas", "elec"):
        r = calc(s["abbr"], f)
        d.rounded_rectangle([64, y, 1136, y + 62], radius=16, fill="#ffffff", outline=LINE, width=2)
        d.text((88, y + 13), names[f], font=font(30, True), fill=INK)
        if low(r): txt, col = "Little heating needed", MUTED
        elif r["save"] >= 0: txt, col = f"Heat pump saves {money(r['save'])}/yr", GOOD
        else: txt, col = f"Heat pump costs {money(-r['save'])} more/yr", BAD
        fo = font(30, True); d.text((1112 - d.textlength(txt, font=fo), y + 13), txt, font=fo, fill=col)
        y += 72
    im.quantize(colors=128, method=Image.Quantize.MEDIANCUT).save(path, optimize=True)

def build(outdir, STATES, META, calc, money, low, base_url):
    outdir = pathlib.Path(outdir); (outdir / "state").mkdir(parents=True, exist_ok=True)
    generic(outdir / "og.png", META, calc, money, base_url)
    for s in STATES: state(outdir / "state" / f"{s['slug']}.png", s, META, calc, money, low, base_url)
