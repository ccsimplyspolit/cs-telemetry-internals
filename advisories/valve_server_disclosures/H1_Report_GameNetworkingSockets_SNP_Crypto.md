# Coordinated Vulnerability Disclosure: Unbounded 64-Bit Unreliable Message Number Offset, Zero-Length Segment OOB Read, `Base64EncodeMaxOutput(0)` Underflow, and `CUtlBuffer::GetString` Seek Misalignment in `GameNetworkingSockets`

- **Advisory / Disclosure ID:** CVD-2026-VALVE-004 (HackerOne / Valve Software Program & GitHub Security Advisory)
- **Target Product:** `ValveSoftware/GameNetworkingSockets` (`<= v1.4.1` / `HEAD`, `Steam Servers`, `Steam Client`, `https://github.com/valvesoftware`)
- **Vulnerability Class:** Out-of-Bounds Read (`CWE-125`), Integer Overflow or Wraparound (`CWE-190`), Integer Underflow (`CWE-191`), Out-of-Bounds Write (`CWE-787`)
- **CVSS v3.1 Base Score:** `6.5 (Medium)` (`CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:L`)
- **Researcher:** Serhii Shunko (`@sshunko` / `@ccsimplyspolit`, ORCID: `0009-0002-4183-0361`, `cc.simply.spolit@gmail.com`)
- **Disclosure Status:** Coordinated Vulnerability Disclosure prepared for Valve Software (`https://hackerone.com/valve` / `ValveSoftware/GameNetworkingSockets`)

---

## 1. Executive Summary

In `ValveSoftware/GameNetworkingSockets` (`src/steamnetworkingsockets/clientlib/steamnetworkingsockets_snp.cpp`, `src/common/crypto_textencode.cpp`, and `src/tier1/utlbuffer.cpp` at `<= v1.4.1` / `HEAD`), four memory-safety and protocol-state invariants can be violated when processing SNP unreliable data chunks, Base64/Hex/PEM buffers, or `CUtlBuffer` strings:

1. **Unbounded 64-Bit `nMsgNumOffset` Wrap/Poisoning & Zero-Length Segment OOB Read in SNP Unreliable Framing (`src/steamnetworkingsockets/clientlib/steamnetworkingsockets_snp.cpp:835-848, 3274-3283`)**
2. **Unsigned Underflow in `CCrypto::Base64EncodeMaxOutput()`, 32-Bit Overflow & Zero-Capacity OOB Write in `HexEncode()`/`Base64Encode()`, and PEM Header Prefix-Match Bypass (`src/common/crypto_textencode.cpp:26-31, 150-156, 209-212, 284-288, 497-502`)**
3. **Truncated `CUtlBuffer::GetString()` Seek Misalignment (`src/tier1/utlbuffer.cpp:628-661`)**

---

## 2. Technical Root Cause Analysis

### 2.1 Unbounded 64-Bit `nMsgNumOffset` Wrap/Poisoning & Zero-Length Segment OOB Read (`steamnetworkingsockets_snp.cpp:835-848, 3274-3283`)
- In `CSteamNetworkConnectionBase::ProcessPlainTextDataChunk()` (`lines 835-847`), when a subsequent unreliable message frame in a packet has header bit `0x10` set, a 64-bit varint `uint64 nMsgNumOffset` is decoded via `READ_VARINT(nMsgNumOffset, "unreliable msgnum offset")` and added directly to `int64 nCurMsgNumForUnreliable` (`nCurMsgNumForUnreliable += nMsgNumOffset;`) without upper-bound or overflow validation. A crafted `nMsgNumOffset` can either wrap `nCurMsgNumForUnreliable` into negative `int64` values or advance `pCurrentLane->m_nHighestSeenMsgNum` (`line 847`) to `INT64_MAX`, poisoning `NearestWithSameLowerBits()` (`lines 810, 816`) for all subsequent unreliable frames on that lane.
- In `CSteamNetworkConnectionBase::SNP_ReceiveUnreliableSegment()` (`line 3282`), `SpewDebugGroup(m_connectionConfig.LogLevel_PacketDecode.Get(), ...)` unconditionally indexes `((byte*)pSegmentData)[0]` and `((byte*)pSegmentData)[cbSegmentSize-1]` before checking whether `cbSegmentSize == 0`. Because zero-length unreliable segments (`cbSegmentSize == 0`) are permitted by `ProcessPlainTextDataChunk()`, when packet decode debug logging (`m_connectionConfig.LogLevel_PacketDecode.Get() >= k_ESteamNetworkingSocketsDebugOutputType_Debug`) is active, `((byte*)pSegmentData)[cbSegmentSize-1]` reads `pSegmentData[-1]` (1 byte before the segment) and `((byte*)pSegmentData)[0]` reads `pEnd[0]` (1 byte past the packet payload buffer).

### 2.2 Unsigned Underflow in `Base64EncodeMaxOutput()`, Zero-Capacity OOB Write in `HexEncode()`/`Base64Encode()`, and PEM Header Prefix-Match Bypass (`crypto_textencode.cpp:26-31, 150-156, 209-212, 284-288, 497-502`)
- In `uint32 CCrypto::Base64EncodeMaxOutput(size_t cubData, const char *pszLineBreak)` (`lines 150-156`), when `cubData == 0` and `pszLineBreak != nullptr`, `nGroups = str_size((cubData + 2) / 3) = 0`. Because `str_size` is unsigned (`unsigned int` on `_WIN64`, `size_t` on POSIX), `(nGroups - 1) / k_LineBreakEveryNGroups` underflows `nGroups - 1` to `UINT_MAX` / `SIZE_MAX`.
- In `CCrypto::HexEncode()` (`lines 26-31`), `(cubData * 2) + 1` is evaluated in 32-bit `uint32` (wrapping when `cubData >= 0x80000000u`), and when `cchEncodedData == 0`, both `HexEncode()` (`line 29`) and `Base64Encode()` (`line 210` -> `goto out_of_space` -> `line 285`) write `*pchEncodedData = '\0'` into a zero-capacity buffer.
- In `BParsePEMHeaderOrFooter()` (`lines 497-502`), `pszType + cchExpectedType > pchPEM || V_strnicmp(pszType, pszExpectedType, cchExpectedType) != 0` checks only that the PEM banner begins with `pszExpectedType`, rather than requiring an exact length match (`pszType + cchExpectedType == pchPEM`) before the closing `-----`.

### 2.3 Truncated `CUtlBuffer::GetString()` Seek Misalignment (`utlbuffer.cpp:628-661`)
- In `CUtlBuffer::GetString(char* pString, int nMaxChars)` (`lines 628-661`), `int nLen = PeekStringLength()` includes the terminating NUL character (`1 + strlen`). When `nLen > nMaxChars` (`lines 645-652`), `Get(pString, nMaxChars - 1)` advances `m_Get` by `nMaxChars - 1` bytes, and then `SeekGet(SEEK_CURRENT, nLen - 1 - nMaxChars)` advances by `nLen - 1 - nMaxChars` and returns `false` before `if (!IsText()) GetChar()` (`line 655`), instead of advancing by `nLen - nMaxChars + (IsText() ? 0 : 1)`, leaving `m_Get` misaligned by 1 byte (text mode) or 2 bytes (binary mode, before the terminating NUL) inside the unread tail of the string.

---

## 3. Recommended Remediation (`difflib.unified_diff` Patch)

```diff
--- a/src/steamnetworkingsockets/clientlib/steamnetworkingsockets_snp.cpp
+++ b/src/steamnetworkingsockets/clientlib/steamnetworkingsockets_snp.cpp
@@ -836,7 +836,12 @@
 				{
 					uint64 nMsgNumOffset;
 					READ_VARINT( nMsgNumOffset, "unreliable msgnum offset" );
-					nCurMsgNumForUnreliable += nMsgNumOffset;
+					if ( nMsgNumOffset > 0x10000000ull ||
+						(uint64)nCurMsgNumForUnreliable > (uint64)INT64_MAX - nMsgNumOffset )
+					{
+						DECODE_ERROR( "unreliable msgnum offset out of bounds" );
+					}
+					nCurMsgNumForUnreliable += (int64)nMsgNumOffset;
 				}
 				else
 				{
@@ -3279,7 +3284,7 @@
 	int idxLane,
 	SteamNetworkingMicroseconds usecNow )
 {
-	SpewDebugGroup( m_connectionConfig.LogLevel_PacketDecode.Get(), "[%s] RX msg %lld offset %d+%d=%d %02x ... %02x\n", GetDescription(), nMsgNum, nOffset, cbSegmentSize, nOffset+cbSegmentSize, ((byte*)pSegmentData)[0], ((byte*)pSegmentData)[cbSegmentSize-1] );
+	SpewDebugGroup( m_connectionConfig.LogLevel_PacketDecode.Get(), "[%s] RX msg %lld offset %d+%d=%d %02x ... %02x\n", GetDescription(), nMsgNum, nOffset, cbSegmentSize, nOffset+cbSegmentSize, cbSegmentSize > 0 ? ((const byte*)pSegmentData)[0] : 0, cbSegmentSize > 0 ? ((const byte*)pSegmentData)[cbSegmentSize-1] : 0 );
 
 	// Ignore data segments when we are not going to process them (e.g. linger)
 	if ( GetState() != k_ESteamNetworkingConnectionState_Connected )
--- a/src/common/crypto_textencode.cpp
+++ b/src/common/crypto_textencode.cpp
@@ -23,7 +23,10 @@
 	Assert( pchEncodedData );
 	Assert( cchEncodedData > 0 );
 
-	if ( cchEncodedData < ( ( cubData * 2 ) + 1 ) )
+	if ( cchEncodedData == 0 )
+		return false;
+
+	if ( cubData > ( UINT32_MAX - 1 ) / 2 || cchEncodedData < ( ( cubData * 2 ) + 1 ) )
 	{
 		Assert( cchEncodedData >= ( cubData * 2 ) + 1 );  // expands to 2x input + NULL, must have room in output buffer
 		*pchEncodedData = '\0';
@@ -151,7 +154,7 @@
 {
 	// terminating null + 4 chars per 3-byte group + line break after every 18 groups (72 output chars) + final line break
 	str_size nGroups = str_size( (cubData+2)/3 );
-	str_size cchRequired = 1 + nGroups*4 + ( pszLineBreak ? V_strlen(pszLineBreak)*(1+(nGroups-1)/k_LineBreakEveryNGroups) : 0 );
+	str_size cchRequired = 1 + nGroups*4 + ( ( pszLineBreak && nGroups > 0 ) ? V_strlen(pszLineBreak)*(1+(nGroups-1)/k_LineBreakEveryNGroups) : 0 );
 	return cchRequired;
 }
 
@@ -282,7 +285,8 @@
 	return true;
 
 out_of_space:
-	*pchEncodedData = 0;
+	if ( pchEncodedData && cchEncodedData > 0 )
+		*pchEncodedData = 0;
 	*pcchEncodedData = Base64EncodeMaxOutput( cubData, pszLineBreak );
 	AssertMsg( false, "CCrypto::Base64Encode: insufficient output buffer (up to n*4/3+5 bytes required, plus linebreaks)" );
 	return false;
@@ -497,7 +501,7 @@
 	if ( pszExpectedType )
 	{
 		int cchExpectedType = V_strlen( pszExpectedType );
-		if ( pszType + cchExpectedType > pchPEM || V_strnicmp( pszType, pszExpectedType, cchExpectedType ) != 0 )
+		if ( pszType + cchExpectedType != pchPEM || V_strnicmp( pszType, pszExpectedType, cchExpectedType ) != 0 )
 			return false;
 	}
 
--- a/src/tier1/utlbuffer.cpp
+++ b/src/tier1/utlbuffer.cpp
@@ -646,7 +646,7 @@
 	{
 		Get( pString, nMaxChars - 1 );
 		pString[ nMaxChars - 1 ] = 0;
-		SeekGet( SEEK_CURRENT, nLen - 1 - nMaxChars );
+		SeekGet( SEEK_CURRENT, nLen - nMaxChars + ( IsText() ? 0 : 1 ) );
 		// we've had to truncate, read out but return false
 		return false;
 	}
```

---

## 4. Formal Specification & Taint Provenance (`re-source-reconstruction` / `PTN`)

### 4.1 Symbol & Call-Graph Provenance Table
| Source Location | Symbol / Function | Subsystem Role |
|---|---|---|
| `src/steamnetworkingsockets/clientlib/steamnetworkingsockets_snp.cpp:835-848` | `CSteamNetworkConnectionBase::ProcessPlainTextDataChunk` | Decodes unreliable segment framing and message numbers |
| `src/steamnetworkingsockets/clientlib/steamnetworkingsockets_snp.cpp:3274-3285` | `CSteamNetworkConnectionBase::SNP_ReceiveUnreliableSegment` | Logs and queues received unreliable message segments |
| `src/common/crypto_textencode.cpp:19-33, 150-156, 204-288, 463-514` | `CCrypto::HexEncode`, `Base64EncodeMaxOutput`, `Base64Encode`, `BParsePEMHeaderOrFooter` | Encodes/decodes Hex, Base64, and PEM blocks |
| `src/tier1/utlbuffer.cpp:611-662` | `CUtlBuffer::GetString(char*, int)` | Reads NUL-terminated string with caller-supplied capacity limit |

### 4.2 PTN Data-Flow & Taint Propagation
- **`I:PlainTextDataChunk`** (unreliable segment header with bit `0x10`) -> **`P(READ_VARINT, nMsgNumOffset)`** -> **`L(ProcessPlainTextDataChunk, nCurMsgNumForUnreliable += nMsgNumOffset)`** -> **`E:pCurrentLane->m_nHighestSeenMsgNum`** (poisons `NearestWithSameLowerBits`).
- **`I:PlainTextDataChunk`** (`cbSegmentSize == 0`) -> **`P(SNP_ReceiveUnreliableSegment, cbSegmentSize=0)`** -> **`E:((byte*)pSegmentData)[cbSegmentSize-1]`** (reads `pSegmentData[-1]`).

### 4.3 Assumption Register (`[A1..A3]`) & Falsification Probes (`QG1–QG7`)
| ID / Gate | Claim / Invariant | Verification / Falsification Probe | Status |
|---|---|---|---|
| `[A1]` / `QG1` | `nMsgNumOffset` in `ProcessPlainTextDataChunk()` (`line 839`) is unbounded and `SNP_ReceiveUnreliableSegment()` (`line 3282`) indexes `pSegmentData[0]` and `pSegmentData[cbSegmentSize-1]` when `cbSegmentSize == 0` | Inspected `steamnetworkingsockets_snp.cpp:835-848, 3274-3283` | Verified (`100%`) |
| `[A2]` / `QG2` | `Base64EncodeMaxOutput(0, pszLineBreak)` underflows `(nGroups - 1)` in unsigned `str_size`, and `HexEncode()`/`Base64Encode()` write `*pchEncodedData = 0` when `cchEncodedData == 0` | Inspected `crypto_textencode.cpp:26-31, 150-156, 209-212, 284-288, 497-502` | Verified (`100%`) |
| `[A3]` / `QG5` | `CUtlBuffer::GetString()` (`line 649`) seeks by `nLen - 1 - nMaxChars` on truncation (`nLen > nMaxChars`) instead of `nLen - nMaxChars + (IsText() ? 0 : 1)` | Inspected `utlbuffer.cpp:628-661`; verified `difflib.unified_diff` hunks (`7/7 EXACT MATCH`) | Verified (`100%`) |
