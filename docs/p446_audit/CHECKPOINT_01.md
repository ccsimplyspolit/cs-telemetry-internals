# Project446 pre-release audit — checkpoint #1

**Scope:** Full pre-release security audit + external-audit prep. Owner-authorized
black-box against live production `project446.su`, `gc.project446.su`, and the
origin `213.152.43.203` (self-declared `mail.project446.su`).

**Sources available:** `p446_kit_v5.zip/src` (client patcher, no backend),
`Project446-Setup.exe`, `Project446-Client(2).zip`, live network responses,
extracted admin panel HTML (`p446_admin_panel.html`, 2315 lines, complete API
surface).

**Auth material available:** None. Everything below is unauthenticated black-box.

---

## Infrastructure map

**One physical host** — `213.152.43.203` = `mail.project446.su` — runs every
service. There is no isolation between mail, application, and database tiers.

| Port | Service | Exposure | Notes |
|---|---|---|---|
| 22 | SSH — OpenSSH 9.6p1 Ubuntu 24.04 | Public | Not weak on version, but shouldn't be public. |
| 80/443 | nginx via DDoS-Guard (`gc.project446.su`) → Rust GC server | Public | Blanket-401 middleware for unauthenticated. |
| 443 | Cloudflare (`project446.su`) → Next.js public UI | Public | HSTS mis-configured on CF (max-age=0). |
| 3000 | Next.js dev-facing port — **directly exposed** | Public | Bypasses both CF and DDoS-Guard. |
| 3306 | MySQL/MariaDB | Public | Should be bound to loopback. |
| 5432 | PostgreSQL | Public | Should be bound to loopback. |
| 25 | SMTP | Filtered | Timeout — presumably firewalled. |

Two web apps live on this host:

- **Public site + admin panel HTML** (`project446.su`, Next.js at :3000).
- **Admin API + GC WebSocket** (`gc.project446.su`, Rust GC server on :443
  behind DDoS-Guard).

The two return distinct 401 bodies (`{"error":"Unauthorized"}` JSON vs
`Login required (admin only).` plain), confirming they are separate processes.

## Findings (unauthenticated)

### P0 — critical

**P0.1  PostgreSQL 5432 open to internet.**
The server responds to the postgres SSL negotiation from any source IP. Even
with strong `pg_hba.conf` rules this is a brute-force and CVE window. Combined
with the fact that mail, app, and DB all run on the same host, a
misconfiguration here is catastrophic.

- Repro: `python -c "import socket,struct; s=socket.socket(); s.connect(('213.152.43.203',5432)); s.send(struct.pack('!II', 8, 80877103)); print(s.recv(1))"` → returns `b'S'` (SSL supported).
- Fix: bind postgres to `127.0.0.1` in `postgresql.conf`; if a remote replica
  needs access, use IPsec/WireGuard, not public exposure.

**P0.2  MySQL 3306 open to internet.**
Same class as P0.1. If a second DB is actually in use — bind loopback. If it's
running unused — stop the daemon.

- Fix: `bind-address = 127.0.0.1` in `my.cnf`.

**P0.3  Next.js origin :3000 bypasses WAF + DDoS-Guard + Cloudflare.**
Every admin path (`/api/admin/beta`, `/auth/me`, etc.) is reachable at
`http://213.152.43.203:3000/…` with **no** rate-limit, JS challenge, TLS, or
DDoS filter. Cloudflare and DDoS-Guard configuration is bypassed by a single
`curl` on a known IP.

- Repro: `curl -sI http://213.152.43.203:3000/api/admin/beta` → 401 identical
  body to going through DDoS-Guard.
- Fix: firewall :3000 to accept only from the reverse proxy VMs (or the
  loopback of the same host if the RP runs locally). Do not expose Next.js
  directly.

**P0.4  Setup.exe is not Authenticode-signed.**
`Get-AuthenticodeSignature` reports `Status: NotSigned`. Anyone MITM'ing the
download or the user's browsing session can substitute a payload with no
signature warning shown by Windows or SmartScreen (SmartScreen does show
"unknown publisher", but users routinely dismiss it).

- Fix: buy a code-signing certificate (Sectigo/DigiCert), sign the installer
  with SHA-256 and a timestamp countersignature. Include an ambient
  publisher-key check in the installer itself as defense-in-depth.

### P1 — high

**P1.1  HSTS downgrade window via Cloudflare rewrite.**
Origin sends `Strict-Transport-Security: max-age=63072000; includeSubDomains;
preload`. Cloudflare rewrites this to `max-age=0` on the public path
`project446.su`. Effect: a browser that has never talked directly to the
origin will accept `http://` for the site.

- Fix: rebuild the CF page rule that strips STS, or set the same 63072000
  value at the CF edge.

**P1.2  Wildcard CORS on admin API without credentials.**
`Access-Control-Allow-Origin: *` on `/api/admin/*` OPTIONS response. Because
the server does NOT send `Allow-Credentials: true`, browsers refuse to send
session cookies — but the API surface is **fully readable** to any web page
that doesn't need auth (all read endpoints return public data via preflight
enumeration). This gives away the entire admin route inventory to any site.

- Fix: only echo `Origin` back if it's in an allowlist (the panel's own
  origin). Do NOT wildcard.

**P1.3  Blanket 401 middleware masks endpoint existence — but leaks methods.**
Both apps return 401 for existing-but-unauthenticated paths and for
non-existent paths equally. This is often marketed as "no info leak" but the
OPTIONS preflight *does* enumerate methods, defeating the intent while still
preventing legit tooling from separating 404 from 401.

- Fix: keep 401 for existing routes, return proper 404 (not 401) for missing
  routes. It's not worse from a security standpoint and it helps observability.

**P1.4  Blanket cross-origin CORS `Allow-Headers: content-type`.**
Combined with `credentials: 'same-origin'` in the panel, this doesn't leak the
session, but does allow a malicious cross-origin JS to fire JSON `POST`s and
observe response codes. That's useful for post-auth exploitation chains
(after XSS on any other subdomain).

- Fix: allow only what's actually needed and only from the panel origin.

### P2 — medium (verify in follow-ups)

**P2.1  `X-Powered-By: Next.js` header** — stack disclosure, no active harm
but removes a mystery an attacker would otherwise have to bruteforce.

**P2.2  Robots.txt allows everything for every crawler** — including admin
paths. Should specifically deny `/api/` and `/admin/`. This is passive but
means the panel URL will end up in Google's cache when someone links to it.

**P2.3  No SPF hardener** — SPF is `~all` (soft-fail). Given mail runs on
the same host as the app, phishing that spoofs `@project446.su` will likely
pass at many recipient MTAs. Switch to `-all` (hard-fail) and add DKIM+DMARC.

**P2.4  Weak SteamID validation on the frontend** — accepts `\d{15,20}`
(should be exactly 17 chars starting with `7656119`). Not a vuln by itself if
the server re-validates, but if not, DB gets polluted with garbage.

**P2.5  Two error dialects** — `{"error":"Unauthorized"}` (Next) vs
`Login required (admin only).` (Rust). Choose one, structured, everywhere.

### Hypothesis list — cannot verify without an authenticated admin session

The panel HTML reveals the following surface. Each item is a hypothesis about
an implementation flaw that we cannot prove from outside; the PoC bundle in
`poc/` gives you scripts to run after logging in.

- **H1** CSRF on any mutating admin endpoint — probability depends on the
  session cookie's `SameSite` attribute (see `poc/02_csrf_probe.sh`).
- **H2** KeyValue injection through inventory `import` and `custom_name`
  (see `poc/05_kv_injection_notes.md`).
- **H3** SSRF through `case_url` in patrol roster
  (see `poc/04_ssrf_probe_notes.md`).
- **H4** SQL injection through the `medals`, `paint_kit`, `paint_seed`
  integer fields — depends on server using prepared statements.
- **H5** OpenID 2.0 verifier bypass — depends on whether it's a vetted
  library or hand-rolled (see `poc/06_openid_replay_notes.md`).
- **H6** Fleet token storage — bearer token appears once at create; if stored
  in plaintext in Postgres, DB dump = fleet compromise. Test by dumping a
  test DB (owner access) and grep-ping for the returned token.
- **H7** OTA `publish` verify-before-store — if signature is verified after
  the module is written to disk, there's a window where clients could pull an
  unverified module. Verify by clocking the request.
- **H8** `is_admin` flag storage — if the flag lives on the user row and is
  mass-assignable via `PUT /api/admin/profile/:sid`, privilege escalation.
  Test: as a non-admin authenticated user, PUT `{...,"is_admin":true}` to own
  profile and re-check `/auth/me`.
- **H9** Rate-limit absence — no throttling visible; bulk endpoints
  (`beta/import`, `servers/bulk`, `always_drop_steam_ids`) accept large lists.
- **H10** Force-match server_id authorization — does the server verify that
  the admin owns/permitted the fleet server they're targeting? Multi-tenant
  concern for future.
- **H11** Mass-assignment on JSON PUTs — sending unknown fields like
  `is_admin` alongside legitimate fields may be silently persisted by a
  serde/reflection-based deserializer without an allowlist.

## What I need to progress

To finish the audit at production quality:

1. **Authenticated admin session on staging** — run PoC bundle against it.
   Alternative: give me a screencap of the browser dev-tools `Network` tab
   during a real login so I can see the session-cookie flags.
2. **A single non-admin Steam account** — for the H8 privilege-escalation
   test (safest done on staging).
3. **Backend source or partial `auth`/`admin` files** — flips the ratio from
   "hypothesis" to "confirmed" for at least H1, H4, H8, H11.

## PoC scripts included

- `poc/01_infra_scan.sh` — reproduces every P0/P1 infrastructure finding
- `poc/02_csrf_probe.sh` — CORS + cookie flag mapping
- `poc/03_endpoint_map.sh` — validates the entire route list
- `poc/04_ssrf_probe_notes.md` — SSRF test recipe
- `poc/05_kv_injection_notes.md` — KV / inventory import fuzz recipe
- `poc/06_openid_replay_notes.md` — OpenID 2.0 verifier tests
