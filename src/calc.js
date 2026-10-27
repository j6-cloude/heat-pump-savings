/* Heat Pump Savings Check calculator. Mirrors calc() in src/build.py. All math runs in your browser. */
(function () {
  var D = window.HPS, BTU = { oil: 138500, propane: 91452, gas: 100000, elec: 3412 };
  var UNIT = { oil: "gallons", propane: "gallons", gas: "therms", elec: "kWh" };
  var EFF = { oil: 83, propane: 90, gas: 90, elec: 100 };
  var F = { tight: 3, avg: 4, leaky: 5.5 };
  function st(ab) { for (var i = 0; i < D.states.length; i++) if (D.states[i].abbr === ab) return D.states[i]; return D.states[0]; }
  function climate(hdd) { return hdd < 3000 ? 1.05 : hdd < 5000 ? 1.0 : hdd < 7000 ? 0.9 : 0.8; }
  function price(s, fuel) { return fuel === "oil" ? s.oil : fuel === "propane" ? s.propane : fuel === "gas" ? s.gas_therm : s.elec / 100; }
  // returns everything the page shows; same formula as build.py calc()
  function calc(o) {
    var s = st(o.state);
    var need = o.mode === "usage" ? o.amount * BTU[o.fuel] * (o.eff / 100) : o.sqft * s.hdd * F[o.ins];   // delivered heat, Btu/yr
    var cop = o.cop > 0 ? o.cop : (o.hspf2 / 3.412) * climate(s.hdd);
    var fuelUnits = need / (BTU[o.fuel] * (o.eff / 100));
    var now = fuelUnits * o.fuelPrice;
    var hpKwh = need / 3412 / cop, hp = hpKwh * o.elecPrice;
    var perNow = o.fuelPrice / (BTU[o.fuel] * o.eff / 100) * 1e6, perHp = o.elecPrice / (3412 * cop) * 1e6;
    var breakeven = o.fuelPrice / (BTU[o.fuel] * o.eff / 100) * 3412 * cop; // $/kWh where costs are equal
    return { need: need, cop: cop, fuelUnits: fuelUnits, now: now, hpKwh: hpKwh, hp: hp, save: now - hp, perNow: perNow, perHp: perHp, breakeven: breakeven };
  }
  window.HPScalc = calc;
  function $(r, n) { return r.querySelector('[name="' + n + '"]'); }
  function m(x) { return (x < 0 ? "-$" : "$") + Math.abs(Math.round(x)).toLocaleString("en-US"); }
  function n0(x) { return Math.round(x).toLocaleString("en-US"); }
  var LOW_NEED = 2e6; // Btu/yr delivered heat; below this say "little heating needed" (same as build.py)
  var FUELS = ["oil", "propane", "gas", "elec"], INS = ["tight", "avg", "leaky"];
  var FNAME = { oil: "heating oil", propane: "propane", gas: "natural gas", elec: "electric baseboard/furnace" };
  var INSNAME = { tight: "good insulation", avg: "average insulation", leaky: "drafty home" };
  var SITE_URL = "j6-cloude.github.io/heat-pump-savings";
  // ---- URL params: read, validate, sanitize. Only whitelisted keys, numbers clamped to the form's ranges. ----
  var NUM = { sqft: [200, 20000], amount: [0, 100000], eff: [40, 100], hspf2: [5, 14], cop: [0, 6], fp: [0, 100], ep: [0, 5] };
  function readParams() {
    var q, out = {};
    try { q = new URLSearchParams(location.search); } catch (e) { return out; }
    var stv = (q.get("state") || "").trim().toUpperCase().slice(0, 2);
    if (/^[A-Z]{2}$/.test(stv) && D.states.some(function (s) { return s.abbr === stv; })) out.state = stv;
    var f = (q.get("fuel") || "").trim().toLowerCase(); if (FUELS.indexOf(f) >= 0) out.fuel = f;
    var md = (q.get("mode") || "").trim().toLowerCase(); if (md === "size" || md === "usage") out.mode = md;
    var ins = (q.get("ins") || "").trim().toLowerCase(); if (INS.indexOf(ins) >= 0) out.ins = ins;
    Object.keys(NUM).forEach(function (k) {
      var v = (q.get(k) || "").trim();
      if (!/^\d{1,6}(\.\d{1,4})?$/.test(v)) return;
      var x = parseFloat(v); if (!isFinite(x)) return;
      out[k] = Math.min(NUM[k][1], Math.max(NUM[k][0], x));
    });
    if (out.sqft) out.sqft = Math.round(out.sqft);
    return out;
  }
  var PARAMS = readParams(), usedParams = false;
  function fmtPrice(f, v) { return f === "elec" ? "$" + v.toFixed(3) + "/kWh" : f === "gas" ? "$" + v.toFixed(2) + "/therm" : "$" + v.toFixed(2) + "/gal"; }
  function fuelPriceDate(f) { return f === "oil" ? "EIA weekly, week of " + D.meta.oil_date : f === "propane" ? "EIA weekly, week of " + D.meta.propane_date : f === "gas" ? "EIA, Nov 2025–Mar 2026 avg" : "EIA, Jan–Aug 2026 avg"; }
  // ---- share card (canvas, 1200x630, site colors) ----
  function wrap(ctx, text, maxw) {
    var words = text.split(" "), lines = [], cur = "";
    words.forEach(function (w) { var t = cur ? cur + " " + w : w; if (ctx.measureText(t).width <= maxw || !cur) cur = t; else { lines.push(cur); cur = w; } });
    if (cur) lines.push(cur); return lines;
  }
  function rrect(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }
  var FF = 'system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans",sans-serif';
  // playful tiers (positive savings only); names are just for fun
  function tierFor(save) { return save >= 750 ? { name: "Heat Pump Hero", emoji: "\u2605\u2605\u2605" } : save >= 300 ? { name: "Winter Winner", emoji: "\u2605\u2605" } : save >= 50 ? { name: "Cozy Saver", emoji: "\u2605" } : null; }
  var CONF = ["#c8551f", "#e8a33d", "#0f6b63", "#f2c94c", "#e07a5f", "#7fb8a4"];
  function rng(seed) { return function () { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; }; }
  function star(x, cx, cy, r) { x.beginPath(); for (var i = 0; i < 10; i++) { var a = -Math.PI / 2 + i * Math.PI / 5, rr = i % 2 ? r * 0.45 : r; x.lineTo(cx + rr * Math.cos(a), cy + rr * Math.sin(a)); } x.closePath(); }
  function drawCard(c, info) {
    c.width = 1200; c.height = 630; var x = c.getContext("2d"), fest = info.kind === "save";
    // warm background with a soft glow
    x.fillStyle = "#fbf7f1"; x.fillRect(0, 0, 1200, 630);
    var g = x.createRadialGradient(330, 250, 40, 330, 250, 720);
    g.addColorStop(0, fest ? "#fff1dc" : "#f4efe6"); g.addColorStop(1, "#fbf7f1"); x.fillStyle = g; x.fillRect(0, 0, 1200, 630);
    if (fest) { // confetti sprinkles kept to the edges, away from the text
      var R = rng(42 + (info.big.length * 7));
      var ok = function (px, py) { return py < 26 || py > 620 || px < 34 || px > 1168 || (px > 1010 && py < 190) || (px > 590 && px < 660 && py < 100) || (px > 700 && py > 560); };
      for (var i = 0; i < 260; i++) {
        var px = R() * 1200, py = R() * 630;
        if (!ok(px, py)) continue;
        x.save(); x.translate(px, py); x.rotate(R() * Math.PI); x.fillStyle = CONF[i % CONF.length]; x.globalAlpha = 0.85;
        var k = R(); if (k < 0.45) x.fillRect(-9, -4, 18, 8); else if (k < 0.75) { x.beginPath(); x.arc(0, 0, 5 + R() * 3, 0, 7); x.fill(); } else { star(x, 0, 0, 9 + R() * 4); x.fill(); }
        x.restore();
      }
    }
    // logo + name
    x.save(); x.translate(64, 44); x.scale(56 / 32, 56 / 32); rrect(x, 0, 0, 32, 32, 9); x.fillStyle = "#c8551f"; x.fill();
    if (window.Path2D) { x.fillStyle = "#fff"; x.fill(new Path2D("M16 7c3 4 6 6 6 11a6 6 0 0 1-12 0c0-3 2-5 3-7 1 2 2 3 3 3-1-3-1-5 0-7z")); } x.restore();
    x.textBaseline = "alphabetic"; x.fillStyle = "#1f2328"; x.font = "800 32px " + FF; x.fillText("Heat Pump Savings Check", 136, 84);
    // tier sticker (tilted, rounded: playful, not a seal) or state label
    if (info.tier) {
      x.save(); x.translate(968, 92); x.rotate(-0.06);
      x.font = "800 30px " + FF; var tw = x.measureText(info.tier.name).width, w = tw + 104;
      x.fillStyle = "rgba(200,85,31,.18)"; rrect(x, -w / 2 + 5, -33, w, 70, 35); x.fill();
      x.fillStyle = "#e8a33d"; rrect(x, -w / 2, -38, w, 70, 35); x.fill();
      x.fillStyle = "#fff"; star(x, -w / 2 + 40, -3, 17); x.fill();
      x.fillStyle = "#3d2100"; x.fillText(info.tier.name, -w / 2 + 68, 8);
      x.restore();
      x.fillStyle = "#575d66"; x.font = "600 22px " + FF; var tl = "Our badge \u00b7 " + info.state; x.fillText(tl, 968 - x.measureText(tl).width / 2, 160);
    } else { x.fillStyle = "#575d66"; x.font = "500 26px " + FF; x.fillText(info.state, 1136 - x.measureText(info.state).width, 84); }
    // hero
    x.fillStyle = "#1f2328"; x.font = "800 46px " + FF; x.fillText(info.line1, 64, 196);
    var bs = 112; x.font = "900 " + bs + "px " + FF; while (x.measureText(info.big).width > 1072 && bs > 60) { bs -= 4; x.font = "900 " + bs + "px " + FF; }
    if (fest) { x.fillStyle = "rgba(232,163,61,.35)"; rrect(x, 54, 300 - bs * 0.32, x.measureText(info.big).width + 22, bs * 0.34, 10); x.fill(); }
    x.fillStyle = info.color; x.fillText(info.big, 60, 300);
    x.fillStyle = "#575d66"; x.font = "500 27px " + FF;
    wrap(x, info.sub, 1072).slice(0, 2).forEach(function (l, i) { x.fillText(l, 64, 354 + i * 35); });
    // assumptions
    x.fillStyle = "#eaf5f3"; rrect(x, 64, 408, 1072, 132, 22); x.fill();
    x.fillStyle = "#0f6b63"; x.font = "800 19px " + FF; x.fillText("OUR NUMBERS", 90, 440);
    x.fillStyle = "#1f2328"; x.font = "500 21px " + FF;
    wrap(x, info.assume, 1020).slice(0, 3).forEach(function (l, i) { x.fillText(l, 90, 470 + i * 28); });
    // footer: URL + plain disclaimer
    x.fillStyle = "#0f6b63"; x.font = "800 27px " + FF; x.fillText(SITE_URL, 64, 578);
    x.fillStyle = "#575d66"; x.font = "500 19px " + FF;
    x.fillText("Estimate only, based on your inputs and EIA prices; not an official document.", 64, 608);
  }
  function cardInfo(o, r, touched) {
    var s = st(o.state), low = r.need < LOW_NEED, fn = FNAME[o.fuel];
    var info = { state: s.name, kind: "even" };
    if (low) { info.line1 = "In our climate, our home needs"; info.big = "Little heating"; info.color = "#6b4500";
      info.sub = (r.now < 50 && r.hp < 50) ? "Heating costs are close to $0 a year either way. A heat pump here is mostly about efficient cooling." : "Heating costs about " + m(r.now) + " a year now and about " + m(r.hp) + " with a heat pump, so the difference is small."; }
    else if (r.save >= 0) { info.kind = r.save >= 50 ? "save" : "even"; info.tier = tierFor(r.save); info.line1 = "Our home could save"; info.big = m(r.save) + "/year"; info.color = "#0b5a3c";
      info.sub = "by switching from " + fn + " (about " + m(r.now) + "/yr) to a heat pump (about " + m(r.hp) + "/yr in electricity)."; }
    else { info.kind = "cost"; info.line1 = "Good to know: a heat pump could cost us"; info.big = m(-r.save) + " more/yr"; info.color = "#8a2d10";
      info.sub = "At today's prices " + fn + " is cheaper to run here (about " + m(r.now) + "/yr vs " + m(r.hp) + "/yr). Better insulation or a higher-efficiency heat pump can change that."; }
    var size = o.mode === "usage" ? n0(o.amount) + " " + UNIT[o.fuel] + " of " + (o.fuel === "elec" ? "electricity" : o.fuel === "gas" ? "gas" : o.fuel) + " last winter" : n0(o.sqft) + " sq ft, " + INSNAME[o.ins];
    var effTxt = o.fuel === "elec" ? "" : " at " + o.eff + "% efficiency";
    var pd = (touched.fuelPrice ? "your price" : fuelPriceDate(o.fuel));
    info.assume = s.name + " · " + FNAME[o.fuel].charAt(0).toUpperCase() + FNAME[o.fuel].slice(1) + " " + fmtPrice(o.fuel, o.fuelPrice) + effTxt + " (" + pd + ") · " + size +
      " · Heat pump " + (o.cop > 0 ? "COP " + o.cop : "HSPF2 " + o.hspf2 + " (COP " + r.cop.toFixed(2) + " used)") +
      " · Electricity $" + o.elecPrice.toFixed(3) + "/kWh (" + (touched.elecPrice ? "your price" : "EIA, Jan–Aug 2026 avg") + ")";
    return info;
  }
  function shareUrl(o, touched) {
    var s = st(o.state), q = ["state=" + o.state, "fuel=" + o.fuel];
    if (o.mode === "usage") q.push("mode=usage", "amount=" + o.amount); else q.push("sqft=" + o.sqft, "ins=" + o.ins);
    if (o.eff !== EFF[o.fuel]) q.push("eff=" + o.eff);
    if (o.hspf2 !== 8.5) q.push("hspf2=" + o.hspf2);
    if (o.cop > 0) q.push("cop=" + o.cop);
    if (touched.fuelPrice && Math.abs(o.fuelPrice - price(s, o.fuel)) > 0.0005) q.push("fp=" + o.fuelPrice);
    if (touched.elecPrice && Math.abs(o.elecPrice - s.elec / 100) > 0.00005) q.push("ep=" + o.elecPrice);
    return location.origin + location.pathname + "?" + q.join("&");
  }
  function shareText(o, r) {
    var s = st(o.state);
    if (r.need < LOW_NEED) return "Our home in " + s.name + " needs little heating, so a heat pump changes the heating bill very little. Free estimate:";
    return (r.save >= 0 ? (tierFor(r.save) ? tierFor(r.save).name + "! " : "") + "Our home could save " + m(r.save) + " a year by switching from " + FNAME[o.fuel] + " to a heat pump" : "A heat pump could cost our home " + m(-r.save) + " more a year than " + FNAME[o.fuel]) + " in " + s.name + " (free estimate, EIA prices):";
  }
  // page confetti: only for a savings result, only after a prefilled link or user input, never with reduced motion
  function reducedMotion() { return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches); }
  var confettiOn = false;
  function confetti() {
    if (confettiOn || reducedMotion() || !window.requestAnimationFrame) return;
    var cv = document.createElement("canvas"), W = window.innerWidth, H = window.innerHeight, dpr = Math.min(2, window.devicePixelRatio || 1);
    cv.className = "confetti"; cv.setAttribute("aria-hidden", "true"); cv.width = W * dpr; cv.height = H * dpr;
    document.body.appendChild(cv); confettiOn = true;
    var x = cv.getContext("2d"); x.scale(dpr, dpr);
    var P = [], n = Math.min(140, Math.round(W / 4)), t0 = null, DUR = 2600;
    for (var i = 0; i < n; i++) P.push({ x: Math.random() * W, y: -20 - Math.random() * H * 0.5, vx: (Math.random() - 0.5) * 2.4, vy: 2 + Math.random() * 3.5, r: Math.random() * 6.3, vr: (Math.random() - 0.5) * 0.3, s: 6 + Math.random() * 7, c: CONF[i % CONF.length], k: Math.random() });
    function f(ts) {
      if (t0 === null) t0 = ts; var t = ts - t0; x.clearRect(0, 0, W, H);
      x.globalAlpha = t > DUR - 600 ? Math.max(0, (DUR - t) / 600) : 1;
      P.forEach(function (p) { p.x += p.vx; p.y += p.vy; p.vy += 0.05; p.r += p.vr; x.save(); x.translate(p.x, p.y); x.rotate(p.r); x.fillStyle = p.c;
        if (p.k < 0.6) x.fillRect(-p.s / 2, -p.s / 4, p.s, p.s / 2); else { x.beginPath(); x.arc(0, 0, p.s / 3, 0, 7); x.fill(); } x.restore(); });
      if (t < DUR) requestAnimationFrame(f); else { cv.remove(); confettiOn = false; }
    }
    requestAnimationFrame(f);
  }
  document.querySelectorAll(".hp-calc").forEach(function (root, idx) {
    var sel = $(root, "state");
    D.states.forEach(function (s) { var op = document.createElement("option"); op.value = s.abbr; op.textContent = s.name; sel.appendChild(op); });
    sel.value = root.dataset.state || "MA";
    $(root, "fuel").value = root.dataset.fuel || "oil";
    var touched = {};
    ["fuelPrice", "elecPrice", "eff"].forEach(function (k) { $(root, k).addEventListener("input", function () { touched[k] = true; }); });
    function prefill(force) {
      var s = st(sel.value), f = $(root, "fuel").value;
      if (force || !touched.fuelPrice) $(root, "fuelPrice").value = price(s, f).toFixed(3);
      if (force || !touched.elecPrice) $(root, "elecPrice").value = (s.elec / 100).toFixed(4);
      if (force || !touched.eff) $(root, "eff").value = EFF[f];
      root.querySelectorAll(".unit").forEach(function (e) { e.textContent = UNIT[f]; });
      root.querySelector(".punit").textContent = f === "gas" ? "per therm" : f === "elec" ? "per kWh" : "per gallon";
    }
    var share = root.querySelector(".share"), canvas = document.createElement("canvas"), blob = null, blobUrl = null, timer = null, last = null, lastTier = null, armed = false;
    if (!root.querySelector(".tier") && root.querySelector(".out .verdict")) { var te = document.createElement("p"); te.className = "tier"; te.hidden = true; root.querySelector(".out .verdict").after(te); }
    function renderShare() {
      if (!share || !last) return;
      var o = last.o, r = last.r, url = shareUrl(o, touched), text = shareText(o, r);
      var info = cardInfo(o, r, touched); drawCard(canvas, info);
      share.hidden = false; share.dataset.kind = info.kind;
      var tierEl = root.querySelector(".tier");
      if (tierEl) { tierEl.hidden = !info.tier; tierEl.textContent = info.tier ? "\u2605 Your badge: " + info.tier.name + " \u2605" : ""; }
      var key = info.tier ? info.tier.name : "";
      if (key && key !== lastTier && armed) confetti();
      lastTier = key; root.dataset.tier = key;
      share.querySelector(".s-link").value = url;
      share.querySelector(".s-fb").href = "https://www.facebook.com/sharer/sharer.php?u=" + encodeURIComponent(url);
      share.querySelector(".s-sms").href = "sms:?&body=" + encodeURIComponent(text + " " + url);
      share.querySelector(".s-wa").href = "https://wa.me/?text=" + encodeURIComponent(text + " " + url);
      share.dataset.url = url; share.dataset.text = text;
      var done = function (b) {
        blob = b; if (blobUrl) URL.revokeObjectURL(blobUrl);
        blobUrl = URL.createObjectURL(b);
        share.querySelector(".share-img").src = blobUrl; share.querySelector(".s-dl").href = blobUrl;
        share.querySelector(".s-dl").download = "heat-pump-savings-" + o.state.toLowerCase() + "-" + o.fuel + ".png";
      };
      if (canvas.toBlob) canvas.toBlob(function (b) { if (b) done(b); }, "image/png");
    }
    if (share) {
      var nat = share.querySelector(".s-native"), status = share.querySelector(".s-status");
      if (navigator.share) nat.hidden = false;
      nat.addEventListener("click", function () {
        var url = share.dataset.url, text = share.dataset.text, title = "Heat Pump Savings Check";
        var file = null;
        try { if (blob && window.File) file = new File([blob], "heat-pump-savings.png", { type: "image/png" }); } catch (e) { file = null; }
        var p;
        if (file && navigator.canShare && navigator.canShare({ files: [file] })) p = navigator.share({ files: [file], title: title, text: text + " " + url });
        else p = navigator.share({ title: title, text: text, url: url });
        p.catch(function (e) { if (e && e.name !== "AbortError") status.textContent = "Sharing didn't work here. Try Copy link."; });
      });
      share.querySelector(".s-copy").addEventListener("click", function () {
        var url = share.dataset.url, inp = share.querySelector(".s-link");
        var ok = function () { status.textContent = "Link copied."; }, fallback = function () { inp.focus(); inp.select(); try { document.execCommand("copy"); ok(); } catch (e) { status.textContent = "Select the link below and copy it."; } };
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(ok, fallback); else fallback();
      });
      share.querySelector(".s-dl").addEventListener("click", function (e) { if (!blobUrl) { e.preventDefault(); renderShare(); } });
      ["s-fb", "s-wa", "s-sms"].forEach(function (c) { share.querySelector("." + c).addEventListener("click", function (e) { if (share.querySelector("." + c).getAttribute("href") === "#") e.preventDefault(); }); });
    }
    function run() {
      var mode = root.querySelector('input[name="mode"]:checked').value;
      root.querySelector(".m-size").hidden = mode !== "size"; root.querySelector(".m-usage").hidden = mode !== "usage";
      var o = { state: sel.value, fuel: $(root, "fuel").value, mode: mode, sqft: +$(root, "sqft").value || 0, ins: $(root, "ins").value,
        amount: +$(root, "amount").value || 0, eff: +$(root, "eff").value || 100, hspf2: +$(root, "hspf2").value || 8.5, cop: +$(root, "cop").value || 0,
        fuelPrice: +$(root, "fuelPrice").value || 0, elecPrice: +$(root, "elecPrice").value || 0 };
      var r = calc(o), out = root.querySelector(".out"), name = FNAME[o.fuel];
      var pct = r.now > 0 ? r.save / r.now : 0, v = out.querySelector(".verdict"), low = r.need < LOW_NEED;
      v.className = "verdict " + (low ? "even" : pct > 0.1 ? "good" : pct < -0.1 ? "bad" : "even");
      v.textContent = low ? "Little heating needed: this climate or home needs very little heat, so the yearly difference is small." : pct > 0.1 ? "A heat pump would likely cost less to run." : pct < -0.1 ? "A heat pump would likely cost more to run at these prices." : "It's close: about the same cost either way.";
      out.querySelector(".big").textContent = low ? "Little heating needed" : (r.save >= 0 ? "Save " : "Pay ") + m(Math.abs(r.save)) + (r.save >= 0 ? "" : " more") + " a year";
      out.querySelector(".sentence").textContent = "Heating with " + name + " costs about " + m(r.now) + " a year. A heat pump would cost about " + m(r.hp) + " a year in electricity." + (low ? " A heat pump may still make sense for summer cooling." : "");
      out.querySelector(".k-now").textContent = m(r.now); out.querySelector(".k-hp").textContent = m(r.hp);
      out.querySelector(".k-units").textContent = n0(r.fuelUnits) + " " + UNIT[o.fuel]; out.querySelector(".k-kwh").textContent = n0(r.hpKwh) + " kWh";
      out.querySelector(".k-cop").textContent = r.cop.toFixed(2); out.querySelector(".k-be").textContent = "$" + r.breakeven.toFixed(3) + "/kWh";
      out.querySelector(".k-per").textContent = "$" + r.perNow.toFixed(2) + " vs $" + r.perHp.toFixed(2);
      out.querySelector(".k-need").textContent = (r.need / 1e6).toFixed(1) + " million Btu";
      last = { o: o, r: r };
      root.dataset.save = Math.round(r.save); root.dataset.now = Math.round(r.now); root.dataset.hp = Math.round(r.hp);
      clearTimeout(timer); timer = setTimeout(renderShare, 250);
    }
    sel.addEventListener("change", function () { prefill(true); run(); });
    $(root, "fuel").addEventListener("change", function () { touched.eff = false; touched.fuelPrice = false; prefill(false); run(); });
    root.addEventListener("input", function () { armed = true; }, true); root.addEventListener("change", function () { armed = true; }, true);
    root.addEventListener("input", run); root.addEventListener("change", run);
    // apply URL params to the first calculator on the page
    var P = PARAMS;
    if (idx === 0 && Object.keys(P).length) {
      usedParams = true; armed = true;
      if (P.state) sel.value = P.state;
      if (P.fuel) $(root, "fuel").value = P.fuel;
      prefill(true);
      if (P.mode) root.querySelectorAll('input[name="mode"]').forEach(function (e) { e.checked = e.value === P.mode; });
      else if (P.amount !== undefined && P.sqft === undefined) root.querySelectorAll('input[name="mode"]').forEach(function (e) { e.checked = e.value === "usage"; });
      if (P.sqft !== undefined) $(root, "sqft").value = P.sqft;
      if (P.ins) $(root, "ins").value = P.ins;
      if (P.amount !== undefined) $(root, "amount").value = P.amount;
      if (P.eff !== undefined) { $(root, "eff").value = P.eff; touched.eff = true; }
      if (P.hspf2 !== undefined) $(root, "hspf2").value = P.hspf2;
      if (P.cop !== undefined && P.cop > 0) $(root, "cop").value = P.cop;
      if (P.fp !== undefined) { $(root, "fuelPrice").value = P.fp; touched.fuelPrice = true; }
      if (P.ep !== undefined) { $(root, "elecPrice").value = P.ep; touched.elecPrice = true; }
      run();
      if (root.scrollIntoView) setTimeout(function () { root.scrollIntoView({ block: "start" }); }, 50);
    } else { prefill(true); run(); }
  });
  // mini-split sizer
  document.querySelectorAll(".hp-size").forEach(function (root) {
    function run() {
      var a = +$(root, "sqft").value || 0, f = F[$(root, "ins").value], t = +$(root, "t").value;
      var btuh = a * f / 24 * (65 - t);
      root.querySelector(".big").textContent = n0(Math.round(btuh / 1000) * 1000) + " Btu/hr";
      root.querySelector(".sentence").textContent = "That is about " + (btuh / 12000).toFixed(1) + " tons. Look for a heat pump that still makes at least this much heat at " + t + "°F (check the spec sheet or the NEEP list).";
    }
    root.addEventListener("input", run); run();
  });
  // payback
  document.querySelectorAll(".hp-pay").forEach(function (root) {
    function run() {
      var c = +$(root, "cost").value || 0, r = +$(root, "rebate").value || 0, s = +$(root, "save").value || 0, net = Math.max(c - r, 0);
      root.querySelector(".big").textContent = s > 0 ? (net / s).toFixed(1) + " years" : "No payback";
      root.querySelector(".sentence").textContent = s > 0 ? "You pay " + m(net) + " after rebates. Saving " + m(s) + " a year pays that back in about " + (net / s).toFixed(1) + " years." : "If the heat pump doesn't lower your yearly bill, it won't pay for itself on energy savings alone.";
    }
    root.addEventListener("input", run); run();
  });
  // HSPF2 -> COP
  document.querySelectorAll(".hp-cop").forEach(function (root) {
    function run() { var h = +$(root, "h").value || 0; root.querySelector(".big").textContent = "COP " + (h / 3.412).toFixed(2); }
    root.addEventListener("input", run); run();
  });
})();
