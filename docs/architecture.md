# ANCHOR — System Architecture

ANCHOR is a lightweight safety and deterministic control layer for autonomous AI agents. It intercepts candidate agent actions, applies declarative action contracts, deterministically computes risk scores, checks strict containment boundaries, creates pre-mutation checkpoints, and objectively verifies execution outcomes.

---

## 1. Core Architecture Diagram

```text
User Goal
    │
    ▼
┌──────────────────────────────────────────────┐
│ Intent Provider Layer                        │
│ ┌──────────────────────┐ ┌─────────────────┐ │
│ │ LocalProvider        │ │ NebiusProvider  │ │
│ │ (No API Key Required)│ │ (NVIDIA Nemotron│ │
│ └──────────────────────┘ └─────────────────┘ │
└──────────────────────┬───────────────────────┘
                       │ Action Contract
                       ▼
┌──────────────────────────────────────────────┐
│ ANCHOR Policy Engine                         │
│ - Strict Workspace Boundary Resolution       │
│ - Hard Deny for Traversal & Symlink Escapes  │
│ - Forbidden Rule Precedence                  │
│ - Allowed Path & Command Filtering           │
└──────────────────────┬───────────────────────┘
                       │ Risk Scoring (Deterministic)
                       ▼
┌──────────────────────────────────────────────┐
│ Deterministic Risk Engine                    │
│ - Categorizes: LOW, MEDIUM, HIGH, CRITICAL   │
│ - Autonomous agents cannot self-downgrade    │
└──────────────────────┬───────────────────────┘
                       │ Decision: ALLOW / DENY / REQUIRE_APPROVAL
                       ▼
┌──────────────────────────────────────────────┐
│ Checkpoint & Execution Layer                 │
│ - Pre-mutation Snapshot Generation           │
│ - Controlled Subprocess & Atomic File Writes │
│ - Sensitive Environment Variable Scrubbing   │
└──────────────────────┬───────────────────────┘
                       │ Output
                       ▼
┌──────────────────────────────────────────────┐
│ Independent Verification Engine              │
│ - Objective Filesystem & Exit Code Checks    │
│ - Automatic Rollback on Verification Failure │
└──────────────────────────────────────────────┘
```

---

## 2. Component Responsibilities

| Component | Module | Responsibility |
| :--- | :--- | :--- |
| **Workspace** | `anchor.workspace.paths` | Resolves canonical paths, enforces directory boundaries, and blocks symlink/traversal escapes. |
| **Contract Engine** | `anchor.contracts` | Parses declarative boundaries, glob patterns, and fail-closed rules. |
| **Policy Engine** | `anchor.policy.engine` | Evaluates action requests against contracts and boundary rules using explicit precedence. |
| **Risk Engine** | `anchor.risk.engine` | Computes objective risk tiers without relying on untrusted agent claims. |
| **Action Executor** | `anchor.actions.executor` | Performs atomic file writes and isolated subprocess execution with timeouts and output limits. |
| **Snapshot Manager**| `anchor.snapshots.manager` | Captures point-in-time file states and provides atomic restoration via `anchor undo`. |
| **Verifier** | `anchor.verification.runner`| Verifies file states and test suite outcomes independently of agent assertions. |
| **Audit Database** | `anchor.storage.database` | SQLite persistence for action histories, pending approvals, and verified outcomes. |
| **AI Providers** | `anchor.providers` | Dual-mode intent parsing: Local deterministic provider or NVIDIA Nemotron via Nebius. |

---

## 3. Dual AI Mode Architecture

ANCHOR separates intent understanding from safety enforcement:

1. **Local Mode (Default)**:
   - Does not require any API keys, credentials, or network calls.
   - Derives structured contracts using deterministic heuristics.
   - Allows instant offline testing, evaluation, and demonstration.

2. **Nebius Token Factory Mode**:
   - Enabled when `NEBIUS_API_KEY` is exported.
   - Uses NVIDIA Nemotron (`nvidia/llama-3.1-nemotron-70b-instruct`) for natural language understanding and contract synthesis.
   - Strict Pydantic validation ensures model hallucinations or prompt injections are rejected before reaching system boundaries.
