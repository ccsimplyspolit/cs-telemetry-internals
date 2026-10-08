#!/usr/bin/env bash
# P446 audit — infra recon PoC (safe, non-destructive)
# Run against prod (with owner permission) or staging.
# Expected: reproduces the P0/P1 findings from the audit report.
set -u

HOST_ORIGIN="${HOST_ORIGIN:-213.152.43.203}"
HOST_PUB="${HOST_PUB:-project446.su}"
HOST_GC="${HOST_GC:-gc.project446.su}"

green() { printf '\033[32m%s\033[0m\n' "$*"; }
red()   { printf '\033[31m%s\033[0m\n' "$*"; }
hdr()   { printf '\n\033[36m=== %s ===\033[0m\n' "$*"; }

hdr "TCP ports on origin"
for port in 21 22 25 80 443 3000 3306 5432 6379; do
    if timeout 2 bash -c "echo > /dev/tcp/${HOST_ORIGIN}/${port}" 2>/dev/null; then
        red "  ${port} OPEN"
    fi
done

hdr "SSH banner"
timeout 4 bash -c "exec 3<>/dev/tcp/${HOST_ORIGIN}/22; read -t2 line <&3; echo \"  \$line\""

hdr "PostgreSQL protocol probe (non-auth SSL negotiation only)"
python3 <<'PY'
import socket, struct, os
h = os.environ['HOST_ORIGIN']
try:
    s = socket.socket(); s.settimeout(3); s.connect((h, 5432))
    s.send(struct.pack('!II', 8, 80877103))  # SSLRequest
    r = s.recv(1)
    if r == b'S':
        print(f'  {h}:5432  postgres protocol ✓  TLS supported')
    elif r == b'N':
        print(f'  {h}:5432  postgres ✓  plaintext only')
    else:
        print(f'  {h}:5432  unexpected byte 0x{r.hex()}')
except Exception as e:
    print(f'  {h}:5432  not reachable ({e})')
PY

hdr "MySQL banner"
python3 <<'PY'
import socket, os
h = os.environ['HOST_ORIGIN']
try:
    s = socket.socket(); s.settimeout(3); s.connect((h, 3306))
    data = s.recv(200)
    # MySQL handshake starts with 4-byte length + payload
    if len(data) > 5:
        proto = data[4]
        # server version string is null-terminated after protocol byte
        ver_end = data.index(b'\x00', 5)
        ver = data[5:ver_end].decode(errors='replace')
        print(f'  {h}:3306  MySQL protocol {proto}, version "{ver}"')
    else:
        print(f'  {h}:3306  short response ({len(data)} bytes)')
except Exception as e:
    print(f'  {h}:3306  {e}')
PY

hdr "HTTP: origin :3000 vs prod (WAF bypass check)"
echo "--- origin :3000 (should be Next.js direct) ---"
curl -sI --max-time 6 -A "Mozilla/5.0" "http://${HOST_ORIGIN}:3000/api/admin/beta" | head -5
echo "--- via DDoS-Guard host ---"
curl -sI --max-time 6 -A "Mozilla/5.0" "https://${HOST_GC}/api/admin/beta" | head -5

hdr "CORS wildcard check (no credentials expected)"
curl -s --max-time 6 -X OPTIONS \
    -H "Origin: https://evil.example" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: content-type" \
    -A "Mozilla/5.0" -o /dev/null -D - \
    "https://${HOST_GC}/api/admin/beta/invite" | grep -iE 'access-control|http/'

hdr "HSTS mismatch (edge vs origin)"
echo "--- via Cloudflare (public site) ---"
curl -sI --max-time 6 -A "Mozilla/5.0" "https://${HOST_PUB}/" | grep -i "strict-transport"
echo "--- direct :3000 (real Next.js response) ---"
curl -sI --max-time 6 -A "Mozilla/5.0" "http://${HOST_ORIGIN}:3000/" | grep -i "strict-transport"

hdr "Origin IP host-header bypass — same-host serves everything"
curl -sI --max-time 6 --resolve "${HOST_PUB}:443:${HOST_ORIGIN}" -k -A "Mozilla/5.0" "https://${HOST_PUB}/" | head -3

hdr "DONE"
