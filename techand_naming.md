# ANCHOR — Tech Stack, Project Structure & Naming Standards

## 1. Technology Philosophy

ANCHOR is a lightweight developer tool.

The technology stack must remain:

- Simple
- Stable
- Easy to understand
- Easy to install
- Easy to test
- Local-first
- Minimal in dependencies
- Easy for another developer to contribute to

Do not add a framework or dependency unless it solves a real problem in the project.

Do not use technology merely because it is popular.

The project should feel like a carefully designed developer tool, not a collection of libraries.

---

# 2. Primary Technology Stack

## Programming Language

### Python 3.12+

Use Python as the primary implementation language.

Reasons:

- Fast development
- Excellent filesystem/process support
- Strong testing ecosystem
- Easy CLI development
- Easy API integration
- Easy integration with Nebius/Nemotron

Do not introduce another programming language for the core implementation.

---

# 3. CLI

### Typer

Use **Typer** for the command-line interface.

The CLI should be the primary interface to ANCHOR.

Example:

```bash
anchor init
anchor demo
anchor run
anchor status
anchor approve
anchor deny
anchor undo
```

Keep CLI commands short and predictable.

Do not create unnecessarily complicated command hierarchies.

---

# 4. Data Validation

### Pydantic

Use **Pydantic** for structured data validation.

Use it for:

- Action requests
- Contracts
- Configuration
- Provider responses
- Risk information
- Verification results

Never trust raw JSON from an AI provider.

The flow should be:

```text
AI response
    ↓
Pydantic validation
    ↓
Policy validation
    ↓
ANCHOR decision
```

---

# 5. AI Provider

### Nebius Token Factory / NVIDIA Nemotron

Use NVIDIA Nemotron through Nebius Token Factory for the real AI integration.

Nemotron's role should remain focused:

```text
Natural language goal
        ↓
Intent understanding
        ↓
Structured contract proposal
```

Nemotron should NOT directly execute commands.

The ANCHOR runtime remains responsible for enforcement.

---

# 6. AI Provider Architecture

Use a provider interface.

```text
IntentProvider
├── LocalProvider
└── NebiusProvider
```

### LocalProvider

Used when no API key exists.

Purpose:

- Offline development
- Tests
- Demo mode
- Judges without credentials
- Users who do not want external AI services

### NebiusProvider

Used when the user provides:

```text
NEBIUS_API_KEY
```

Purpose:

- Real Nemotron inference
- Hackathon demonstration
- Real-world usage

The core system must not care which provider is being used.

---

# 7. Configuration

Use environment variables for secrets.

Primary variable:

```text
NEBIUS_API_KEY
```

Never store secrets in:

- Source code
- YAML contracts
- JSON configuration
- README
- Git history
- Test fixtures

Provide:

```text
.env.example
```

with placeholder values only.

---

# 8. Policy Engine

The policy engine should use normal Python.

Do not introduce a policy framework unless the project genuinely requires one.

Responsibilities:

- Evaluate actions.
- Check workspace boundaries.
- Check allowed paths.
- Check forbidden paths.
- Check allowed commands.
- Require approval for dangerous operations.
- Default to safe behavior when uncertain.

Possible decisions:

```text
ALLOW
DENY
REQUIRE_APPROVAL
```

---

# 9. Risk Engine

Use deterministic Python logic.

Do not use an LLM to calculate the final risk score.

The risk engine should consider:

- Action type
- Target
- Destructive behavior
- Sensitive paths
- Scope
- Reversibility
- Command characteristics

Example categories:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

The agent must never be able to provide or modify its own final risk score.

---

# 10. Filesystem

Use Python's standard library wherever possible.

Primary tools:

```text
pathlib
os
shutil
hashlib
tempfile
```

Use `pathlib` for path handling instead of manually manipulating strings.

Never use string prefix checks as the primary workspace security mechanism.

---

# 11. Command Execution

Use Python's:

```text
subprocess
```

Prefer argument lists:

```python
subprocess.run(
    ["pytest", "-q"],
    ...
)
```

Avoid unrestricted:

```python
shell=True
```

for untrusted agent input.

Command execution should have:

- Timeout
- Controlled working directory
- Controlled environment
- Output limits where appropriate
- Exit-code handling
- Process cleanup

---

# 12. Snapshot & Rollback

### Initial implementation

Use Git/checkpoints where practical.

Git provides:

- File history
- Diffs
- Restore capability
- Familiar developer workflow

For files not tracked by Git, use a small ANCHOR snapshot mechanism.

Do not introduce a large backup system.

Possible structure:

```text
.anchor/
└── snapshots/
    └── <snapshot-id>/
        ├── manifest.json
        └── files/
```

The `.anchor/` directory must never be treated as user application data.

---

# 13. Database

### SQLite

Use SQLite for lightweight local metadata.

No external database should be required.

Store only useful metadata such as:

```text
action_id
timestamp
action
decision
risk
result
snapshot_id
```

Do not store secrets.

Do not use PostgreSQL, MySQL, Redis, MongoDB, or a vector database.

They are unnecessary for the project.

---

# 14. Testing

### pytest

Use **pytest**.

Testing should include:

```text
Unit tests
Integration tests
Adversarial tests
Rollback tests
Provider tests
CLI tests
```

The adversarial test suite is especially important.

Tests should attempt to:

- Escape workspace.
- Bypass policy.
- Execute forbidden commands.
- Exploit symlinks.
- Break rollback.
- Corrupt state.
- Abuse malformed AI output.
- Exhaust resources.
- Cause process failures.

---

# 15. Code Quality

Recommended development tools:

### Ruff

Use Ruff for:

- Formatting
- Linting
- Basic code quality

### MyPy

Use MyPy where practical for static type checking.

Do not introduce a complicated type-checking configuration unnecessarily.

---

# 16. API Layer

### FastAPI — Optional

FastAPI should NOT be required for the core project.

Add it only after the CLI and core runtime are stable.

Potential API:

```text
POST /actions
POST /contracts
POST /approve
POST /deny
POST /rollback
GET  /status
```

The API must call the same ANCHOR core used by the CLI.

Do not duplicate business logic inside API routes.

Correct architecture:

```text
CLI ───────┐
           │
API ───────┼──→ ANCHOR Core
           │
Python SDK ┘
```

---

# 17. Web UI

A large frontend is not required.

The primary interface should remain the CLI.

If a visual demo is useful, create a very small interface only after the core system is complete.

Do not introduce:

- Next.js
- React
- Redux
- Tailwind
- Large frontend frameworks

unless there is a strong reason.

A simple HTML/JavaScript demonstration is sufficient.

The hackathon should be won by the product idea and engineering, not frontend complexity.

---

# 18. HTTP Client

Use a small, reliable HTTP client for the Nebius provider.

Prefer:

```text
httpx
```

Do not introduce multiple HTTP libraries.

Keep all provider-specific network code inside:

```text
providers/nebius.py
```

The rest of ANCHOR should not know how the API works.

---

# 19. Dependency Philosophy

Keep runtime dependencies minimal.

Expected core dependencies:

```text
typer
pydantic
httpx
```

Development dependencies:

```text
pytest
ruff
mypy
```

FastAPI can remain optional.

Do not add libraries for functionality already provided by Python's standard library.

---

# 20. Recommended Project Structure

Use a structure that a normal developer can understand immediately.

```text
anchor/
│
├── src/
│   └── anchor/
│       ├── __init__.py
│       ├── cli.py
│       │
│       ├── actions/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   └── executor.py
│       │
│       ├── contracts/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   └── parser.py
│       │
│       ├── policy/
│       │   ├── __init__.py
│       │   └── engine.py
│       │
│       ├── risk/
│       │   ├── __init__.py
│       │   └── engine.py
│       │
│       ├── snapshots/
│       │   ├── __init__.py
│       │   └── manager.py
│       │
│       ├── verification/
│       │   ├── __init__.py
│       │   └── runner.py
│       │
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── local.py
│       │   └── nebius.py
│       │
│       ├── storage/
│       │   ├── __init__.py
│       │   └── database.py
│       │
│       └── workspace/
│           ├── __init__.py
│           └── paths.py
│
├── tests/
│   ├── unit/
│   │   ├── test_policy.py
│   │   ├── test_risk.py
│   │   ├── test_contracts.py
│   │   └── test_paths.py
│   │
│   ├── integration/
│   │   ├── test_actions.py
│   │   ├── test_rollback.py
│   │   └── test_verification.py
│   │
│   └── security/
│       ├── test_path_escape.py
│       ├── test_command_escape.py
│       ├── test_policy_bypass.py
│       ├── test_symlink_escape.py
│       └── test_malicious_ai_output.py
│
├── examples/
│   └── coding_agent.py
│
├── docs/
│   ├── architecture.md
│   └── security.md
│
├── .github/
│   └── workflows/
│       └── tests.yml
│
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
├── pyproject.toml
└── Dockerfile
```

This structure should remain flexible.

Do not create a folder unless it contains meaningful code.

If a package contains only one tiny function and does not benefit from a package boundary, keep the implementation simpler.

---

# 21. Naming Rules

Names must be human-readable.

A developer should be able to understand a filename without opening it.

### Good

```text
policy.py
risk.py
executor.py
snapshot.py
database.py
nebius.py
local.py
paths.py
verification.py
```

### Bad

```text
core_engine_v2.py
advanced_policy_processor.py
unified_action_orchestrator.py
intelligent_safety_manager.py
ai_execution_abstraction_layer.py
phase_three_security_module.py
```

Avoid names that sound like generated enterprise architecture.

---

# 22. Class Naming

Use normal Python class names.

Good:

```text
Action
ActionRequest
Contract
PolicyEngine
RiskEngine
SnapshotManager
VerificationResult
LocalProvider
NebiusProvider
Workspace
```

Avoid:

```text
EnterpriseActionOrchestrationManager
UniversalSafetyDecisionCoordinator
AdvancedIntelligentExecutionController
```

Classes should describe what they actually do.

---

# 23. Function Naming

Use clear verbs.

Good:

```text
validate_action()
check_policy()
calculate_risk()
create_snapshot()
restore_snapshot()
run_command()
verify_result()
load_contract()
generate_contract()
```

Avoid:

```text
process_data()
handle_logic()
execute_core()
perform_operation()
manage_system()
```

unless the function genuinely has that broad responsibility.

---

# 24. Test Naming

Tests should explain the behavior being tested.

Good:

```text
test_blocks_path_outside_workspace()
test_denies_forbidden_file()
test_requires_approval_for_delete()
test_rolls_back_failed_write()
test_rejects_malformed_contract()
test_rejects_malicious_provider_output()
```

Avoid:

```text
test_phase1()
test_security()
test_final()
test_edge_case()
test_stuff()
```

---

# 25. Documentation Naming

Use simple names:

```text
README.md
architecture.md
security.md
```

Avoid:

```text
MASTER_ARCHITECTURE_DOCUMENT.md
ENTERPRISE_SECURITY_FRAMEWORK.md
COMPLETE_IMPLEMENTATION_GUIDE.md
```

Documentation should describe the project, not inflate it.

---

# 26. Git Naming

Branch names should be simple and human.

Examples:

```text
main
feature/contracts
feature/rollback
fix/path-validation
fix/command-execution
```

Avoid:

```text
phase-7-enterprise-security-hardening
ultimate-production-readiness
advanced-ai-agent-orchestration-v2
```

---

# 27. File Responsibility

Every file should have one obvious reason to exist.

For example:

```text
policy/engine.py
```

should contain policy evaluation.

It should not also contain:

- CLI formatting
- Database queries
- HTTP requests
- LLM calls
- Snapshot handling

Similarly:

```text
providers/nebius.py
```

should contain Nebius-specific provider logic.

It should not contain policy decisions.

---

# 28. Architecture Boundary

Keep these responsibilities separate:

```text
Provider
    ↓
understands intent

Contract
    ↓
describes permissions

Policy
    ↓
decides whether an action is allowed

Risk
    ↓
calculates danger

Executor
    ↓
performs action

Verifier
    ↓
checks result

Snapshot
    ↓
restores previous state

Storage
    ↓
records metadata
```

Do not mix these responsibilities.

---

# 29. Final Stack

The intended stack is:

```text
Language:
Python 3.12+

CLI:
Typer

Validation:
Pydantic

AI:
NVIDIA Nemotron via Nebius Token Factory

HTTP:
HTTPX

Filesystem:
Python standard library

Command execution:
subprocess

Snapshots:
Git + lightweight local snapshots

Database:
SQLite

Testing:
pytest

Linting/formatting:
Ruff

Type checking:
MyPy

Optional API:
FastAPI

Packaging:
pyproject.toml + uv

Container:
Docker

Repository:
GitHub

License:
MIT or Apache-2.0
```

---

# 30. Final Rule

Do not judge the quality of the project by the number of technologies used.

A strong ANCHOR implementation should be understandable by one developer sitting down with the repository for the first time.

The ideal reaction should be:

> "I can understand this architecture in a few minutes."

Not:

> "Why are there 40 folders and 25 frameworks?"

Keep ANCHOR **small, boring where it should be boring, and extremely reliable where safety matters.**