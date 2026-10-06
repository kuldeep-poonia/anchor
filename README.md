# ANCHOR

> **Lightweight safety and deterministic control layer for autonomous AI agents.**

[![Tests](https://img.shields.io/badge/tests-86%20passed-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)]()
[![NVIDIA](https://img.shields.io/badge/powered%20by-NVIDIA%20Nemotron-76B900.svg)]()

> *"AI can act, but AI should not act without boundaries."*  
> *"AI agents don't need to be perfect. They need to be controllable."*

---

## What is ANCHOR?

Autonomous AI coding agents (such as Gemini, Claude, Cursor, Devin, or custom LLM bots) are increasingly given raw tool access to developer workstations: reading files, modifying codebases, executing terminal commands, and managing configuration.

**The Problem:**
1. **Accidental Credential Leaks:** An agent can read `.env`, SSH keys, or cloud secrets and inadvertently transmit them.
2. **Destructive Operations:** An agent can delete essential modules, run unconstrained recursive deletions (`rm -rf`), or modify system files outside the workspace.
3. **Hallucinated Verification:** An agent can introduce breaking syntax errors or broken logic and falsely assert that *"All tests passed!"*.
4. **No Clean Safety Net:** Standard `git restore` does not recover untracked newly generated files or uncommitted mutations.

**The Solution:**  
**ANCHOR sits between the AI agent and your Operating System as a deterministic security firewall.** The AI model is never the final security authority. The AI can propose actions, but ANCHOR's deterministic runtime enforces permissions, evaluates risk, captures pre-mutation snapshots, objectively verifies outcomes, and automatically rolls back if tests fail.

---

## How It Works

```text
User Goal
    │
    ▼
[1] Intent Provider Layer
    ├── Local Provider (Default, 100% offline, zero API keys needed)
    └── Nebius Provider (NVIDIA Nemotron inference via Nebius Token Factory)
    │
    ▼ Action Contract (Pydantic Schema Validation)
[2] ANCHOR Policy Engine
    ├── Workspace Boundary Check (Path traversal ../ & symlinks BLOCKED)
    ├── Forbidden Pattern Filter (.env, secrets/**, .git/** BLOCKED)
    └── Command Whitelist (Pipes, shell chaining &&, ; BLOCKED)
    │
    ▼ Deterministic Risk Classifier (LOW / MEDIUM / HIGH / CRITICAL)
[3] Decision Gate
    ├── ALLOW ──────────────┐
    ├── REQUIRE_APPROVAL ───┼─→ Waits for 'anchor approve <id>'
    └── DENY ───────────────┼─→ BLOCKED (0 bytes leaked)
                            │
                            ▼
[4] Pre-Mutation Snapshot (.anchor/snapshots/)
    ├── Backs up affected files prior to write/delete
    └── Records SHA-256 hashes
                            │
                            ▼
[5] Sandboxed Execution (ActionExecutor)
    ├── Atomic file writes (avoids partial file corruption)
    └── Scrubbed subprocesses (redacts API keys from child environment)
                            │
                            ▼
[6] Objective Verification (VerificationRunner)
    ├── Independent test run (pytest) & disk inspection
    ├── PASS  ──→ Action confirmed & recorded in SQLite audit log
    └── FAIL  ──→ AUTOMATIC ROLLBACK (Restores original state instantly!)
```

---

## Dual AI Architecture

ANCHOR separates intent understanding from deterministic safety enforcement:

1. **Mode A — Local / No API Key (Default)**:
   - **Zero configuration required.** Works completely offline with zero network calls and no paid subscriptions.
   - Evaluates actions and derives bounded contracts using deterministic heuristics.
   - Anyone cloning the repository can immediately run `anchor demo` without credentials.

2. **Mode B — NVIDIA Nemotron via Nebius Token Factory**:
   - Enabled seamlessly when you provide `NEBIUS_API_KEY`.
   - Utilizes **NVIDIA Nemotron** (`nvidia/llama-3.1-nemotron-70b-instruct`) hosted on Nebius Token Factory for natural language understanding and contract synthesis.
   - Even if the model produces malformed or compromised output, ANCHOR fails closed and protects system boundaries.

---

## Complete User Guide & CLI Commands

ANCHOR provides a clean, predictable CLI interface:

### 1. Initialize Workspace Safety Boundary
Run inside any project directory (or pass `-w <path>`):
```bash
anchor init
```
*Creates the local `.anchor/` directory for audit logging, snapshots, and boundary enforcement.*

### 2. Run the Deterministic Safety Demo (No API Key Required)
Experience ANCHOR's complete enforcement in 5 seconds:
```bash
anchor demo
```
**What the demo proves:**
- Synthesizes an action contract for an authentication goal.
- Executes an allowed file write and objectively verifies it on disk.
- Intercepts and **blocks** an attempt to read `.env` credentials (0 bytes leaked).
- Detects a destructive deletion and pauses for human confirmation.
- Simulates a mutation that breaks tests, triggers **automatic rollback**, and restores the exact original state.

### 3. Run an Autonomous Goal
```bash
anchor run "Refactor payment service and add tests"
```
Evaluates proposed actions against the contract, executes permitted steps, queues high-risk steps for approval, and blocks forbidden access.

### 4. Check Safety Status & Pending Approvals
```bash
anchor status
```
Displays active workspace boundary, active provider mode (Local or Nebius), pending human approvals, snapshot history, and recent audit records.

### 5. Approve or Deny High-Risk Operations
```bash
# Approve a pending destructive action:
anchor approve <action-id>

# Reject an action:
anchor deny <action-id>
```

### 6. Instant Rollback (`anchor undo`)
Revert the workspace to the latest pre-mutation checkpoint:
```bash
anchor undo
```
- **Modified files:** Restored from pre-mutation backup copies.
- **Newly created files:** Safely deleted.
- **Deleted files:** Restored from pre-mutation snapshots.
- *Note:* Does not require Git commits—works directly on the filesystem level.

---

## Using ANCHOR with IDE AI Agents (Gemini, Claude, Cursor)

When interacting with AI agents in an IDE chat window, ANCHOR acts as your safety layer in two key ways:

### 1. Developer Safety Net
While chatting with an AI agent in your IDE, the agent may modify multiple files. If the code breaks or produces unwanted side effects, simply run in your IDE terminal:
```bash
anchor undo
```
ANCHOR instantly restores your project to its clean state without having to manually sift through file diffs or uncommitted changes.

### 2. Tool Middleware for Custom Agents
If you are building an AI agent or wrapping IDE tools, route file and shell operations through ANCHOR's Python SDK instead of direct OS calls:

```python
from anchor.workspace import Workspace
from anchor.policy import PolicyEngine
from anchor.actions import Action, ActionType, ActionExecutor
from anchor.snapshots import SnapshotManager

ws = Workspace("./my-project")
snapshot_mgr = SnapshotManager(ws)
policy = PolicyEngine(ws)
executor = ActionExecutor(ws)

# Evaluate candidate agent action
action = Action(type=ActionType.WRITE_FILE, target="src/auth.py", content="...")
decision = policy.evaluate(action, contract)

if decision.decision == "ALLOW":
    snap_id = snapshot_mgr.create_snapshot(action)
    result = executor.execute(action)
```
*(See [examples/coding_agent.py](examples/coding_agent.py) for an end-to-end programmatic implementation.)*

---

## Installation & Setup

### Prerequisites
- Python 3.10, 3.11, or 3.12
- Git

### Option 1: One-Line Global Install from GitHub (Fastest)
Any user can install and use ANCHOR globally in one command:
```bash
pip install git+https://github.com/kuldeep-poonia/anchor.git

# Run directly from anywhere in your terminal:
anchor demo
```

### Option 2: Clone & Local Development Setup
```bash
# 1. Clone repository
git clone https://github.com/kuldeep-poonia/anchor.git
cd anchor

# 2. Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# 3. Install in editable mode
pip install -e .

# Run CLI:
anchor demo
```

> **Tip:** You can also run ANCHOR directly via Python module syntax without relying on PATH:
> ```bash
> python -m anchor demo
> ```

### Optional: Enable NVIDIA Nemotron Mode
```bash
# Set your Nebius Token Factory API key:
# On Windows PowerShell:
$env:NEBIUS_API_KEY="your-nebius-api-key"
# On Linux/macOS:
export NEBIUS_API_KEY="your-nebius-api-key"
```

### Docker Container Usage
A production-ready [Dockerfile](Dockerfile) is included:
```bash
docker build -t anchor .
docker run -v ${PWD}:/workspace anchor run "Build authentication service"
```

---

## Testing & Adversarial Security Suite

ANCHOR includes an aggressive security test suite designed to attempt breaking boundaries, exploiting symlinks, and evading policies:

```bash
# Run all 86 unit, integration, and security tests
pytest

# Run linter
ruff check .
```

### Test Coverage Highlights:
- **Path Traversal Attacks:** Tests `../../../../etc/shadow`, encoded traversal, and null-byte injection.
- **Symlink Escapes:** Tests symlinks created inside the workspace targeting external files.
- **Shell Injections:** Tests commands with operators (`&&`, `;`, `|`, `` ` ``, `$()`, `>`).
- **Policy & Casing Bypasses:** Tests case variations (`.ENV`, `SECRETS/`).
- **Compromised Model Resistance:** Tests scenarios where the LLM deliberately attempts to bypass boundaries or grant unauthorized access.
- **Fault Injection & Chaos:** Tests atomic write crash resistance and corrupt manifest handling.

---

## Architecture Documentation

For in-depth details on component contracts, evaluation precedence, and threat modeling, refer to [architecture.md](architecture.md).

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
