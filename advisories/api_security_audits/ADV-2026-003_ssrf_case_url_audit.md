# Security Research Advisory: ADV-2026-003

- **Advisory ID:** ADV-2026-003
- **Title:** Server-Side Request Forgery (SSRF) & URL Parser Confusion in Automated Replay Ingestion Pipelines
- **Published:** October 2026
- **Researcher:** Serhii Shunko (`cc.simply.spolit@gmail.com`)
- **Vulnerability Class:** Server-Side Request Forgery (`CWE-918`), Improper Input Validation (`CWE-20`)

---

## 1. Executive Summary

Backend telemetry and match-replay ingestion services frequently accept external resource locators (such as `case_url` or replay archive URLs) to fetch, parse, and index binary demo files asynchronously. When the ingestion endpoint validates the user-supplied URL solely via naive string prefix checks rather than post-resolution IP and scheme allowlisting, attackers can trigger Server-Side Request Forgery (`CWE-918`) to probe internal metadata services (`169.254.169.254`), localhost database listeners, or non-HTTP protocol handlers (`file://`, `gopher://`).

---

## 2. Vulnerability Mechanics & Attack Surface

### 2.1 Unvalidated Asynchronous Fetch
When a backend worker processes a JSON payload containing a remote archive reference:
```json
{
  "match_id": "8492019482",
  "case_url": "https://replay-cdn.example.net/demos/match_8492019482.dem.bz2"
}
```
If the worker passes `case_url` directly to an HTTP client (`reqwest`, `libcurl`, or `urllib`) without validating the resolved socket address:
1. **Scheme Smuggling:** Supplying `file:///proc/self/environ` or `gopher://127.0.0.1:6379/` when the underlying HTTP library permits non-HTTPS schemes.
2. **URL Parser Authority Confusion:** Exploiting discrepancies between RFC 3986 URL parsers and host validators using embedded credentials or backslashes (`https://trusted-cdn.example.net@127.0.0.1:8080/`).
3. **DNS Rebinding (TOCTOU):** Passing initial hostname validation via an external domain whose DNS A-record subsequently resolves to an RFC 1918 private address (`10.0.0.0/8`, `127.0.0.0/8`, `169.254.169.254`) when the HTTP client establishes the TCP connection.

---

## 3. Remediation & Defensive Architecture

To eliminate SSRF and DNS rebinding vectors in replay/telemetry ingestion workers:

```python
import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_REPLAY_HOSTS = frozenset({
    "replay1.valve.net",
    "replay2.valve.net",
})

def validate_and_resolve_replay_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if parsed.scheme != "https":
        raise ValueError("Only HTTPS scheme is permitted for replay ingestion")
    if parsed.username or parsed.password:
        raise ValueError("Embedded URL credentials are prohibited")
    if parsed.hostname not in ALLOWED_REPLAY_HOSTS:
        raise ValueError(f"Host {parsed.hostname!r} is not in the replay CDN allowlist")

    # Resolve hostname and verify all returned A/AAAA records are globally routable
    for family, _, _, _, sockaddr in socket.getaddrinfo(parsed.hostname, 443, proto=socket.IPPROTO_TCP):
        ip_obj = ipaddress.ip_address(sockaddr[0])
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
        ):
            raise ValueError(f"Resolved IP {ip_obj} violates public network boundary")

    return raw_url
```

1. **Disable HTTP Redirects:** Configure the ingestion HTTP client with `allow_redirects=False` so a validated CDN endpoint cannot redirect the worker to an internal address.
2. **Network-Layer Egress Isolation:** Execute replay-fetching workers inside an isolated egress namespace or proxy that blocks RFC 1918, loopback, and cloud metadata CIDR ranges at the packet filter level.
