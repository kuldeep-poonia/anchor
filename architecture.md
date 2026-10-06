# ANCHOR — System Architecture & Design

ANCHOR is designed as a lightweight, deterministic safety and control layer positioned directly between autonomous AI agents and developer operating systems.

---

## 1. High-Level Architecture

```text
                           USER / AGENT GOAL
                                   │
                                   ▼
                   ┌───────────────────────────────┐
                   │     INTENT PROVIDER LAYER     │
                   │                               │
                   │  ┌─────────────────────────┐  │
                   │  │ LocalProvider (Offline) │  │
                   │  └─────────────────────────┘  │
                   │  ┌─────────────────────────┐  │
                   │  │ NebiusProvider          │  │
                   │  │ (NVIDIA Nemotron)       │  │
                   │  └─────────────────────────┘  │
                   └───────────────┬───────────────┘
                                   │ Action Contract
                                   ▼
                   ┌───────────────────────────────┐
                   │    ANCHOR POLICY ENGINE       │
                   │                               │
                   │  • Workspace Boundary Check   │
                   │  • Canonical Path Resolution  │
                   │  • Hard Deny on Escapes       │
                   │  • Forbidden Pattern Matching │
                   │  • Command Whitelisting       │
                   └───────────────┬───────────────┘
                                   │
                                   ▼
                   ┌───────────────────────────────┐
                   │      DETERMINISTIC RISK       │
                   │                               │
                   │   LOW | MEDIUM | HIGH | CRIT  │
                   │   (Agents cannot downgrade)   │
                   └───────────────┬───────────────┘
                                   │ Decision
                        ┌──────────┴──────────┐
                        │                     │
                     [ ALLOW ]      [ REQUIRE_APPROVAL ]
                        │                     │
                        │           Pending Approval Queued
                        ▼           (Requires 'anchor approve')
                   ┌───────────────────────────────┐
                   │       SNAPSHOT MANAGER        │
                   │                               │
                   │  Point-in-Time File Backup    │
                   │  SHA-256 State Manifest       │
                   └───────────────┬───────────────┘
                                   │
                                   ▼
                   ┌───────────────────────────────┐
                   │        ACTION EXECUTOR        │
                   │                               │
                   │  • Atomic File Operations     │
                   │  • Isolated Subprocess Array  │
                   │  • Sanitized Process Env      │
                   │  • Strict Timeout Limit       │
                   └───────────────┬───────────────┘
                                   │ Output State
                                   ▼
                   ┌───────────────────────────────┐
                   │      INDEPENDENT VERIFIER     │
                   │                               │
                   │  • Objective Test Run (pytest)│
                   │  • File Integrity Validation  │
                   └───────────────┬───────────────┘
                                   │
                         ┌─────────┴─────────┐
                         ▼                   ▼
                    [ PASS ]              [ FAIL ]
                         │                   │
                  Confirmed & Logged    AUTOMATIC ROLLBACK
                  in SQLite Audit DB    (State Restored)
```

---

## 2. Core Modules & Responsibilities

| Module | Location | Responsibility |
| :--- | :--- | :--- |
| **Workspace Boundary** | `anchor.workspace.paths` | Resolves canonical paths with `pathlib.Path.resolve()`, prevents path traversal (`../`), symlink escapes, alternate data streams (`:stream`), and Windows reserved device names. |
| **Contracts** | `anchor.contracts` | Pydantic validation of declarative action boundaries (`allowed_paths`, `forbidden_paths`, `allowed_commands`, `destructive_requires_approval`). Fails closed on ambiguity. |
| **Policy Engine** | `anchor.policy.engine` | Deterministic decision engine (`ALLOW`, `DENY`, `REQUIRE_APPROVAL`). Enforces strict precedence: Forbidden rules always supersede allowed rules. |
| **Risk Engine** | `anchor.risk.engine` | Independent risk classifier (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`). Ignores agent claims and evaluates destructive nature, target sensitivity, and command characteristics. |
| **Action Executor** | `anchor.actions.executor` | Executes atomic file writes via temporary files and controlled subprocesses with output truncation and scrubbed environments (redacts `NEBIUS_API_KEY`). |
| **Snapshot Manager** | `anchor.snapshots.manager` | Captures pre-mutation checkpoints in `.anchor/snapshots/` with SHA-256 hashes. Restores modified files, deleted files, and purges newly created files during rollback. |
| **Verification Runner**| `anchor.verification.runner` | Executes objective verification tests and filesystem integrity checks completely independent of agent self-claims. |
| **Audit Database** | `anchor.storage.database` | Parameterized SQLite database (`.anchor/audit.db`) storing full action audit history, snapshot pointers, and pending approval states. |
| **AI Providers** | `anchor.providers` | Provider abstraction: `LocalProvider` for offline deterministic operation, and `NebiusProvider` for real NVIDIA Nemotron inference via Nebius Token Factory. |

---

## 3. Evaluation Precedence Rules

To eliminate policy ambiguity, ANCHOR enforces a deterministic 5-stage evaluation order:

```text
Stage 1: Hard DENY
         • Null bytes (\x00)
         • Reserved device names (CON, NUL, PRN, etc.)
         • Alternate data streams (:stream)
         • Workspace boundary escape (../../ or external symlinks)
              ↓
Stage 2: Forbidden Contract Rules
         • Default protected patterns (.env*, .git/**, .anchor/**, *.key, *.pem)
         • Contract forbidden paths
              ↓
Stage 3: Destructive & High-Risk Approval
         • File deletions with destructive_requires_approval = True
         • CRITICAL risk tier operations
              ↓
Stage 4: Allowed Contract Rules
         • Must match an explicit allowed path glob or allowed command
              ↓
Stage 5: Default DENY
         • Any action not explicitly matched fails closed
```

---

## 4. Threat Model & Security Mitigations

### 1. Path Traversal & Canonical Bypasses
- **Threat:** Agent requests `../../../../etc/shadow` or relative traversal disguised as `src/../.env`.
- **Mitigation:** ANCHOR resolves the canonical absolute path using `Path.resolve()` and strictly verifies `resolved.is_relative_to(workspace_canonical)`. Simple string prefix checking is forbidden.

### 2. Symlink Escape Vectors
- **Threat:** Agent creates a symlink inside the workspace pointing to an external directory.
- **Mitigation:** Symlinks are followed during path resolution and verified against the canonical workspace boundary. Any symlink pointing outside is rejected with `WorkspaceBoundaryError`.

### 3. Shell Chaining & Operator Injections
- **Threat:** Agent requests `pytest && rm -rf /` or `pytest $(cat /etc/passwd)`.
- **Mitigation:** Unrestricted `shell=True` execution is banned. Commands are parsed and checked for shell operators (`&&`, `;`, `|`, `` ` ``, `$()`, `>`, `<`). Subprocesses run as structured argument arrays.

### 4. Credential Leakage to Child Subprocesses
- **Threat:** A child subprocess inspects parent environment variables to steal `NEBIUS_API_KEY` or cloud tokens.
- **Mitigation:** ActionExecutor creates a sanitized environment copy, scrubbing known sensitive variables before invoking child processes.

### 5. Malicious or Hallucinating LLM Output
- **Threat:** The AI model is compromised via prompt injection and returns a contract attempting to grant full access or arbitrary execution.
- **Mitigation:** All LLM outputs are treated as untrusted data and strictly validated with Pydantic schemas. Even if the model attempts to allow all paths (`**`), ANCHOR's built-in default forbidden patterns (`.env*`, `.git/**`, `.anchor/**`) and workspace boundary checks remain non-negotiable.
