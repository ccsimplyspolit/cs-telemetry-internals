#!/usr/bin/env bash
# Map every admin endpoint extracted from the panel HTML.
# Records 401 vs 404 to confirm which routes actually exist.
# Uses no auth — everything should be 401 (auth-gated) or 404 (missing).
set -u
HOST_GC="${HOST_GC:-gc.project446.su}"

routes=(
  "GET  /auth/me"
  "GET  /auth/login"
  "POST /auth/logout"
  "GET  /auth-check"
  "GET  /api/admin/beta/"
  "POST /api/admin/beta/invite"
  "POST /api/admin/beta/import"
  "DELETE /api/admin/beta/76561198000000000"
  "GET  /api/admin/penalties"
  "POST /api/admin/penalties/76561198000000000"
  "DELETE /api/admin/penalties/76561198000000000"
  "DELETE /api/admin/penalties/all"
  "GET  /api/admin/profile/76561198000000000"
  "PUT  /api/admin/profile/76561198000000000"
  "GET  /api/admin/inventory/76561198000000000"
  "PUT  /api/admin/inventory/76561198000000000"
  "DELETE /api/admin/inventory/76561198000000000/items"
  "POST /api/admin/inventory/76561198000000000/import"
  "GET  /api/admin/inventory/76561198000000000/export"
  "POST /api/admin/inventory/76561198000000000/grant"
  "GET  /api/admin/servers/"
  "POST /api/admin/servers/"
  "POST /api/admin/servers/bulk"
  "PUT  /api/admin/servers/1"
  "PUT  /api/admin/servers/1/ban"
  "PUT  /api/admin/servers/1/unban"
  "DELETE /api/admin/servers/1"
  "GET  /api/admin/matchmaking/config"
  "POST /api/admin/matchmaking/config"
  "GET  /api/admin/matchmaking/searching"
  "GET  /api/admin/matchmaking/live-servers"
  "POST /api/admin/matchmaking/live-servers/1/block"
  "DELETE /api/admin/matchmaking/live-servers/1/block"
  "POST /api/admin/matchmaking/force"
  "GET  /api/admin/drops/config"
  "PUT  /api/admin/drops/config"
  "GET  /api/admin/whitelist/"
  "POST /api/admin/whitelist/"
  "DELETE /api/admin/whitelist/76561198000000000"
  "GET  /api/admin/patrol/"
  "POST /api/admin/patrol/"
  "PUT  /api/admin/patrol/76561198000000000"
  "DELETE /api/admin/patrol/76561198000000000"
  "POST /api/admin/patrol/76561198000000000/send"
  "GET  /api/admin/update/status"
  "POST /api/admin/update/publish"
  "POST /api/admin/update/notify"
  "GET  /api/admin/users"
  "POST /api/admin/prime/all"
  "POST /api/replays/upload/foo"
  "GET  /api/server/fleet/1"
  "GET  /api/update/download"
  "GET  /api/update/manifest"
)

printf "%-6s %-55s %-6s %s\n" "CODE" "PATH" "SIZE" "TYPE"
for entry in "${routes[@]}"; do
    method="${entry%% *}"
    path="${entry#* }"; path="${path# }"
    ret=$(curl -s --max-time 5 -X "$method" \
        -A "Mozilla/5.0" \
        -H "Content-Type: application/json" \
        -o /tmp/p446_body \
        -w '%{http_code}|%{size_download}|%{content_type}' \
        "https://${HOST_GC}${path}")
    code="${ret%%|*}"
    rest="${ret#*|}"
    size="${rest%%|*}"
    ct="${rest#*|}"
    label=""
    case "$code" in
      401) label="AUTH"  ;;
      404) label="MISS"  ;;
      405) label="M-N-A" ;;
      308) label="REDIR" ;;
      200) label="!!! OPEN"  ;;
    esac
    printf "%-6s %-55s %-6s %s  %s\n" "$code" "$path" "$size" "$label" "$ct"
done
