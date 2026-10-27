#!/usr/bin/env bash
# Re-download public EIA + NOAA files (no API keys) into data/raw, then: python3 src/build_data.py && python3 src/build.py
set -euo pipefail
cd "$(dirname "$0")/data/raw"
A="Mozilla/5.0"
curl -fsSL -A "$A" -o table_5_06_b.xlsx https://www.eia.gov/electricity/monthly/xls/table_5_06_b.xlsx
curl -fsSL -A "$A" -o table_5_06_a.xlsx https://www.eia.gov/electricity/monthly/xls/table_5_06_a.xlsx
curl -fsSL -A "$A" -o NG_PRI_SUM_A_EPG0_PRS_DMCF_M.xls https://www.eia.gov/dnav/ng/xls/NG_PRI_SUM_A_EPG0_PRS_DMCF_M.xls
curl -fsSL -A "$A" -o PET_PRI_WFR_A_EPD2F_PRS_DPGAL_W.xls https://www.eia.gov/dnav/pet/xls/PET_PRI_WFR_A_EPD2F_PRS_DPGAL_W.xls
curl -fsSL -A "$A" -o PET_PRI_WFR_A_EPLLPA_PRS_DPGAL_W.xls https://www.eia.gov/dnav/pet/xls/PET_PRI_WFR_A_EPLLPA_PRS_DPGAL_W.xls
D=https://www.ncei.noaa.gov/monitoring-content/data/us/climdiv/monthly/current
F=$(curl -fsSL "$D/" | grep -o 'climdiv-hddcst-v[0-9.]*-[0-9]*' | sort -u | tail -1)
curl -fsSL -o hddcst.txt "$D/$F"
for s in USW00026451 USW00022521 USW00013743; do
  curl -fsSL -o normals_$s.csv https://www.ncei.noaa.gov/data/normals-annualseasonal/1991-2020/access/$s.csv
done
echo "ok: $F"
