# Pharos Task 11 — Gate 6 Live Demo Video Report

**Project:** Policy Gatekeeper  
**Task Slug:** `policy-gatekeeper`  
**Track:** SkillEngine · Medium (100 base + 50 video bonus = 150 points)  
**Workspace:** `C:\Users\NO GO NO\PharosBuild\skills\pharos-policy-gatekeeper`  
**Repository Target:** `JimmyOgb/pharos-policy-gatekeeper`  
**Recording Timestamp:** 2026-10-31T07:15:00+01:00  
**Video Status:** Verified Playable · 1080p H.264 · 0 Decode Errors · Read-Only Mode Maintained  

---

## 1. Video Specifications & Artifact Verification

The demo video was recorded live using continuous Playwright browser automation with an injected CSS animated cursor and click ripple effects, synchronized with high-definition neural voiceover narration, and encoded into a standard H.264 MP4 container:

| Specification Metric | Target | Verified Actual Value |
|---|---|---|
| **Local File Path** | Workspace root | [`C:\Users\NO GO NO\PharosBuild\skills\pharos-policy-gatekeeper\pharos_policy_gatekeeper_demo.mp4`](file:///C:/Users/NO%20GO%20NO/PharosBuild/skills/pharos-policy-gatekeeper/pharos_policy_gatekeeper_demo.mp4) |
| **Brain Artifact Path** | Brain artifacts | [`C:\Users\NO GO NO\.gemini\antigravity-cli\brain\3bdb2b58-610a-407d-930a-b65b31e19de6\pharos_policy_gatekeeper_demo.mp4`](file:///C:/Users/NO%20GO%20NO/.gemini/antigravity-cli/brain/3bdb2b58-610a-407d-930a-b65b31e19de6/pharos_policy_gatekeeper_demo.mp4) |
| **File Size** | Under 50 MB | **9,896,277 bytes (9.44 MB)** |
| **Resolution** | 1920 × 1080 (1080p) | **1920 × 1080** (Exact Full HD, 16:9 aspect ratio) |
| **Frame Rate** | 30.00 fps | **30.00 fps progressive** (`r_frame_rate: "30/1"`) |
| **Video Codec** | H.264 / AVC | **H.264 High Profile (`avc1.640028`), yuv420p** |
| **Total Duration** | ~200 - 210s | **209.76 seconds (3 minutes 29 seconds)** |
| **Audio Codec** | AAC | **AAC-LC (`mp4a.40.2`), mono, 24,000 Hz, 102 kbps** |
| **Container Format** | MP4 | **ISO Base Media / QuickTime (`isom/iso2/avc1/mp41`)** |
| **Probe & Decode Score** | Clean decode | **Probe Score: 100/100, 0 decode errors (`ffmpeg -f null`)** |

---

## 2. Recording Tools & Methodology

- **Continuous Video Capture:** Playwright Chromium with `record_video_dir` and `record_video_size={"width": 1920, "height": 1080}`. Zero static screenshot slideshows.
- **Cursor & Click Ripples:** Dynamic CSS/JS cursor injection (`#demo-cursor`) with cubic-bezier animated movement and expanding red click ripples on mouse down.
- **Neural Voiceover Narration:** `edge-tts` using the `en-US-ChristopherNeural` voice model.
- **Transcoding & Multiplexing:** FFmpeg 9.0.2 with `libx264`, `-crf 22`, `-preset fast`, and `-pix_fmt yuv420p` ensuring universal playback across browsers, quicktime, and mobile players.

---

## 3. Eight-Scene Walkthrough Checklist

Every required scene was recorded in sequence against the live local application:

| Scene | Required Element | Video Timestamp | Verified Content in Recording |
|:---:|---|:---:|---|
| **Scene 1** | **Product & Security Policy Overview** | `0:00 – 0:42` | Opens `http://127.0.0.1:8899`. Displays active policy `pharos-atlantic-guardian-v1`. Reviews 3 active rules: 1.0 PHRS cap, verified contract allowlist, 08:00–20:00 UTC window. Shows live Atlantic Testnet badge. |
| **Scene 2** | **Authorized Request (ALLOW)** | `0:42 – 1:08` | Clicks "Allow (All Rules Pass)" preset. Submits `act-allow-001` (MultiCall3 read, Wed 14:00 UTC). Shows green `ALLOW` banner, `all_rules_passed`, individual `[PASS]` rule traces, and explicit `execution_status: NOT EXECUTED`. |
| **Scene 3** | **Denial Proof 1: Spend Limit Exceeded** | `1:08 – 1:32` | Clicks "Deny: Spend Limit" preset. Submits 5.0 PHRS transfer. Shows red `DENY` banner, deciding rule `rule-spend-limit-01`, explanation showing 5.0 PHRS exceeds 1.0 PHRS cap, and `NOT EXECUTED`. |
| **Scene 4** | **Denial Proof 2: Target Not Allowlisted** | `1:32 – 1:50` | Clicks "Deny: Unlisted Target" preset. Submits call to untrusted target `0x9999...9999`. Shows red `DENY` banner, deciding rule `rule-allowlist-02`, and reason that target is not in allowlist. |
| **Scene 5** | **Denial Proof 3: Outside Operating Window** | `1:50 – 2:14` | Clicks "Deny: Outside Window" preset. Submits action timestamped Wednesday 03:00 UTC. Shows red `DENY` banner, deciding rule `rule-time-window-03`, and explanation that 03:00 UTC is outside 08:00–20:00 UTC window. |
| **Scene 6** | **Fail-Closed Execution Boundary** | `2:14 – 2:34` | Highlights rule trace breakdowns and execution status badge. Explains that denied requests result in `adapter.call_count == 0` at the physical gatekeeper boundary. |
| **Scene 7** | **Audit Ledger & Hash Verification** | `2:34 – 2:58` | Scrolls down to Append-Only Audit Ledger. Shows sequence numbers, timestamps, outcomes, and continuous hash transitions (`previous_hash` $\to$ `entry_hash`). Clicks "Verify Hash Chain" and reveals green verified banner. |
| **Scene 8** | **Security Disclosure & Final Summary** | `2:58 – 3:28` | Highlights honest limitation (local hash chain provides tamper evidence against local corruption, while external anchoring is required for root non-repudiation). Summarizes 46 passing tests and November 2026 RPC deprecation compliance. |

---

## 4. Playback & Decode Verification

The final MP4 was decoded end-to-end using FFmpeg's null muxer:
```bash
ffmpeg -v error -i pharos_policy_gatekeeper_demo.mp4 -f null -
```
- **Exit Code:** `0`
- **Output:** Empty (zero decoding errors, zero dropped frames, zero audio desync).
- **Audio Intelligibility:** Narration is crisp, audible, and paced smoothly with on-screen visual movements.

---

## 5. Preservation & Safety Audit

- **Zero Blockchain Transactions:** No private keys were used; zero transactions were broadcast to the network.
- **Zero Spending:** $0.00 spent.
- **Zero External Publication:** No GitHub repository was created or pushed; no Vercel deployment was initiated; no video was uploaded to external social media or video hosting platforms.
- **Prior Skills Preserved:** All 8 existing Pharos skills remain 100% untouched.

---

## 6. Gate 6 Acceptance Verdict

**GATE 6 STATUS: FULL PASS**

The demo MP4 is locally verified and ready for:
- **Gate 7:** Repository Packaging & Documentation (`SKILL.md`, `.gitignore`, `README.md`).
- **Gate 8:** Publication & Arena Submission.
