# Inventory KV-injection surface

`POST /api/admin/inventory/:sid/import` accepts raw `text/plain`, described in
the frontend as "KeyValue format" (Valve `.txt` inventory format). The frontend
also grants items with a free-form `custom_name` field.

## Test payloads (require authenticated admin)

### 1. Newline injection into export
Grant an item with a name containing `\n` and see if it corrupts export format.

```
POST /api/admin/inventory/76561198000000000/grant
{
  "def_index": 7,
  "custom_name": "AK-47\"\n}\ninject:\"whatever",
  "quality": 4
}
```

Then GET the export — if the injected keys appear as valid VDF entries, KV
injection is confirmed (allows crafting items with arbitrary metadata that
never went through the grant path).

### 2. Quote escape
```
{ "custom_name": "test\"key\"={\"nested\":\"exploit\"}" }
```

### 3. VDF-parser recursion / DoS
```
POST /api/admin/inventory/76561198000000000/import
Content-Type: text/plain

"items"
{
  "1"  { "1"  { "1"  { ... 10 000 nested "1" { ... }}}}}
}
```
Watch memory / time-to-response on the server. If unbounded → DoS.

### 4. Very large payload
```
# 100 MB of ` ` (space) between tokens
```
Watch for OOM or hard timeout. Rate-limit check.

### 5. Unicode homoglyphs in def_index / paint_kit
Not KV-injection but adjacent — if server does `int(x)` on locale-affected
strings, you may bypass whitelists with digits from other scripts (Arabic-
Indic, fullwidth). Try:
```
{ "custom_name": "test", "paint_kit": "４４" }   // fullwidth 44
```

## Server-side fix

- Reject `\r\n` in any string field written to export.
- Bound total payload size (< 256 KB should be plenty).
- Bound VDF nesting depth (< 32).
- Reject non-ASCII digits in numeric fields (use `str.isdigit()` NOT locale-aware).
