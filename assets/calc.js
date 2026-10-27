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
  document.querySelectorAll(".hp-calc").forEach(function (root) {
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
    function run() {
      var mode = root.querySelector('input[name="mode"]:checked').value;
      root.querySelector(".m-size").hidden = mode !== "size"; root.querySelector(".m-usage").hidden = mode !== "usage";
      var o = { state: sel.value, fuel: $(root, "fuel").value, mode: mode, sqft: +$(root, "sqft").value || 0, ins: $(root, "ins").value,
        amount: +$(root, "amount").value || 0, eff: +$(root, "eff").value || 100, hspf2: +$(root, "hspf2").value || 8.5, cop: +$(root, "cop").value || 0,
        fuelPrice: +$(root, "fuelPrice").value || 0, elecPrice: +$(root, "elecPrice").value || 0 };
      var r = calc(o), out = root.querySelector(".out"), name = { oil: "heating oil", propane: "propane", gas: "natural gas", elec: "electric baseboard/furnace" }[o.fuel];
      var pct = r.now > 0 ? r.save / r.now : 0, v = out.querySelector(".verdict");
      v.className = "verdict " + (pct > 0.1 ? "good" : pct < -0.1 ? "bad" : "even");
      v.textContent = pct > 0.1 ? "A heat pump would likely cost less to run." : pct < -0.1 ? "A heat pump would likely cost more to run at these prices." : "It's close: about the same cost either way.";
      out.querySelector(".big").textContent = (r.save >= 0 ? "Save " : "Pay ") + m(Math.abs(r.save)) + " a year";
      out.querySelector(".sentence").textContent = "Heating with " + name + " costs about " + m(r.now) + " a year. A heat pump would cost about " + m(r.hp) + " a year in electricity.";
      out.querySelector(".k-now").textContent = m(r.now); out.querySelector(".k-hp").textContent = m(r.hp);
      out.querySelector(".k-units").textContent = n0(r.fuelUnits) + " " + UNIT[o.fuel]; out.querySelector(".k-kwh").textContent = n0(r.hpKwh) + " kWh";
      out.querySelector(".k-cop").textContent = r.cop.toFixed(2); out.querySelector(".k-be").textContent = "$" + r.breakeven.toFixed(3) + "/kWh";
      out.querySelector(".k-per").textContent = "$" + r.perNow.toFixed(2) + " vs $" + r.perHp.toFixed(2);
      out.querySelector(".k-need").textContent = (r.need / 1e6).toFixed(1) + " million Btu";
    }
    sel.addEventListener("change", function () { prefill(true); run(); });
    $(root, "fuel").addEventListener("change", function () { touched.eff = false; touched.fuelPrice = false; prefill(false); run(); });
    root.addEventListener("input", run); root.addEventListener("change", run);
    prefill(true); run();
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
