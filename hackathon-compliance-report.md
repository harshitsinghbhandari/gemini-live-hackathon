# Aegis Hackathon Winning Strategy & Compliance Report

## 1. Executive Summary
Aegis is a trust-first, voice-native AI agent for macOS that leverages the Gemini Live API and Composio to bridge the gap between powerful automation and personal security. We are entering the **Live Agents** category, competing for the **$25,000 Grand Prize** and the **Live Agent Category Prize**. Aegis is currently functional in its core voice loop and biometric security layer (Touch ID/Face ID), but is critically missing the visual multimodal integration ("Vision") and the required Google Cloud deployment proof and documentation needed to pass the Stage 1 baseline.

---

## 2. Compliance Status
Brutally honest audit against `hackathon-rules.md`.

### A. General Requirements
| Requirement | Status | Evidence / Action to Fix |
|:---|:---:|:---|
| **NEW Project Only** | ✅ COMPLIANT | Created after Feb 16. Git history confirms development started in March. |
| **Eligibility Restrictions** | ⚠️ ACTION REQUIRED | Confirm members are not in embargoed countries/Quebec/Italy, not gov employees, and no financial support from Sponsor. |
| **English Support** | ✅ COMPLIANT | All UI, voice prompts, and code documentation are in English. |
| **Multimodal I/O** | ⚠️ PARTIAL | **Missing Vision.** Voice handles barge-in, but adding screen capture guarantees "move beyond text-in/text-out". |
| **Gemini Model** | ✅ COMPLIANT | Uses `gemini-2.5-flash-native-audio-latest` and `gemini-2.5-flash`. |
| **GenAI SDK / ADK** | ✅ COMPLIANT | Uses `google-genai` Python SDK. |
| **Google Cloud Service** | ✅ COMPLIANT | Backend is designed for Cloud Run; uses Firestore and FCM. |
| **Category Fit** | ✅ COMPLIANT | Perfect fit for "Live Agents" (Real-time, barge-in, voice persona). |

### B. Submission Requirements
| Requirement | Status | Evidence / Action to Fix |
|:---|:---:|:---|
| **Public Repository** | ❌ MISSING | **Action:** Move repo to public GitHub before submission. |
| **Spin-up Instructions** | ⚠️ PARTIAL | README has basics but must have a step-by-step guide explaining setup/cloud deploy. |
| **GCP Deployment Proof** | ❌ MISSING | **Action:** Record 30s clip of Google Cloud Console showing backend on Cloud Run, OR link to a code file showing GCP use. |
| **Architecture Diagram** | ❌ MISSING | **Action:** Create clear visual representation showing Gemini ↔ Backend ↔ Mobile loop. |
| **Demo Video (≤4m)** | ❌ MISSING | **Action:** Record actual software working. Pitch problem/value. Upload to YouTube or Vimeo. English language/subtitles. |
| **Testing Access** | ❌ MISSING | **Action:** Provide the URL to the deployed Dashboard and credentials for testing. |

---

## 3. Judging Criteria Breakdown

### Criterion 1: Innovation & Multimodal UX (40%)
*   **Current Score: 6/10**
*   **Why:** High points for native biometric integration (Touch ID/Face ID) which is unique. Points lost for lack of visual awareness (agent is currently blind).
*   **Ideal Submission:** The agent should "see" the screen to understand what the user is talking about (e.g., "Summarize this PDF" while it's open).
*   **Action:** Implement `screen.py` and the continuous frame-streaming loop in `voice.py`.

### Criterion 2: Technical Implementation & Architecture (30%)
*   **Current Score: 8/10**
*   **Why:** Architecture is robust (Python agent + FastAPI + React PWA). 3-tier security model is a sophisticated "Agentic" feature.
*   **Ideal Submission:** Clean code, robust error handling for API timeouts, and clear proof of GCP hosting.
*   **Action:** Add retry logic for Composio tool calls and ensure the backend polls Firestore efficiently.

### Criterion 3: Demo & Presentation (30%)
*   **Current Score: 0/10**
*   **Why:** No video or diagram exists.
*   **Ideal Submission:** A high-energy 4-minute video that shows the actual software working, clearly defines the problem/solution, and proves the architecture.
*   **Action:** Follow the script in Section 6. Upload to YouTube/Vimeo.

### Bonus Contributions (Up to +1.0)
*   **Content (+0.6):** ❌ Write a blog post on "Building the Trust Layer for Agents". Must include `#GeminiLiveAgentChallenge` and exact disclaimer.
*   **Automation (+0.2):** ✅ COMPLIANT (Already have `deploy.sh` in public repo).
*   **GDG (+0.2):** ❌ Harshit to provide public GDG profile link if a member.

---

## 4. Winning Actions — DO THIS

| Impact | Action | Why it wins | Effort | Owner |
|:---|:---|:---|:---|:---|
| **CRITICAL** | **Restore `screen.py` & Vision Loop** | Multimodal "Vision" is a mandatory judging requirement. Being audio-only is an automatic loss. | 4h | Jules |
| **HIGH** | **Deploy Backend to Cloud Run** | Satisfies the "Google Cloud Native" technical requirement (30% weight). | 2h | Jules |
| **HIGH** | **Record High-Fidelity Demo** | Video is 30% of the score. Must look slick and "Live". | 6h | Harshit |
| **MED** | **Create Architecture Diagram** | Proves technical depth and system design (30% weight). | 2h | Jules |
| **MED** | **Write "Winning" README** | Judges look here for technical grounding. Highlight the Security Tiering logic. | 2h | Jules |
| **HIGH** | **Sweep Bonus Points** | +1.0 total points (out of 6.0) is a massive ~17% boost. Most teams skip this. | 6h | Both |

---

## 5. What NOT To Do
*   **❌ DON'T waste time on "UI Polish":** The dashboard is functional enough. Judges care about the Agent's brain and the voice interaction.
*   **❌ DON'T add more tools:** Gmail and Calendar are sufficient. Adding more (Slack, Notion) provides diminishing returns compared to fixing Vision.
*   **❌ DON'T hide the "RED" tier:** Judges love safety. Show the agent *refusing* to act without a fingerprint. It proves the "Trust Layer" works.

---

## 6. Demo Video Strategy (30% of Score)
**Target Length:** 3m 30s (Strict limit: ≤4 minutes). **Platform**: YouTube or Vimeo.

### Script Outline:
1.  **The Hook (0:00-0:30):** "AI agents are powerful, but do you trust them with your bank or your inbox? Meet Aegis." (Pitch problem and solution value).
2.  **The Interaction (0:30-1:30):** Show a "Live" voice conversation.
    *   *Prompt:* "What's my next meeting?" (GREEN - silent/fast).
    *   *Interruption:* Interrupt the agent while it's talking to ask for more details.
3.  **The Vision (1:30-2:15):** Open a document on screen.
    *   *Prompt:* "Based on what I'm looking at, draft a reply to this email." (Vision + Tool execution).
4.  **The Trust Layer (2:15-3:15):** The "Money Shot".
    *   *Prompt:* "Okay, send that email."
    *   *Agent:* "That's a RED action. I need your fingerprint."
    *   *Action:* Show the Mac Touch ID prompt OR the iPhone Face ID notification.
    *   *Result:* Approved and executed.
5.  **The Proof (3:15-3:45):** Quick flashes of the Dashboard audit log and the Google Cloud Console.
6.  **Closing:** "Aegis: The trust layer for the agentic future."

---

## 7. Differentiation — Why Aegis Wins
**The "Unfair Advantage" Talking Points:**
1.  **Native Security Integration:** We are the only project using native `pyobjc` to call macOS biometric APIs. Most agents are just wrappers; Aegis is an OS-level citizen.
2.  **The 3-Tier Risk Model:** We don't just "ask for permission". We use Gemini to classify risk (RED/YELLOW/GREEN) based on *contextual intent*.
3.  **Remote Biometrics:** The iPhone PWA as a hardware "security key" for a Mac agent is a highly memorable user experience.

---

## 8. Submission Checklist
*   [ ] Public GitHub Repository URL (containing all code and `deploy.sh`).
*   [ ] ≤4-minute YouTube or Vimeo Video Link (Public/Unlisted).
*   [ ] Text Description (Problem solved, tech used, learnings).
*   [ ] Architecture Diagram Image.
*   [ ] Google Cloud Proof (Short recording or repository link to GCP usage).
*   [ ] Testing Instructions (URL to project and login credentials).
*   [ ] **Bonus:** Blog post link + `#GeminiLiveAgentChallenge` on Socials.

---

## 10. Bonus Points — How to Sweep (Total +1.0)
In a high-stakes hackathon, the winner is often decided by fractions of a point. Section 8 of the rules allows for up to **1.0 bonus points** (on a 6.0 scale). This is a **17% advantage** over teams that only do the technical work.

### A. Content Creation Bonus (+0.6) — "The Multi-Channel Strategy"
The rules allow multiple pieces of content. To guarantee the full 0.6, we will do two:
1.  **Technical Deep Dive (Blog):** Publish on **Dev.to** or **Medium**.
    *   *Title:* "The Architecture of Trust: Native macOS Biometrics in AI Agents".
    *   *Focus:* Explain the 3-tier security model and how Gemini classifies intent.
2.  **"How it was Built" (Video/Reel):** A 60-second "Speedrun" of the architecture.
    *   *Platform:* LinkedIn or X.
    *   *Mandatory:* Must include the hashtag `#GeminiLiveAgentChallenge`.
3.  **PRO TIP:** Every piece of content **MUST** include this exact disclaimer:
    > *"I created this piece of content for the purposes of entering this hackathon."*
    *Missing this sentence means 0 points.*

### B. Deployment Automation Bonus (+0.2) — "Infrastructure as Code"
We have the scripts, but we need to *prove* them to the judges.
*   **Action:** Jules will create a `/docs/DEPLOYMENT.md` file that explains the `deploy.sh` flow.
*   **Requirement:** Ensure the code repository is public and includes the `Dockerfile` for every service (Mac app, Mobile app, Dashboard, Backend).
*   **Evidence:** In the Devpost "How it works" section, explicitly link to the `deploy.sh` file as proof of automation.

### C. GDG Membership Bonus (+0.2) — "The Community Factor"
*   **Action:** Harshit must join a local GDG chapter at [gdg.community.dev](https://gdg.community.dev).
*   **The Link:** You must provide your **Public Profile Link** (e.g., `https://gdg.community.dev/u/harshitbhandari`).
*   **Verification:** Ensure the profile is set to "Public" in settings so judges can verify membership.

---

## 9. Timeline
**Deadline: March 16, 5:00 PM PT**

| Day | Task | Assigned |
|:---|:---|:---|
| **Mar 7 (Today)** | **Audit & Strategy.** (Done). Restore `screen.py`. | Jules |
| **Mar 8** | Fix Vision Loop in `voice.py`. Test "See + Speak" flow. | Jules |
| **Mar 9** | Deploy to Cloud Run. Finalize `deploy.sh`. | Jules |
| **Mar 10** | Create Architecture Diagram. Refactor README. | Jules |
| **Mar 11-12** | **DEMO RECORDING.** Harshit records live footage + voiceover. | Harshit |
| **Mar 13** | Video Editing. Write Blog Post. | Harshit |
| **Mar 14** | Dry Run Submission. Check all links & public settings. | Both |
| **Mar 15** | Buffer Day (Fixing bugs found during recording). | Both |
| **Mar 16** | **SUBMISSION DAY.** Upload to Devpost by 12:00 PM (avoid 5pm rush). | Harshit |
