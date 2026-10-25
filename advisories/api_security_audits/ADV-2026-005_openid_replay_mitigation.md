# Security Research Advisory: ADV-2026-005

- **Advisory ID:** ADV-2026-005
- **Title:** Authentication Bypass & Assertion Replay Vulnerabilities in Custom OpenID 2.0 Relying Parties
- **Published:** October 2026
- **Researcher:** Serhii Shunko (`cc.simply.spolit@gmail.com`)
- **Vulnerability Class:** Authentication Bypass by Spoofing (`CWE-290`), Capture-Replay (`CWE-294`)

---

## 1. Executive Summary

Because the Steam Community authentication provider utilizes legacy **OpenID 2.0** (`http://specs.openid.net/auth/2.0`) rather than OpenID Connect (OIDC), web platforms and telemetry portals frequently implement custom OpenID 2.0 callback handlers.

Security audits of custom OpenID 2.0 Relying Party (RP) implementations reveal five recurring critical defects that enable account takeover (`CWE-290`) and assertion replay (`CWE-294`):
1. **Missing Direct Verification (`check_authentication` Omission):** Trusting `openid.identity` directly from the callback query string without executing a server-to-server `POST` with `openid.mode=check_authentication` to `https://steamcommunity.com/openid/login`.
2. **Identity / Claimed-ID Desynchronization:** Validating `openid.claimed_id` during signature verification while extracting the authenticated user ID from `openid.identity` (or vice versa).
3. **Unpinned `openid.op_endpoint` SSRF / Spoofing:** Forwarding the verification `POST` to the URL specified in the user-supplied `openid.op_endpoint` query parameter instead of hardcoding `https://steamcommunity.com/openid/login`, allowing an attacker-controlled server to return `is_valid:true` for any account ID.
4. **Unsigned Parameter Stripping:** Failing to verify that `openid.signed` explicitly covers `op_endpoint,claimed_id,identity,return_to,response_nonce,assoc_handle`.
5. **Stateless Nonce Replay (`CWE-294`):** Failing to track and invalidate `openid.response_nonce` values within the acceptance timestamp window, allowing captured callback URLs to issue duplicate session tokens.

---

## 2. Secure Relying Party Verification Pattern

A compliant OpenID 2.0 verifier must enforce strict endpoint pinning, signed-field coverage, and single-use nonce consumption:

```python
import hmac
from urllib.parse import urlparse

STEAM_OPENID_ENDPOINT = "https://steamcommunity.com/openid/login"
REQUIRED_SIGNED_FIELDS = {
    "op_endpoint",
    "claimed_id",
    "identity",
    "return_to",
    "response_nonce",
    "assoc_handle",
}

def verify_openid2_callback(query_params: dict[str, str], expected_return_to: str, nonce_store) -> str:
    # 1. Verify mode and pinned OP endpoint
    if query_params.get("openid.mode") != "id_res":
        raise ValueError("Invalid openid.mode")
    if query_params.get("openid.op_endpoint") != STEAM_OPENID_ENDPOINT:
        raise ValueError("Untrusted OpenID Provider endpoint")

    # 2. Enforce exact match between claimed_id and identity
    claimed_id = query_params.get("openid.claimed_id", "")
    identity = query_params.get("openid.identity", "")
    if not hmac.compare_digest(claimed_id, identity):
        raise ValueError("Mismatch between openid.claimed_id and openid.identity")

    # 3. Verify return_to matches the expected callback URL
    if query_params.get("openid.return_to") != expected_return_to:
        raise ValueError("Invalid openid.return_to destination")

    # 4. Verify all security-critical fields are covered by openid.signed
    signed_fields = set(query_params.get("openid.signed", "").split(","))
    if not REQUIRED_SIGNED_FIELDS.issubset(signed_fields):
        raise ValueError("Missing mandatory fields in openid.signed")

    # 5. Enforce single-use response_nonce prior to network verification
    nonce = query_params.get("openid.response_nonce", "")
    if not nonce or not nonce_store.consume_once(nonce):
        raise ValueError("Replayed or expired openid.response_nonce")

    # 6. Perform server-to-server check_authentication POST to hardcoded endpoint
    verify_payload = {k: v for k, v in query_params.items() if k.startswith("openid.")}
    verify_payload["openid.mode"] = "check_authentication"
    # POST verify_payload to STEAM_OPENID_ENDPOINT and verify "is_valid:true" in response
    return claimed_id
```
