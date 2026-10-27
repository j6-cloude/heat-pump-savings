#!/usr/bin/env bash
# Usage: BASE_URL=https://yourdomain.com ./indexnow_ping.sh
# Submits every URL in the live sitemap to IndexNow (Bing, Yandex, Seznam, Naver share submissions).
# Run only AFTER the site is live at BASE_URL and https://$HOST/<key>.txt is reachable.
set -euo pipefail
BASE_URL="${BASE_URL:?set BASE_URL, e.g. https://j6-cloude.github.io/heat-pump-savings}"
KEY="$(cat "$(dirname "$0")/.indexnow_key")"
HOST="$(echo "$BASE_URL" | sed -E 's#https?://([^/]+).*#\1#')"
URLS=$(curl -fsSL "$BASE_URL/sitemap.xml" | grep -o '<loc>[^<]*</loc>' | sed -E 's#</?loc>##g' | python3 -c 'import sys,json;print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))')
curl -sS -o /tmp/indexnow_resp.txt -w "IndexNow HTTP %{http_code}\n" -X POST "https://api.indexnow.org/indexnow" \
  -H 'Content-Type: application/json; charset=utf-8' \
  -d "{\"host\":\"$HOST\",\"key\":\"$KEY\",\"keyLocation\":\"$BASE_URL/$KEY.txt\",\"urlList\":$URLS}"
# 200/202 = accepted. 403 = key file not reachable. 422 = URLs don't match host.
