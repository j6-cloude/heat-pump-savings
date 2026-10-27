# Heat Pump Savings Check

Static site: https://j6-cloude.github.io/heat-pump-savings/ — independent tool, not affiliated with any government agency or manufacturer. Author: j6 (liu04731@gmail.com).

- `./fetch_data.sh` — download EIA/NOAA public files (no API key) to `data/raw/`
- `python3 src/build_data.py` — parse into `data/prices.json`
- `python3 src/build.py` — generate `public/` (`BASE_URL` env overrides the base)
- `BASE_URL=https://j6-cloude.github.io/heat-pump-savings ./indexnow_ping.sh` — after deploy

Branches: `main` = built site (GitHub Pages), `source` = this generator.
Ad/affiliate slots are empty placeholders (`.ad-slot`, `.affil-slot`).
