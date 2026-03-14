# Gemini Live Agent Challenge — AI Judging Sheet
## Category: UI Navigator ☸️
### Criteria Covered: Innovation & Multimodal UX (40%) + Technical Implementation & Agent Architecture (30%)

---

## HOW TO USE THIS SHEET

You are an AI auditor evaluating a hackathon submission for the **Gemini Live Agent Challenge**. Your job is to read through the entire codebase and produce a detailed, granular score report.

**Rules for scoring:**
- Every score must be justified by **explicit evidence found in the code or repository**. Do not assume, infer, or give benefit of the doubt.
- Each sub-criterion has a defined point budget. Score within that range only.
- If a feature is partially implemented, award partial points and note exactly what is missing.
- If evidence is ambiguous, note it and award the **lower end** of the range.
- Your sub-scores must **add up exactly** to the Section total you report.
- Output your findings in the exact structure defined at the end of this sheet.

**Score scales:**
- **Section 1 (Innovation & Multimodal UX):** 0–100 points, built from sub-scores
- **Section 2 (Technical Implementation & Architecture):** 0–100 points, built from sub-scores
- **Final weighted score** is computed at the end from both sections

---

## SECTION 1 — INNOVATION & MULTIMODAL USER EXPERIENCE
**Official weight: 40% of total hackathon score**
**This sheet scores it: 0–100 points**

Sub-score budget breakdown (must sum to your Section 1 total):

| Sub-criterion | Max Points |
|---|---|
| 1.1 The "Beyond Text Box" Factor | 30 |
| 1.2 Visual Precision & Screen Context Understanding | 30 |
| 1.3 Seamlessness & Fluidity of the Agent Loop | 25 |
| 1.4 Distinct Persona or User Experience Layer | 15 |
| **TOTAL** | **100** |

---

### 1.1 — The "Beyond Text Box" Factor
**Max: 30 points**

The agent must use vision as its **primary input** to understand and navigate UI — not text descriptions, hardcoded selectors, or DOM parsing.

**Look for:**
- [ ] Code that actively captures screenshots or screen recordings during agent operation (e.g., `PIL.ImageGrab`, `pyautogui.screenshot()`, Playwright/Puppeteer `.screenshot()`, `scrcpy`, browser DevTools Protocol screenshot, etc.)
- [ ] Those screenshots/frames are passed as **image content** directly into a Gemini multimodal API call — not converted to text descriptions first
- [ ] The agent's action decisions are **downstream of what Gemini sees** — the visual input is in the causal chain of every action
- [ ] A real-time or near-real-time feedback loop exists: agent takes an action → captures a new screenshot → feeds it back to Gemini → decides next action

**Scoring bands:**
- **25–30**: Vision is the essential, primary input; the agent literally cannot decide what to do without a screenshot; feedback loop is clearly implemented end-to-end
- **17–24**: Vision is used substantively for most decisions; minor fallback to DOM/selectors exists but is not the primary path
- **9–16**: Vision is used but supplementary; agent primarily relies on DOM queries, hardcoded selectors, or text descriptions of the UI
- **3–8**: Vision is present but cosmetic or one-off (e.g., only used in one step, or screenshot is taken but Gemini is not actually deciding from it)
- **0–2**: No genuine vision input found; purely text, DOM, or API-based navigation

**Record as:** `1.1 = __ / 30`

---

### 1.2 — Visual Precision & Screen Context Understanding
**Max: 30 points**

Per the official rules, UI Navigator submissions are specifically judged on: *"Does the agent demonstrate visual precision (understanding screen context) rather than blind clicking?"*

**Look for:**
- [ ] Gemini is explicitly prompted to identify and locate specific UI elements (buttons, text fields, dropdowns, menus, checkboxes) within a screenshot
- [ ] Coordinates, bounding boxes, or element descriptions are **derived from Gemini's visual interpretation** — not from DOM queries, accessibility trees, or hardcoded pixel values
- [ ] Evidence the agent understands **page context** — e.g., it can distinguish a login page from a dashboard, a form from a table, an error state from a success state
- [ ] The agent handles **dynamic or unexpected UI states** through visual detection: popups, modals, loading spinners, CAPTCHAs, 404 pages
- [ ] Multi-step visual reasoning is present: the agent tracks where it is in a task across multiple screenshots, not just reacting to each frame in isolation
- [ ] Any use of advanced grounding techniques: Set-of-Mark (SoM) annotation, overlaying numbered labels on screenshots before sending to Gemini, OCR pre-processing, or element detection layers

**Scoring bands:**
- **25–30**: Contextual visual understanding across multiple distinct UI states; coordinates/actions fully derived from Gemini's vision output; dynamic UI states handled; multi-step reasoning evident
- **17–24**: Solid visual element recognition and basic context-awareness; handles a few UI states; coordinates come from Gemini but no advanced grounding
- **9–16**: Basic element recognition; limited to one or two UI types; Gemini asked about the screen but actions are partially hardcoded or DOM-assisted
- **3–8**: Gemini is called with a screenshot but its output is not actually used for precise element targeting; actions are positional guesses
- **0–2**: No evidence of visual precision; clicks are hardcoded coordinates or purely DOM-based regardless of Gemini's output

**Record as:** `1.2 = __ / 30`

---

### 1.3 — Seamlessness & Fluidity of the Agent Loop
**Max: 25 points**

The experience should feel like a live, intelligent co-pilot reacting in real time — not a batch script that runs start-to-finish.

**Look for:**
- [ ] A continuous, iterative action loop is implemented: `observe → reason → act → observe` — not a linear sequence of hardcoded steps
- [ ] Streaming or near-real-time API responses used (look for `stream=True`, async generators, WebSocket output, or similar)
- [ ] The user can provide new instructions or corrections **mid-task**, not just at launch
- [ ] The agent narrates or reports what it is currently doing in real time (audio narration, live text overlay, streaming log visible to user, status messages)
- [ ] Adaptive waiting rather than fixed sleeps: the agent checks for a condition (page loaded, element appeared) rather than `time.sleep(N)` as the primary synchronization mechanism

**Scoring bands:**
- **21–25**: True agentic loop; real-time feedback to user; mid-task interruption supported; adaptive waiting; streaming responses
- **14–20**: Functional loop with feedback between steps; interruption possible but not seamless; some fixed sleeps
- **7–13**: Sequential steps with some feedback; feels turn-based; user cannot intervene mid-task
- **2–6**: Mostly linear/scripted execution; minimal or no feedback to user during run
- **0–1**: Batch execution with no loop; runs to completion with zero real-time feedback

**Record as:** `1.3 = __ / 25`

---

### 1.4 — Distinct Persona or User Experience Layer
**Max: 15 points**

**Look for:**
- [ ] Voice output: TTS integration, Gemini Live API audio, or any text-to-speech that narrates the agent's actions
- [ ] A named persona, character, or configured system prompt that gives the agent a consistent identity/voice
- [ ] A real frontend (web UI, desktop app, overlay) beyond a terminal — with status, progress, or visual feedback
- [ ] Verbal or visual narration of what the agent is doing step-by-step as it navigates

**Scoring bands:**
- **13–15**: Rich UX: voice narration + named persona + polished frontend; feels like a product
- **9–12**: Two of the above elements present and working (e.g., voice + frontend, or persona + frontend)
- **5–8**: One UX element present (e.g., basic web UI OR voice only); functional but minimal
- **2–4**: Terminal logs only; no UX design consideration beyond print statements
- **0–1**: No UX layer at all; raw crash-prone output

**Record as:** `1.4 = __ / 15`

---

### SECTION 1 — TOTAL

```
S1 = 1.1 + 1.2 + 1.3 + 1.4
S1 = __ + __ + __ + __ = __ / 100
```

**Interpretation:**
- 85–100: Exceptional — genuinely immersive, vision-first, context-aware UI navigator
- 70–84: Strong — solid multimodal implementation with minor gaps
- 50–69: Competent — functional use of vision but experience feels mechanical or turn-based
- 30–49: Weak — vision present but largely decorative; mostly text/DOM-driven
- 0–29: Failing — no meaningful departure from a text chatbot

---

## SECTION 2 — TECHNICAL IMPLEMENTATION & AGENT ARCHITECTURE
**Official weight: 30% of total hackathon score**
**This sheet scores it: 0–100 points**

Sub-score budget breakdown (must sum to your Section 2 total):

| Sub-criterion | Max Points |
|---|---|
| 2.1 Mandatory Tech Compliance (gate) | 20 |
| 2.2 Quality of Google GenAI SDK / ADK Usage | 20 |
| 2.3 Agent Logic & System Design | 25 |
| 2.4 Error Handling, Robustness & Edge Cases | 15 |
| 2.5 Grounding & Hallucination Resistance | 12 |
| 2.6 Google Cloud Native Architecture | 8 |
| **TOTAL** | **100** |

---

### 2.1 — Mandatory Tech Compliance (UI Navigator)
**Max: 20 points**
**⚠ This is also a PASS/FAIL disqualification gate. Failing all three = flag for disqualification regardless of score.**

Verify all three mandatory requirements:

**Requirement A — Gemini Multimodal for Screenshots/Screen Recordings (up to 7 pts):**
- [ ] Explicit API calls to a real, current Gemini model (e.g., `gemini-2.0-flash`, `gemini-1.5-pro`, `gemini-2.5-pro`) with **image or video content** in the message payload
- [ ] The image content is a live screenshot or screen recording frame — not a static asset, test fixture, or stock image
- [ ] Look for: `Part.from_image()`, `inline_data` with `mime_type: image/png` or `image/jpeg`, base64-encoded bytes passed to Gemini, or `types.Content` with image parts in the GenAI SDK

**Requirement B — Executable Actions Derived from Gemini Output (up to 7 pts):**
- [ ] Agent outputs are wired to real action-execution: mouse clicks, keyboard input, browser navigation, shell commands
- [ ] Look for: `pyautogui`, `playwright`, `selenium`, `subprocess`, `xdotool`, ADB commands, browser CDP calls
- [ ] **Actions must be dynamically derived from Gemini's response** — not hardcoded regardless of what Gemini says. Check that the action-execution code reads from a variable populated by Gemini's output.

**Requirement C — Google Cloud Hosting (up to 6 pts):**
- [ ] Evidence of actual deployment configuration for GCP: `Cloud Run`, `App Engine`, `Compute Engine`, `GKE`, `Cloud Functions`, or `Vertex AI`
- [ ] Look in: `Dockerfile` + `cloudbuild.yaml`, `app.yaml`, `.github/workflows/` with GCP deploy steps, `gcloud run deploy` commands in scripts, or Terraform with GCP provider
- [ ] A file referencing a real GCP project ID in a deployment context counts; a `requirements.txt` with `google-cloud-*` packages alone does NOT

**Scoring bands:**
- **18–20**: All 3 requirements fully and unambiguously met with clear code evidence
- **13–17**: All 3 met but one has minor gaps (e.g., deployment config present but incomplete)
- **8–12**: 2 of 3 requirements clearly met; one is missing or only partially evidenced — **flag for disqualification**
- **3–7**: Only 1 requirement clearly met — **flag for disqualification**
- **0–2**: None clearly met — **flag for disqualification; recommend rejection from category**

**Gate result:** PASS / PARTIAL / FAIL
**Record as:** `2.1 = __ / 20`

---

### 2.2 — Quality of Google GenAI SDK / ADK Usage
**Max: 20 points**

**Look for:**
- [ ] Official `google-generativeai` Python SDK or `google-cloud-aiplatform` SDK used (not raw `requests` / `httpx` to Gemini endpoints, unless a justified wrapper exists)
- [ ] Model name is a real, current Gemini model — not a hallucinated or deprecated string
- [ ] Use of ADK (`google.adk`): agent definitions, tool registrations, runner setup — ADK usage is a strong positive signal
- [ ] Multi-turn conversation history is correctly maintained and passed across calls (not re-initialized every call)
- [ ] Gemini function calling / tool use implemented where it would improve the agent (e.g., defining `click`, `type`, `scroll` as Gemini tools)
- [ ] API response structure is correctly parsed — content blocks accessed properly, not just `str(response)`

**Scoring bands:**
- **17–20**: Idiomatic SDK usage throughout; ADK used appropriately; multi-turn history correct; function calling/tool use implemented; clean response parsing
- **13–16**: Correct SDK usage; multi-turn history present; ADK absent or minimal; response parsing mostly correct
- **8–12**: SDK used but with significant issues (e.g., history not maintained, wrong response parsing, deprecated patterns)
- **3–7**: Mix of raw HTTP and SDK; SDK used superficially or only in one place
- **0–2**: Raw HTTP calls only, or no evidence of any official Google SDK

**Record as:** `2.2 = __ / 20`

---

### 2.3 — Agent Logic & System Design
**Max: 25 points**

**Look for:**
- [ ] A clearly defined agentic loop with explicit states or phases (e.g., `OBSERVE`, `PLAN`, `ACT`, `VERIFY`, `DONE`, `FAILED`)
- [ ] Gemini's system prompt or instruction includes reasoning guidance: chain-of-thought, step-by-step planning, or explicit instruction to reason before acting
- [ ] Task decomposition: the agent can break a high-level goal (e.g., "book a flight") into sub-steps autonomously — not just execute one hardcoded step per call
- [ ] State/memory across steps: action history, current task context, or intermediate results are tracked and passed forward in a structured way (not lost between iterations)
- [ ] Explicit **termination conditions**: the agent knows when the task is complete or has irrecoverably failed — it does not loop forever
- [ ] Basic safety guardrails: the agent does not blindly execute any string Gemini outputs as a shell command or action without some validation layer

**Scoring bands:**
- **21–25**: Well-architected loop with defined states; task decomposition; persistent state/memory; clear termination; safety checks present
- **15–20**: Solid loop and state management; task decomposition present but shallow; termination conditions defined; no safety checks
- **8–14**: Functional loop but fragile; state is ad hoc (e.g., passed as a growing string); no decomposition; termination is implicit
- **3–7**: Linear script with a loop wrapper; no real reasoning or state management; tasks are hardcoded sequences
- **0–2**: No identifiable agent architecture; purely procedural, top-to-bottom code

**Record as:** `2.3 = __ / 25`

---

### 2.4 — Error Handling, Robustness & Edge Cases
**Max: 15 points**

**Look for:**
- [ ] Gemini API call failures handled with retry logic or graceful degradation — not bare `except: pass` or unhandled exceptions
- [ ] Handling when Gemini returns unexpected or unparseable output (e.g., JSON parse error, missing required fields, empty response)
- [ ] Timeouts implemented for actions that could hang indefinitely (e.g., waiting for page load, waiting for element to appear)
- [ ] Agent does not crash on unexpected UI states: CAPTCHA page, network error, 404, session timeout, unexpected popup
- [ ] Meaningful logging or structured error reporting that would help diagnose failures in production (not just `print("error")`)

**Scoring bands:**
- **13–15**: Comprehensive error handling across API failures, Gemini output parsing, action execution, and unexpected UI states; graceful recovery in all major paths; production-grade logging
- **9–12**: Most error paths handled; timeouts present; 1–2 notable edge cases unhandled
- **5–8**: Basic try/catch exists but is shallow; will crash on moderate edge cases; no timeouts
- **2–4**: Minimal error handling; only happy path works reliably
- **0–1**: No error handling; bare unprotected code throughout

**Record as:** `2.4 = __ / 15`

---

### 2.5 — Grounding & Hallucination Resistance
**Max: 12 points**

For a UI Navigator, hallucination means Gemini inventing UI elements that don't exist, producing nonsensical coordinates, or describing actions that don't match what's on screen.

**Look for:**
- [ ] **Structured output enforcement**: Gemini is prompted to respond in a strict, parseable format (JSON schema, XML, defined fields) for action outputs — not free-form prose
- [ ] **Post-action verification**: after executing an action, the agent captures a new screenshot and checks whether the expected result occurred before proceeding
- [ ] **Coordinate validation**: before clicking, the agent checks that coordinates are within screen bounds and not (0,0) or obviously wrong
- [ ] **Advanced grounding**: Set-of-Mark (SoM) labeling, numbered element overlays, OCR pre-processing, or any technique that anchors Gemini's output to real on-screen elements
- [ ] **Retry on bad output**: if Gemini's response fails parsing or produces invalid coordinates, the agent retries with the same or clarified prompt — not silently proceeds with a broken action

**Scoring bands:**
- **10–12**: Structured output enforced via schema; post-action screenshot verification; coordinate bounds checking; retry logic on parse failure
- **7–9**: Structured output and some verification present; coordinate validation absent or incomplete
- **4–6**: Structured output attempted but verification loop absent; Gemini output trusted after parsing
- **1–3**: Minimal structured output; no verification; hallucinations would silently cause wrong actions
- **0**: No grounding whatsoever; Gemini's free-text output executed verbatim

**Record as:** `2.5 = __ / 12`

---

### 2.6 — Google Cloud Native Architecture
**Max: 8 points**

**Look for:**
- [ ] Backend deployed to a specific named GCP service (Cloud Run preferred; also Vertex AI, GKE, App Engine, Cloud Functions)
- [ ] Use of **additional GCP services** beyond just the Gemini API call: Cloud Storage (for screenshots/recordings), Firestore (for state/history), Pub/Sub (for task queuing), Secret Manager (for API keys), Cloud Logging
- [ ] Infrastructure-as-code or deployment automation: Terraform with GCP provider, `cloudbuild.yaml`, `gcloud` deploy scripts in the repo
- [ ] Gemini calls routed through **Vertex AI endpoint** (`aiplatform.googleapis.com`) rather than the consumer API — stronger signal of cloud-native design

**Scoring bands:**
- **7–8**: Deployed to GCP + 2 or more additional GCP services used meaningfully + IaC/automation present
- **5–6**: Deployed to GCP + 1 additional GCP service; deployment documented but manual
- **3–4**: GCP deployment clearly configured; Gemini API used but no other GCP services
- **1–2**: GCP deployment mentioned or partially configured but not clearly proven in code
- **0**: No GCP deployment evidence found anywhere in the codebase

**Record as:** `2.6 = __ / 8`

---

### SECTION 2 — TOTAL

```
S2 = 2.1 + 2.2 + 2.3 + 2.4 + 2.5 + 2.6
S2 = __ + __ + __ + __ + __ + __ = __ / 100
```

**Interpretation:**
- 85–100: Exemplary — all mandatory tech correct; robust, grounded, cloud-native architecture
- 70–84: Strong — mandatory tech met; minor robustness or architecture gaps
- 50–69: Functional — mostly correct tech usage; several robustness and design weaknesses
- 30–49: Weak — mandatory tech partially met; agent logic shallow; not production-ready
- 0–29: Failing — mandatory tech not met or serious architectural flaws

---

## FINAL WEIGHTED SCORE

The official hackathon weights the two criteria as 40% and 30%. Both sections are scored out of 100, then weighted:

```
Weighted Score = (S1 × 0.40) + (S2 × 0.30)

Maximum possible from these two criteria = (100 × 0.40) + (100 × 0.30) = 70 points

Example: S1 = 79, S2 = 74
→ (79 × 0.40) + (74 × 0.30) = 31.6 + 22.2 = 53.8 / 70
```

The remaining 30 points (Demo & Presentation) require video review and are not covered by this sheet.

---

## OUTPUT FORMAT

Produce your audit report in **exactly** this structure:

---

### ═══════════════════════════════════
### AUDIT REPORT
### ═══════════════════════════════════

**Repository:** [URL or path audited]
**Audited by:** [AI agent name/model]
**Date:** [Date of audit]

---

#### ▶ MANDATORY TECH CHECK (Disqualification Gate)

| Requirement | Status | Evidence (file:line or description) |
|---|---|---|
| A — Gemini multimodal with live screenshots | PASS / PARTIAL / FAIL | |
| B — Executable actions derived from Gemini output | PASS / PARTIAL / FAIL | |
| C — Google Cloud hosting configuration | PASS / PARTIAL / FAIL | |

**Gate Result:** PASS / PARTIAL / FAIL
**Disqualification Risk:** None / Low / Medium / HIGH

---

#### ▶ SECTION 1 — INNOVATION & MULTIMODAL UX

| Sub-criterion | Max | Score | Key Evidence | What's Missing |
|---|---|---|---|---|
| 1.1 Beyond Text Box | 30 | __ | [file:line] | [gap or "none"] |
| 1.2 Visual Precision | 30 | __ | [file:line] | [gap or "none"] |
| 1.3 Fluidity & Loop | 25 | __ | [file:line] | [gap or "none"] |
| 1.4 Persona & UX Layer | 15 | __ | [file:line] | [gap or "none"] |
| **SECTION 1 TOTAL** | **100** | **__** | | |

**Section 1 Narrative:** [3–5 sentences explaining the score. Reference specific files or patterns found.]

---

#### ▶ SECTION 2 — TECHNICAL IMPLEMENTATION & ARCHITECTURE

| Sub-criterion | Max | Score | Key Evidence | What's Missing |
|---|---|---|---|---|
| 2.1 Mandatory Tech Compliance | 20 | __ | [file:line] | [gap or "none"] |
| 2.2 GenAI SDK / ADK Quality | 20 | __ | [file:line] | [gap or "none"] |
| 2.3 Agent Logic & System Design | 25 | __ | [file:line] | [gap or "none"] |
| 2.4 Error Handling & Robustness | 15 | __ | [file:line] | [gap or "none"] |
| 2.5 Grounding & Hallucination Resistance | 12 | __ | [file:line] | [gap or "none"] |
| 2.6 GCP Native Architecture | 8 | __ | [file:line] | [gap or "none"] |
| **SECTION 2 TOTAL** | **100** | **__** | | |

**Section 2 Narrative:** [3–5 sentences explaining the score. Reference specific files or patterns found.]

---

#### ▶ FINAL WEIGHTED SCORE

```
S1 = __ / 100   →   S1 × 0.40 = __
S2 = __ / 100   →   S2 × 0.30 = __

Combined Score (Criteria 1+2 only) = __ / 70
Demo & Presentation (30 pts) = NOT ASSESSED — requires video review
```

---

#### ▶ TOP 3 STRENGTHS
1. **[Title]** — [Finding with file:line reference]
2. **[Title]** — [Finding with file:line reference]
3. **[Title]** — [Finding with file:line reference]

#### ▶ TOP 3 GAPS (Highest Impact to Fix Before Deadline)
1. **[Title]** — [Gap with file:line and specific suggested fix]
2. **[Title]** — [Gap with file:line and specific suggested fix]
3. **[Title]** — [Gap with file:line and specific suggested fix]

#### ▶ DISQUALIFICATION FLAGS
- [List any mandatory tech failures, rule violations, or eligibility concerns — or write "None identified"]

---
*This sheet covers Judging Criteria 1 (Innovation & Multimodal UX, 40%) and Criteria 2 (Technical Implementation, 30%) only.*
*Criteria 3 — Demo & Presentation (30%) — requires video review and is not assessed here.*