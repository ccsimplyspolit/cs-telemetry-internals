#!/usr/bin/env bash
# CSRF risk assessment.
# Frontend uses `credentials: 'same-origin'` without CSRF token.
# We check:
#   1) Response to a cross-origin POST without cookies (baseline 401 expected).
#   2) Does the server accept cross-site content-types (JSON) after preflight?
#   3) Is Access-Control-Allow-Credentials set anywhere?
#
# NOTE: An actual CSRF PoC requires an authenticated admin session cookie
#       in a browser — this script only maps the wire protocol.
set -u
HOST_GC="${HOST_GC:-gc.project446.su}"

hdr() { printf '\n\033[36m=== %s ===\033[0m\n' "$*"; }

hdr "Preflight from evil origin"
curl -s --max-time 6 -X OPTIONS \
    -H "Origin: https://evil.example" \
    -H "Access-Control-Request-Method: DELETE" \
    -H "Access-Control-Request-Headers: content-type,x-csrf-token" \
    -o /dev/null -D - "https://${HOST_GC}/api/admin/penalties/all" | grep -iE 'access-control|http/|vary'

hdr "GET with cross-origin — check ACAO/Vary/Credentials"
curl -s --max-time 6 \
    -H "Origin: https://evil.example" \
    -o /dev/null -D - "https://${HOST_GC}/auth/me" | grep -iE 'access-control|vary|http/|set-cookie'

hdr "POST cross-origin without body (baseline 401)"
curl -s --max-time 6 -X POST \
    -H "Origin: https://evil.example" \
    -H "Content-Type: application/json" \
    -d '{}' -o /dev/null -D - "https://${HOST_GC}/api/admin/beta/invite" | head -8

hdr "Steam OpenID init path enumeration"
for path in /auth/steam /auth/login /login /signin /openid /openid/authenticate /openid/return; do
    code=$(curl -s --max-time 5 -o /dev/null -w '%{http_code}' -A "Mozilla/5.0" "https://${HOST_GC}${path}")
    if [ "$code" != "401" ] && [ "$code" != "404" ]; then
        echo "  ${path} → ${code}  <-- interesting"
    fi
done

hdr "Cookie flags check (login flow needs manual browser step)"
echo "  Run in browser: watch for Set-Cookie SameSite/Secure/HttpOnly after Steam login"
echo "  If SameSite=None → CSRF surface is HIGH"
echo "  If SameSite=Lax → limited CSRF (only same-site or GET redirects)"
echo "  If SameSite=Strict → CSRF closed"
