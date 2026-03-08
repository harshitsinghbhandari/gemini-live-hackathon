# Aegis — Frontend Handoff Document
**Version 1.0 · For Developer Use**
All three surfaces: Mac App, Mobile App, Dashboard

---

## Design Principles (Read First)

Before touching any screen, understand the core perceptual rule that governs every design decision in Aegis:

**Silence is the product.** Aegis communicates trust not by looking secure but by behaving securely. The UI should feel like a senior engineer's tool — calm, precise, never theatrical. Color is used exclusively as signal. When nothing requires attention, the screen earns its quietness. When something requires attention, the UI shifts tone deliberately and the contrast does the work.

Reference aesthetic: 1Password, Linear, Vercel Dashboard. Not a hacker terminal. Not a sci-fi prop.

**Color rules:**
- Green (#2D6A4F / sage) → system is active, action is safe, read-only
- Amber (#D97706) → action is reversible but requires confirmation
- Red (#DC2626) → irreversible action, full authorization required
- These three colors must never appear decoratively. They only appear when they mean something.

**Typography:**
- UI labels, headings, body: clean geometric sans-serif (e.g. Geist, Inter as fallback)
- All timestamps, file paths, device IDs, technical strings: monospace (e.g. Geist Mono, JetBrains Mono)

**Surfaces:**
- Background: `#0D1117`
- Card / elevated surface: `#161B22`
- Higher elevated surface: `#1C2128`
- Border: `rgba(255,255,255,0.06)` — barely visible, just structural
- Text primary: `#E6EDF3`
- Text secondary: `#7D8590`
- Text dim / metadata: `#484F58`

---

## Surface 1 — Mac App (1440 × 900px)

The Mac App is the primary control interface. It runs locally on port 3001, connects to the Aegis agent via WebSocket on port 8765, and to the Helper Server via HTTP on port 8766. The user speaks to it, monitors actions through it, and stops sessions from it. It has five screens.

---

### Screen 1 · Idle / Pre-flight

**Purpose:** This is the first screen a user sees when they open the Mac App. Nothing is running yet. The screen communicates that two things must be true before a session can start: the Helper Server must be running, and the Aegis agent must be connected. It does not rush the user. It waits.

**Layout:** Centered single-column layout. Generous empty space above and below the central content block. The content block sits at vertical center of the 900px canvas.

**Top bar:** Persistent across all Mac App screens. Left: small Aegis shield icon (geometric, simple — a shield outline with a minimal checkmark or lock mark inside, no gradients, no glow) followed by the wordmark "Aegis" in medium weight. Right side of the top bar: two small inline status indicators displayed as rows or a horizontal pair:
- "Helper Server" with a dot indicator. When offline: dot is `#484F58` (dim grey). When online: dot is `#2D6A4F` (sage green). Label text in monospace, small.
- "Agent" with a dot indicator. Same states — grey when disconnected, green when connected. This dot only turns green after the user has clicked Connect, not automatically.

**Center content block:**
- The Aegis shield mark, rendered at approximately 48px, in `#7D8590` when idle (not green — it earns color when active)
- Wordmark "AEGIS" below the mark, medium weight, 18px, letter-spaced at 0.1em, color `#7D8590`
- Beneath that, 24px of space, then a single "Start Session" button. This button is outlined only (no fill), border `rgba(255,255,255,0.12)`, text color `#7D8590`, corner radius 6px, padding 10px 24px. It reads as available but not urgent.
- The button is only visually active (border brightens slightly, text goes to `#E6EDF3`) once the Helper Server dot is green. Before that it can exist but should appear disabled.

**Behavioral note for the developer:** The Helper Server status is polled via HTTP GET to `localhost:8766/health` on a short interval. The Agent status is only confirmed after a successful WebSocket connection attempt to `localhost:8765`. These are sequential — Helper Server first, then Agent. The UI should reflect that sequence visually: Agent indicator only becomes meaningful once Helper Server is green.

**What this screen communicates to the user:** The system is in pre-flight. Two conditions must be met. One is automatic (Helper Server running in background), one requires intent (clicking Connect). This two-step pattern is deliberate — it trains the user to understand that Aegis has a chain of trust, not a single on/off switch.

---

### Screen 2 · Listening

**Purpose:** The user has connected and the session is live. Gemini Live API is active, the microphone is open, and the agent is processing audio in real time. This screen should feel like a presence is actively paying attention. The listening state is the dominant state — everything else in the app is subordinate to it until an action appears.

**Layout:** Full-screen takeover. The canvas is 1440 × 900. Top bar remains. Everything else is centered around the audio visualizer.

**Top bar:** Same as Screen 1. Both status dots now green. "Stop" text link on the far right of the top bar — small, muted (`#7D8590`), no button chrome. It is present but not prominent. It reads as available, not suggested.

**Center element — audio visualizer:** A circular oscilloscope ring centered on the canvas. Not a blob. Not an orb with glow. A geometric ring — approximately 200px diameter — made of thin radial lines or a single circle path that deforms subtly in response to microphone amplitude. When no audio is detected, it rests as a perfect circle with very low opacity lines. When voice is detected, the ring deforms outward at points corresponding to audio frequency, returning quickly. The animation is fluid but restrained. The ring color: `#2D6A4F` at 60% opacity at rest, 90% opacity when active. No glow. No drop shadow. The restraint is the point.

**Transcript bubble:** A dark surface card (`#161B22`, border `rgba(255,255,255,0.06)`, border-radius 10px) positioned below the visualizer with approximately 32px gap. Width: 480px max, centered. Padding: 16px 20px. Inside: live transcript text in monospace, 13px, color `#7D8590`. As words are recognized they appear progressively. A blinking cursor character at the end of the current text. This is a display-only element — the user does not interact with it.

**Empty state of transcript bubble:** Before the user has spoken, the bubble shows a placeholder in dim text: "Listening for input…" in monospace, `#484F58`.

**Bottom center:** The canvas has 40px bottom padding. Nothing else lives here during the listening state.

**What this screen communicates:** A calm, attentive presence. The user should feel heard without feeling surveilled. The oscilloscope ring gives visual confirmation that audio is being received without being dramatic about it.

---

### Screen 3 · Executing — Green Actions

**Purpose:** The agent has processed the user's speech and is executing one or more green-tier (read-only) actions. Green actions require no user confirmation and execute automatically. The screen should not interrupt the flow — the listening state remains primary, and green actions appear peripherally as a quiet log.

**Layout:** The audio visualizer shifts left — not to the edge, but off-center. Approximately at x: 560px (horizontally). It scales down slightly, to about 160px diameter. The transcript bubble follows it, still centered beneath it in its new position. A right panel slides in from the right edge of the canvas.

**Right action panel:** Width 320px. Right edge flush with canvas right edge (no margin). Top-to-bottom: action cards stack from top, newest at bottom (chronological feed). Each card:
- Height: 52px
- Background: `#161B22`
- Left border: 3px solid `#2D6A4F` (sage green)
- Padding: 12px 16px
- Content: one line of action description text, 12px, regular weight, `#E6EDF3`. Below it one line of monospace timestamp, 10px, `#484F58`
- No icons. No badges. No tier label on green cards — the green left border is the only signal needed.
- Cards have a subtle fade-in animation as they appear (opacity 0 → 1, translateY 6px → 0, duration 200ms)

**Separation between visualizer area and right panel:** No explicit divider line. The panel background (`#161B22`) against the page background (`#0D1117`) creates natural separation.

**Behavioral note:** The right panel persists across Screen 3, 4, and 5. Green action cards continue to accumulate in this panel throughout the session. Yellow and red cards, when they appear, are visually differentiated (see Screens 4 and 5).

---

### Screen 4 · Yellow Action — Verbal Confirmation

**Purpose:** The agent has proposed an action classified as yellow-tier — reversible but not read-only. Examples: moving files to trash, renaming folders, sending a draft message. The agent cannot proceed until the user verbally confirms. This screen should communicate a deliberate pause — not an alarm, but a clear moment of "this needs your attention."

**Layout:** Same as Screen 3 — visualizer shifted left, right panel visible. Two changes occur:

**Visualizer state change:** The ring transitions from green to amber. Color shifts from `#2D6A4F` to `#D97706`. The transition is smooth, approximately 400ms. The ring slows its deformation — it is now listening specifically for a confirmation word, not open-ended speech. This visual shift is the first signal to the user that something has changed.

**Right panel — yellow card:** The most recent card in the right panel is the yellow action card. It is larger than green cards:
- Height: auto, minimum 80px
- Background: `#1C2128` (slightly elevated)
- Left border: 3px solid `#D97706` (amber)
- Padding: 14px 16px
- Line 1: action description, 13px, medium weight, `#E6EDF3`
- Line 2: monospace detail (e.g. file path or scope), 11px, `#7D8590`
- Line 3: "Verbal confirmation required" in 11px, `#D97706`, italic
- Below line 3: a minimal horizontal waveform — 16 bars, each 2px wide, 3px height at rest, amber color, animating when mic is active. This waveform is the only animation in the card.
- Line below waveform: monospace 10px, `#484F58`: "say "confirm" to proceed · "cancel" to abort"

**Behavioral note:** The agent is actively listening for the words "confirm" or "cancel." If confirmed verbally, the yellow card updates its status (border fades, a small checkmark or "confirmed" label appears in dim text) and slides into the green cards stack. If cancelled, border shifts to red briefly then fades out. The agent returns to the listening state.

---

### Screen 5 · Red Action — Full Authorization Required

**Purpose:** The agent has proposed an irreversible action — classified red-tier. This is the most serious state in the app. The full screen shifts tone. The user must authorize via their mobile device using biometric authentication. This screen should feel like the system has stopped everything and is asking you to look carefully at what is about to happen.

**Layout:** The visualizer and transcript are no longer the dominant elements. A central modal card takes over the canvas.

**Background treatment:** The page background dims with a dark overlay (`#0D1117` at additional 40% opacity on top of the existing background, or simply a darker shade like `#070A0E`). The right action panel is still visible but dims to 40% opacity — it's not gone, but it is no longer active.

**Central modal card:**
- Width: 560px, horizontally centered
- Background: `#161B22`
- Border: 1px solid `rgba(220,38,38,0.3)` — a subtle red tint, not aggressive
- Border-radius: 12px
- Padding: 32px
- No drop shadow with glow. If shadow, use `0 8px 32px rgba(0,0,0,0.4)` — dark shadow only.

**Card contents (top to bottom):**
- Small label: "AUTHORIZATION REQUIRED" in monospace, 10px, letter-spaced 0.12em, `#DC2626`, uppercase
- 16px gap
- Action description in plain English, 16px, medium weight, `#E6EDF3`, line-height 1.6. Example: "Permanently delete database backup." Keep this human-readable — no file paths in the headline.
- Below the description, one line of monospace detail: file path and size, 12px, `#7D8590`
- 24px gap
- "This action cannot be undone." in 12px, regular weight, `#DC2626`
- 24px gap
- Countdown timer: large monospace numerals, 32px, `#E6EDF3`, displaying seconds counting down from 30. Format: `0:30`, `0:29`... At 10 seconds remaining, the timer color shifts to `#DC2626`.
- 16px gap
- One line of dim text: "Approval request sent to mobile device" in monospace 11px, `#484F58`
- A subtle inline spinner (16px, thin stroke, rotating) next to that text, same color
- 32px gap
- At the very bottom of the card: "Cancel Action" as a text link, 12px, `#7D8590`, centered. No button chrome.

**Behavioral note:** If the user approves from mobile, this card dismisses with a fade (200ms). A green "Authorized" confirmation card appears briefly in the right panel before the action executes and the agent returns to listening. If denied or timed out, the card dismisses, a red "Blocked" card appears in the right panel, and the agent returns to listening.

---

## Surface 2 — Mobile App (390 × 844px)

The Mobile App is a companion Progressive Web App. It runs on the user's phone and serves one primary purpose: to receive red-tier authorization requests from the Aegis agent and allow the user to approve or deny them using biometric authentication. It is also a remote stop — the user can stop the Mac session from their phone.

Most of the time this app is in a waiting state. It should be minimal and undemanding when nothing is happening. It should be clear and decisive when an authorization request arrives.

---

### Screen 1 · Waiting / Linked

**Purpose:** The mobile app is open, connected, and waiting for an authorization request. Nothing is happening. The screen should communicate exactly that: everything is fine, I'm watching, no action needed from you.

**Layout:** Full screen, single column, vertically centered content block. Standard iOS status bar at top. Home indicator space at bottom.

**Content block (centered):**
- Aegis shield mark at 40px, color `#3D6B8C` (a muted blue-grey — distinct from the Mac app green, indicating this is a companion device, not a control surface)
- "Aegis Mobile" wordmark below, 15px, medium weight, `#7D8590`
- 20px gap
- One status row: a small dot in `#2D6A4F` (green) followed by "Session Active" in monospace 12px, `#7D8590`
- 8px below that: masked device ID string in monospace 11px, `#484F58`. Example: `device · iphone-7f3a`

**Bottom of screen (persistent across all mobile screens):**
- 32px above home indicator: "Stop Session" as a button. Outlined only, border `rgba(220,38,38,0.4)`, text `#DC2626`, 12px, width 200px, centered, border-radius 8px, padding 10px. This button is always accessible. It should never be buried or disabled.

**What this screen communicates:** The phone is armed. Nothing is needed from you right now. The stop button is there if you need it.

---

### Screen 2 · Red Authorization Request

**Purpose:** A red-tier action has been triggered on the Mac. The mobile app has received the authorization request. The user must read what is being asked, understand it, and make a deliberate choice to approve or deny. This is the most consequential screen in the entire Aegis system. Every design decision here should reduce the chance of accidental approval.

**Layout:** Full screen. A central card takes up approximately 70% of the vertical height, centered with equal margin top and bottom (minus the top status bar).

**Top of screen:** A slim banner at the very top of the content area (below status bar). Background `rgba(220,38,38,0.1)`, border-bottom `1px solid rgba(220,38,38,0.2)`. Text inside: "APPROVAL REQUIRED" in monospace 10px, letter-spaced, `#DC2626`, centered. Height 36px. This banner announces the state change before the user reads the card.

**Central authorization card:**
- Background: `#161B22`
- Border: 1px solid `rgba(220,38,38,0.25)`
- Border-radius: 14px
- Padding: 28px 24px
- Margin: 16px on left and right

**Card contents (top to bottom):**
- Small label: "IRREVERSIBLE ACTION" in monospace 10px, letter-spaced 0.1em, `#DC2626`
- 14px gap
- Action description in plain English, 17px, medium weight, `#E6EDF3`, line-height 1.5. Human-readable, no jargon. Example: "Permanently delete database backup."
- "This cannot be undone." on its own line, 13px, `#DC2626`
- 16px gap
- Monospace detail row: file path and relevant metadata, 12px, `#7D8590`
- 24px gap
- Countdown timer: monospace numerals, 28px, `#E6EDF3`. Same behavior as Mac — turns red at 10 seconds. Label above timer in monospace 10px `#484F58`: "TIME REMAINING"
- 28px gap
- Two buttons, side by side, equal vertical padding:
  - **Deny button (left):** Width 55% of card inner width. Background `#1C2128`. Border `1px solid rgba(255,255,255,0.1)`. Text "Deny" in 15px medium weight, `#E6EDF3`. Border-radius 10px. Padding 16px. This button is intentionally larger and easier to tap. The safe action is the default action.
  - **Approve button (right):** Width 40% of card inner width. Background transparent. Border `1px solid rgba(220,38,38,0.5)`. Text "Approve" in 15px medium weight, `#DC2626`. Border-radius 10px. Padding 16px. Slightly narrower than Deny. Triggers Face ID or Touch ID on tap — the OS biometric prompt appears natively. The button itself does not execute the action; the biometric confirmation does.

**Behavioral note for developer:** The size difference between Deny and Approve is intentional and important. In security UX, the safe default (Deny) should always be the largest, easiest target. Approve requires deliberate targeting and then a second deliberate action (biometric). If the countdown reaches zero without a response, the app auto-denies and transitions to Screen 3 (denied state).

**Bottom of screen:** "Stop Session" button remains visible below the card, same styling as Screen 1.

---

### Screen 3 · Post Authorization

**Purpose:** The user has made a decision — either approved or denied. This screen confirms the outcome clearly and returns the app to a neutral state. The resolution should feel administrative, not emotional. No celebration for approving, no alarm for denying.

**This screen has two states — show both as separate artboards or clearly separated in the design:**

**State A — Approved:**
- Center of screen: a circle (48px diameter) with border `1px solid rgba(45,106,79,0.4)`, background `rgba(45,106,79,0.1)`. Inside: a checkmark in `#2D6A4F`, 20px stroke.
- Below the circle: "Action Authorized" in 15px, medium weight, `#E6EDF3`
- One line below: "Executing on Mac." in monospace 12px, `#7D8590`
- 32px below that: "Return to Monitor" as a text link, 12px, `#7D8590`
- After 3 seconds the app transitions back to Screen 1 automatically. The text link is for manual return if the user wants to go back immediately.

**State B — Denied (or timed out):**
- Same layout. Circle has border `rgba(220,38,38,0.3)`, background `rgba(220,38,38,0.08)`. Inside: an X mark in `#DC2626`.
- "Action Blocked" in 15px, medium weight, `#E6EDF3`
- "Aegis halted execution." in monospace 12px, `#7D8590`
- If auto-denied by timeout: "Request timed out — action denied automatically." in monospace 11px, `#484F58`
- "Return to Monitor" text link, same as State A.
- Auto-return to Screen 1 after 3 seconds.

---

## Surface 3 — Dashboard (Adaptive, base 1440px wide)

The Dashboard is a remote monitoring interface accessible at `https://aegis.projectalpha.in`. It is not a control surface — the user cannot start or stop the agent from here. It is a record. Every action the agent has ever taken or attempted is here, classified, timestamped, and available for inspection. It adapts from 1440px desktop down to 768px tablet. Three screens.

---

### Screen 1 · Main Audit Log

**Purpose:** The primary view of the dashboard. The user can see the agent's current status, review session statistics at a glance, scan the chronological log of all actions, and inspect any individual action in detail. This screen is used both during active sessions (live feed) and after sessions (historical review).

**Layout at 1440px:** Full-width header. Below header: a stats row spanning full width. Below stats: a two-column content area. Left column 65%, right column 35%.

**Header bar (full width, height 56px):**
- Left: Aegis shield mark (20px) + "Aegis" wordmark in medium weight + a separator + "Audit Console" in `#7D8590` regular weight
- Center: empty
- Right: Agent status pill — a small rounded pill, background `rgba(45,106,79,0.12)`, border `1px solid rgba(45,106,79,0.3)`, containing a 6px dot in `#2D6A4F` and label "Agent Active" in 12px monospace, `#2D6A4F`. When offline this pill switches to amber (see Screen 2).
- Header bottom border: `1px solid rgba(255,255,255,0.06)`

**Stats row (below header, full width, height 96px):**
Four cards in a row, equal width, separated by 1px borders or 12px gaps. Each card:
- Top border: 2px solid in tier color (green / amber / red / `#484F58` for Blocked)
- Content: large numeral (28px, bold, tier color) and below it a label in monospace 10px, letter-spaced, `#7D8590`
- Labels: "GREEN EXECUTED" / "YELLOW CONFIRMED" / "RED AUTHORIZED" / "BLOCKED"
- Background: `#161B22`

**Left column — Audit log table:**
- Column header row: monospace 10px, `#484F58`, letter-spaced. Columns: (no label — tier dot) | ACTION | TIME | STATUS
- Each log row (48px height):
  - Left edge: 4px colored border in tier color (green / amber / red)
  - Tier dot: 6px circle in tier color, 16px from left
  - Action description: 13px, regular weight, `#E6EDF3`, truncated with ellipsis if too long
  - Timestamp: monospace 12px, `#484F58`, right-aligned in time column
  - Status label: monospace 11px, color varies — "executed" `#7D8590`, "confirmed" `#D97706`, "authorized" `#2D6A4F`, "blocked" `#DC2626`
  - Alternating row backgrounds: even rows `#0D1117`, odd rows `rgba(255,255,255,0.01)` — barely perceptible, just enough to aid scanning
  - Selected row: background `#1C2128`, left border brightens to full opacity
  - Hover state: background `#161B22`
- The log is a live feed during active sessions — new rows append at the bottom with a subtle fade-in

**Right column — Detail panel:**
- Background: `#161B22`, left border `1px solid rgba(255,255,255,0.06)`
- Default (no selection): centered text "Select an action to inspect" in 12px, `#484F58`
- When a row is selected:
  - Top label: "ACTION DETAIL" in monospace 10px, letter-spaced, `#484F58`
  - Tier badge: small pill in tier color background tint with tier color text, e.g. "GREEN" or "RED"
  - Action description: 14px, medium weight, `#E6EDF3`, full text (not truncated)
  - Metadata rows: each row is a label-value pair. Label in monospace 10px `#484F58`, value in monospace 11px `#7D8590`. Rows: Timestamp | Session ID | Risk Tier | Outcome | Auth Device (if red) | Auth Method (if red)
  - Bottom: "Export Entry" text link, 11px, `#7D8590`

**Layout at 768px (tablet):**
- Stats row collapses to 2×2 grid
- Two-column layout becomes single column — detail panel moves below the log table
- When a row is selected on tablet, detail panel expands below the log in-place (accordion style)

---

### Screen 2 · Agent Offline

**Purpose:** The dashboard is open but the Aegis agent is not running. The user may be reviewing historical data from a previous session, or they may be checking in while the agent is between sessions. The screen should clearly communicate disconnected state without hiding the historical data.

**Layout:** Identical to Screen 1 in structure. Three changes only:

**Header status pill:** Switches from green to amber. Background `rgba(217,119,6,0.12)`, border `rgba(217,119,6,0.3)`. Dot and text in `#D97706`. Label reads "Agent Offline." A small "Reconnect" text link appears immediately to the left of the pill.

**Notification banner:** A slim full-width banner appears immediately below the header. Height 36px. Background `rgba(217,119,6,0.08)`. Border-bottom `1px solid rgba(217,119,6,0.15)`. Text: "Live feed paused — showing last session data." in 12px `#D97706`, left-aligned with 24px left padding. Right side of banner: "Last active: [timestamp]" in monospace 11px `#484F58`.

**Content area:** All stat cards and log rows render at 65% opacity. They are readable but visually communicate that this is historical data, not live. No other changes to layout.

**What this screen communicates:** The agent is not active. Here is what happened last time. Everything is accounted for, nothing is lost.

---

### Screen 3 · Red Action Detail Expanded

**Purpose:** A red-tier action has been selected from the audit log and the user wants the full incident detail. This is the most information-dense view in the dashboard — it should present everything relevant to understanding what happened, why, and what the outcome was, without requiring the user to go anywhere else.

**Layout at 1440px:** The right detail panel expands. Rather than the standard 35% width, it takes over 50% of the content area. The log table compresses to 50%. Alternatively this can be a slide-in drawer from the right edge — 520px wide, overlaying the log table partially with a backdrop `rgba(0,0,0,0.4)` on the log area.

**Expanded detail panel contents (top to bottom):**
- "INCIDENT DETAIL" label: monospace 10px, letter-spaced, `#484F58`
- 12px gap
- Tier badge: larger pill, "RED — IRREVERSIBLE ACTION" in monospace 11px, background `rgba(220,38,38,0.1)`, border `rgba(220,38,38,0.3)`, text `#DC2626`
- 16px gap
- Action description in plain English: 16px, medium weight, `#E6EDF3`, line-height 1.6
- Monospace detail (file path, size): 12px, `#7D8590`
- 24px gap
- Divider: `1px solid rgba(255,255,255,0.06)`
- 24px gap
- Section label: "CLASSIFICATION" in monospace 10px `#484F58`
- Risk Tier: value row
- Reasoning: one sentence from the agent explaining why it classified this action as red, 12px regular `#7D8590`, italic
- 20px gap
- Section label: "AUTHORIZATION CHAIN"
- Metadata rows in label-value pairs (monospace, same styling as Screen 1):
  - Requested at: timestamp
  - Auth request sent: timestamp
  - Auth device: device ID string
  - Auth method: "Face ID" or "Touch ID"
  - Response received at: timestamp
  - Outcome: "Authorized" (green text) or "Blocked" (red text) or "Timed Out — Auto Denied" (amber text)
  - Total duration: time from request to outcome in seconds
- 24px gap
- Divider
- 20px gap
- Two text links at bottom: "Export Entry" left-aligned, `#7D8590` · "Flag for Review" right-aligned, `#7D8590`

**Layout at 768px:** The expanded detail panel takes the full content width. The log table is hidden while detail is open — a "← Back to Log" text link sits at the top left of the detail panel to return. All content reflows to single column. No information is hidden.

---

## Shared Interaction Patterns

**Transitions:** Keep them short and purposeful. State changes: 200ms ease. Panel slide-ins: 250ms ease-out. Color shifts (visualizer ring tier change): 400ms ease. Nothing bounces. Nothing overshoots.

**Loading / connecting states:** Use a minimal spinner — thin stroke circle, 16px, rotating. Place it inline with the relevant label, not center-screen. The user should never stare at a full-screen loader.

**Error states:** Inline, below the relevant element. Monospace 11px, `#DC2626`. No modal dialogs for errors. The system surfaces problems without making them events.

**Empty states:** Dim centered text, monospace, `#484F58`. No illustrations. No "nothing here yet!" copy. Just a factual description of what is absent.

**Focus states (accessibility):** Outline `2px solid rgba(61,142,255,0.6)`, offset 2px. On dark backgrounds this is visible without being distracting.

---

*Document prepared for frontend developer handoff. Backend, WebSocket, and API specifications are maintained separately.*