# ATF Miner Backend — Bug Report
## Date: 2026-08-17

---

## CRITICAL BUGS

### BUG #1: CRITICAL — Boost Captcha Bypass via Empty challenge_id
**Severity: CRITICAL**
**Endpoint: activate_boost (index.php?action=activate_boost)**
**Impact: Unlimited free boosts without solving math challenges**

The server accepts `activate_boost` requests with an **empty `challenge_id`** and **any answer value** (including "0", "42", "9999", etc.). The math challenge security check is NOT enforced for boost activation.

**Reproduction:**
```json
POST index.php?action=activate_boost
{
  "challenge_id": "",
  "answer": "0",
  "scope": "boost",
  "display_preview": 0
}
// Returns: {"status": "success", "pending_reward": ..., "boost_active_until": ...}
```

**Evidence:**
- Before exploit: pending_reward=0.0393, total_boost_count=3
- After 1 empty challenge_id boost: pending_reward=0.0401 (INCREASED)
- After multiple: pending_reward=0.0497, total_boost_count=4
- Server accepted the boost, updated balances, and incremented boost count

**Mitigation (partial):** Server eventually applies a ~13-minute penalty ("Boost temporarily locked"), but:
- The first exploit ALWAYS succeeds
- Penalty only kicks in AFTER repeated abuse
- This is retroactive, not preventive

**Note:** Empty challenge_id for `start_mine` is properly rejected ("challenge_missing"). The bug is boost-specific.

---

### BUG #2: HIGH — Massive User Data Disclosure in API Responses
**Severity: HIGH**  
**Endpoint: sync_mining_state (all endpoints that return user data)**
**Impact: Full user record exposure including sensitive hashes**

The `sync_mining_state` endpoint returns the **complete user database record** including:

```
wallet_address, wallet_public_key,
signup_ip_hash, last_ip_hash, last_ip_prefix_hash,
ua_hash, device_id_hash,
risk_score, risk_flags,
wallet_verified, wallet_verified_at,
human_challenge_hash, human_passed,
all balance data, referral data,
nonbuyer protection flags, admin flags,
withdraw_puzzle state, etc.
```

This is returned on every `sync_mining_state` call. If intercepted (MITM, XSS, etc.), an attacker gets a complete profile of the user.

---

### BUG #3: MEDIUM — request_id Not Required for Sensitive Endpoints
**Severity: MEDIUM**
**Endpoint: sync_mining_state**
**Impact: Bypass of request deduplication mechanism**

The server works perfectly without a `request_id` field at all:
```json
// No request_id field at all
{"initData": "...", "device_id": "test", "tg_id": 5184629862}
// Returns: success with full user data
```

The dedup only catches **duplicate** request_ids, not **missing** ones.

---

### BUG #4: MEDIUM — Abuse Watch Counter Not Functional
**Severity: MEDIUM**
**Impact: Rate limiting ineffective for early requests**

The `abuse_watch.request_count` stays at `0` even after 5+ rapid boost attempts:
```json
"abuse_watch": {"request_count": 0, "active_seconds": 0, ...}
```

The abuse detection system appears non-functional or counting only specific actions.

---

## TESTS THAT SERVER HANDLED CORRECTLY

| Test | Vector | Server Response |
|------|--------|----------------|
| 1 | Negative math_answer | ❌ Error: "challenge_missing" (no valid challenge in session) |
| 2 | Huge number answer | ❌ Error: "challenge_missing" |
| 3 | Duplicate challenge_id | ❌ Error: "challenge_missing" |
| 4 (start_mine) | Empty challenge_id for start_mine | ❌ Error: "challenge_missing" |
| 5 | Replay old challenges | ❌ Error: "challenge_missing" |
| 6 | Boost during cooldown | ✅ "cooldown" status returned correctly |
| 7 | Race condition concurrent boosts | ✅ One gets "busy" ("Boost already in progress") |
| 9 | Crafted request_ids | ✅ All blocked: "Duplicate request blocked" |
| 10 | client_boost_cycle_seconds | ✅ Server ignores, always returns 8 |
| Extra | Malicious fields in sync | ✅ Server ignores unknown fields |

---

## KEY FINDINGS SUMMARY

1. **Empty challenge_id bypass for boost** is the most exploitable bug — allows free boosts without math solving. First attempt always succeeds.
2. **Full user record leak** in API responses is a significant privacy/security issue.
3. **Rate limiting is retroactive**, not preventive — exploits succeed before penalties kick in.
4. **start_mine is properly protected** but **boost is not** — inconsistent security.
5. The math challenge system works for start_mine but is completely bypassed for boost.
