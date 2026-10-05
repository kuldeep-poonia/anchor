# ANCHOR

> Lightweight safety and deterministic control layer for AI agents.

AI agents are increasingly capable of interacting directly with developer environments: reading files, modifying codebases, executing shell commands, and managing configuration. However, foundation models can hallucinate, misunderstand goals, or propose destructive commands.

**ANCHOR** sits between the AI agent and the operating system. It enforces deterministic safety boundaries, AI-generated action contracts, risk evaluations, interactive approval thresholds, and automatic rollback checkpoints.

The core principle:
**AI can act, but AI should not act without boundaries.**

---

## Key Features

- **Dual AI Mode Architecture**:
  - **Local Mode (Default)**: Full deterministic safety, contract evaluation, and rollback verification without requiring an external AI API key or network access.
  - **NVIDIA Nemotron via Nebius Token Factory Mode**: High-accuracy contract synthesis from natural language goals using NVIDIA Nemotron when a user provides their `NEBIUS_API_KEY`.
- **Deterministic Policy Enforcement**: Strict workspace boundary verification, canonical path resolution, forbidden path protection, and command allowlisting.
- **Independent Risk Engine**: Deterministic classification (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`). Agents can never self-evaluate or downgrade their own risk.
- **Snapshot & Rollback**: Automatic point-in-time state preservation before dangerous mutations with instant restoration via `anchor undo`.
- **Independent Verification**: Action outcomes are evaluated objectively (e.g. exit codes, filesystem state, tests) rather than relying on agent claims.
- **Minimal Dependencies**: Built on Python 3.10+ with standard library primitives, Typer, and Pydantic.

---

## Architecture Flow

```text
User Goal
    ↓
Intent Provider (Local or Nebius / Nemotron)
    ↓
Action Contract (Pydantic Schema Validation)
    ↓
ANCHOR Policy Engine (Canonical Path & Boundary Checks)
    ↓
Risk Engine (Deterministic Scoring)
    ↓
Decision (ALLOW / DENY / REQUIRE_APPROVAL)
    ↓
Snapshot Manager (Pre-mutation Checkpoint)
    ↓
Action Executor (Isolated subprocess / atomic file write)
    ↓
Verification Engine (Independent validation)
    ↓
SUCCESS or automatic ROLLBACK
```

---

## Installation

### Prerequisites
- Python 3.10 or higher
- Git

### Setup
```bash
# Clone the repository
git clone https://github.com/poonia-98/anchor.git
cd anchor

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies and anchor CLI
pip install -e .
```

### Development Dependencies
```bash
pip install -e ".[dev]"
```

---

## Configuration

ANCHOR works immediately out of the box in Local Mode without any API keys.

To enable NVIDIA Nemotron contract synthesis through Nebius Token Factory:
```bash
cp .env.example .env
```
Edit `.env` or set the environment variable:
```bash
export NEBIUS_API_KEY="your-nebius-api-key"
```

---

## Quick Start & CLI Usage

### 1. Initialize Workspace Boundary
```bash
anchor init
```

### 2. Run Deterministic Demo
Demonstrates allowed actions, blocked secret access, risk elevation, and rollback:
```bash
anchor demo
```

### 3. Execute a Goal
```bash
anchor run "Refactor authentication module and run tests"
```

### 4. Check Safety Status
```bash
anchor status
```

### 5. Rollback Latest Changes
```bash
anchor undo
```

---

## Testing

ANCHOR includes unit tests, integration tests, and a dedicated adversarial attack suite (path traversal, symlink escapes, shell injection, and malformed model payloads).

```bash
# Run complete test suite
pytest

# Run linter
ruff check .
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
