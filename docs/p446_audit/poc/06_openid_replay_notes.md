# Steam OpenID 2.0 — replay / verification bypass tests

Steam still uses OpenID 2.0 (no OIDC). The known failure modes when a site
implements it manually rather than using a vetted library:

## Known OpenID2 verifier bugs

1. **`check_authentication` bypass** — accept the assertion straight from the
   query string without calling back `https://steamcommunity.com/openid/login`
   to verify. If the site trusts `openid.identity` blindly, forge any steam_id.

2. **`openid.claimed_id` vs `openid.identity` confusion** — some verifiers
   check one but return the other. Set `openid.claimed_id` to attacker's own,
   `openid.identity` to victim's SteamID.

3. **Signature strip** — remove `openid.sig` and `openid.signed` from the
   callback; if the site only fires `check_authentication` "when signature
   present", missing signature bypasses check.

4. **`openid.op_endpoint` swap** — point to attacker-controlled OP that
   always returns `is_valid:true`. If the callback handler doesn't hardcode
   `steamcommunity.com` for the verification POST, forged.

5. **Replay window too wide** — nonces reused across sessions.

## How to test (require running a fake OP or intercepting the callback)

Because Steam OpenID uses redirects, testing requires either:
- Local mitmproxy sitting between browser and OP callback URL.
- Or crafting a full callback URL by hand — legitimate `check_authentication`
  request to Steam, harvest the exact params, then re-post to the callback URL
  with modifications.

Concrete test:

```bash
# 1. Initiate login (browser or curl). Follow redirect to Steam.
curl -sL "https://gc.project446.su/auth/login"
# 2. Log in real Steam account, capture the callback URL (something like
#    https://gc.project446.su/auth/return?openid.mode=id_res&openid.sig=...)
# 3. Replay the same URL a second time in an incognito window. If a session
#    cookie is issued again → replay window open (should be rejected).
# 4. Modify openid.identity to another SteamID64 and see if server accepts.
#    A correct server will refuse (sig mismatch).
```

## What to record

- Whether the server calls back `steamcommunity.com/openid/login` with
  `openid.mode=check_authentication` — inspect outbound conn from origin
  during login. If yes, spec-compliant; if not, likely trusting query blindly.
- Whether the same callback URL can be replayed → nonce reuse.
- Whether the callback URL parameter host is validated.

## Server-side fix

Use a well-audited library:
- Node: `openid` (npm), or better switch to Steam Web API token flow.
- Rust: `openid` crate, or same switch to Web API.
- Go: `github.com/yohcop/openid-go`.

Do NOT roll your own OpenID2 verifier.
