# Security Research Advisory: ADV-2026-004

- **Advisory ID:** ADV-2026-004
- **Title:** Valve Data Format (VDF / KeyValues) Serializer Injection & Recursive Parser Exhaustion
- **Published:** October 2026
- **Researcher:** Serhii Shunko (`cc.simply.spolit@gmail.com`)
- **Vulnerability Class:** Improper Neutralization of Special Elements in Data Query Logic (`CWE-943`), Uncontrolled Recursion (`CWE-674`)

---

## 1. Executive Summary

Services interfacing with Source and Source 2 backend pipelines frequently serialize and deserialize structured configuration and inventory records using Valve Data Format (`VDF` / `KeyValues`), a hierarchical plain-text format delimited by double quotes (`"`) and braces (`{`, `}`).

Two vulnerability classes arise in custom VDF handling implementations:
1. **Structural KeyValues Injection (`CWE-943`):** Concatenating unescaped user-controlled strings (such as `custom_name` or player metadata) into a VDF serialization buffer allows attackers to break out of the string literal using `"`, `\n`, and `{}` tokens to inject arbitrary sibling keys or override privileged attributes.
2. **Unbounded Recursive Descent DoS (`CWE-674`):** Recursive-descent VDF parsers that do not enforce a maximum nesting depth or payload byte ceiling are vulnerable to stack overflow or memory exhaustion when parsing deeply nested brace sequences (`{ "a" { "a" { ... } } }`).

---

## 2. Technical Vulnerability Analysis

### 2.1 VDF Serializer Breakout via Unescaped Delimiters
When a serializer constructs VDF output via string interpolation:
```text
"item_record"
{
    "def_index"     "7"
    "custom_name"   "<USER_INPUT>"
    "quality"       "4"
}
```
If `<USER_INPUT>` contains `test"\n    "quality" "99"\n    "comment" "`, the resulting VDF document alters the structural AST parsed by downstream game servers.

### 2.2 Locale-Dependent Numeric Parsing (`CWE-178`)
In Python and C/C++ services that validate numeric string fields using Unicode-aware digit checks (e.g., Python `str.isdigit()` without `str.isascii()`), fullwidth Unicode digits (`"４４"`, `U+FF14`) pass validation filters while being coerced or rejected inconsistently by downstream native C++ `atoi` / `strtol` parsers.

---

## 3. Remediation & Secure Parser Implementation

1. **Strict Token Escaping & Control-Character Rejection:**
   ```python
   def sanitize_vdf_string(value: str, max_len: int = 128) -> str:
       if len(value) > max_len:
           raise ValueError("VDF string exceeds maximum length")
       if any(ord(ch) < 0x20 or ch in ('"', '\\', '{', '}') for ch in value):
           raise ValueError("Forbidden control or structural delimiter in VDF string")
       return value
   ```
2. **Depth-Bounded Iterative Parsing:** Enforce a hard payload size cap ($\le 256\text{ KB}$) and a maximum nesting depth ($\le 32$ levels) in all VDF deserializers.
3. **ASCII-Strict Integer Validation:** Validate numeric identifiers exclusively against `^[0-9]{1,10}$` prior to type conversion.
