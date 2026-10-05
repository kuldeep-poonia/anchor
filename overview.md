# ANCHOR — Project Specification

## 1. What is ANCHOR?

ANCHOR is a lightweight safety and control layer for AI agents.

AI agents are increasingly capable of taking real actions such as:

- Reading files
- Creating and modifying files
- Running commands
- Installing packages
- Changing configuration
- Deleting files
- Executing workflows

The problem is that an AI model can make mistakes.

ANCHOR sits between the AI agent and the system and controls those actions.

The core principle is:

> **AI can act, but AI should not act without boundaries.**

ANCHOR provides:

- AI-generated action contracts
- Deterministic policy enforcement
- Risk evaluation
- Permission control
- Action execution
- Verification
- Checkpoints/snapshots
- Rollback

The AI model is not the final authority.

The model can propose what should be allowed, but the deterministic ANCHOR runtime decides what can actually happen.

---

# 2. How ANCHOR Works

The basic flow is:

```text
User Goal
    ↓
AI / Intent Understanding
    ↓
Action Contract
    ↓
ANCHOR Policy Engine
    ↓
Risk Evaluation
    ↓
ALLOW / DENY / APPROVAL
    ↓
Snapshot if required
    ↓
Execute Action
    ↓
Verify Result
    ↓
SUCCESS
   or
ROLLBACK
```

Example:

```text
User:

"Refactor the authentication module and add tests."

        ↓

ANCHOR creates a contract:

Allowed:
- src/auth/**
- tests/**
- pytest

Forbidden:
- .env
- secrets/**
- deployment/**

Destructive operations:
- require approval

        ↓

AI agent requests:

modify src/auth/login.py

        ↓

ANCHOR checks:

Contract: allowed
Risk: low

        ↓

EXECUTE

        ↓

Run tests

        ↓

PASS
```

If an agent attempts:

```text
read .env
```

ANCHOR should reject it if `.env` is outside the permitted contract.

If an agent performs a permitted but dangerous operation:

```text
delete src/auth/
```

ANCHOR can require explicit approval and create a rollback point before execution.

---

# 3. Core Architecture

ANCHOR should remain lightweight.

```text
                    AI AGENT
                       │
                       │ action request
                       ▼
              ┌─────────────────┐
              │     ANCHOR      │
              │                 │
              │ Contract Engine │
              │ Policy Engine   │
              │ Risk Engine     │
              │ Snapshot Manager│
              │ Executor        │
              │ Verifier        │
              └────────┬────────┘
                       │
                ┌──────┼──────┐
                ▼      ▼      ▼
             Files   Shell   Tools
                │      │      │
                └──────┼──────┘
                       ▼
                    System
```

The core runtime must not depend on an external AI API.

This is an important design requirement.

---

# 4. Dual AI Architecture

ANCHOR must support two modes.

## Mode A — Local / No API Key

ANCHOR must work without any API key.

This mode is intended for:

- Local development
- Testing
- Offline usage
- Judges who do not provide an API key
- Users who do not want to use an external AI service

The core ANCHOR functionality must continue to work:

```text
Local Intent/Contract Provider
        ↓
Contract
        ↓
Policy Engine
        ↓
Risk Engine
        ↓
Execution
        ↓
Verification
        ↓
Rollback
```

The local provider can use deterministic/demo contract generation where AI inference is not available.

Do not make the project unusable simply because an API key is missing.

The user must be able to run a complete demonstration without an API key.

Example:

```bash
anchor demo
```

should work without credentials.

---

# 5. Mode B — User-Provided Nebius / Nemotron API

ANCHOR must also support real NVIDIA Nemotron inference through Nebius Token Factory.

Users should be able to provide their own API key.

Example:

```bash
export NEBIUS_API_KEY="your-api-key"
```

Then:

```bash
anchor run
```

ANCHOR should automatically use the configured Nebius provider.

The architecture should look like:

```text
                    ANCHOR
                       │
                 AI Provider
                       │
             ┌─────────┴─────────┐
             │                   │
       Local Provider       Nebius Provider
             │                   │
        No API Key          User API Key
             │                   │
             │              Nemotron
             │                   │
             └─────────┬─────────┘
                       ▼
                 Contract Engine
                       ↓
                 Policy Engine
                       ↓
                  Risk Engine
                       ↓
                    Execute
                       ↓
                   Verify
                       ↓
                   Rollback
```

The user must never be required to modify source code to change the provider.

Provider selection should happen through configuration or environment variables.

---

# 6. Provider Abstraction

The AI layer must be abstracted.

For example:

```text
IntentProvider
    │
    ├── LocalProvider
    │
    └── NebiusProvider
```

The core ANCHOR engine must depend on the provider interface, not directly on the Nebius API.

Conceptually:

```python
class IntentProvider:
    def generate_contract(self, goal):
        ...
```

Then:

```text
LocalProvider
NebiusProvider
```

can implement the same interface.

This allows ANCHOR to operate without external AI services while still supporting real Nemotron inference.

---

# 7. API Key Handling

Never hardcode an API key.

Never commit an API key to GitHub.

Never place a real key inside the repository.

Use environment variables:

```text
NEBIUS_API_KEY
```

Provide:

```text
.env.example
```

with only a placeholder:

```text
NEBIUS_API_KEY=
```

The `.env` file itself must be ignored by Git.

---

# 8. What Nemotron Should Do

Nemotron should have a focused role.

It should help convert natural-language goals into structured intent/contracts.

Example:

```text
User:

"Refactor the authentication module and add tests."

        ↓

Nemotron

        ↓

Structured contract
```

Example output:

```json
{
  "goal": "refactor authentication",
  "allowed_paths": [
    "src/auth/**",
    "tests/**"
  ],
  "allowed_commands": [
    "pytest"
  ],
  "forbidden_paths": [
    ".env",
    "secrets/**",
    "deployment/**"
  ],
  "destructive_requires_approval": true
}
```

The output must be validated before being used.

Nemotron must NOT directly execute system actions.

---

# 9. Deterministic Safety Boundary

This is one of the most important principles of ANCHOR.

The LLM is not trusted as the final security authority.

The architecture must be:

```text
Nemotron
   ↓
Proposal
   ↓
Validation
   ↓
ANCHOR Policy Engine
   ↓
Decision
```

Never:

```text
Nemotron
   ↓
direct shell execution
```

ANCHOR's deterministic code must enforce:

- Allowed paths
- Forbidden paths
- Allowed commands
- Destructive operations
- Approval requirements
- Risk thresholds
- Execution boundaries
- Verification
- Rollback

This allows ANCHOR to remain useful even when an AI model makes a mistake.

---

# 10. Example Action Flow

Agent requests:

```text
modify src/auth/login.py
```

ANCHOR:

```text
Contract:
ALLOWED

Risk:
LOW

Decision:
ALLOW
```

Execute.

Then verify.

---

Agent requests:

```text
read .env
```

ANCHOR:

```text
Contract:
FORBIDDEN

Risk:
CRITICAL

Decision:
DENY
```

No execution occurs.

---

Agent requests:

```text
delete src/auth/
```

ANCHOR:

```text
Contract:
ALLOWED

Risk:
CRITICAL

Rollback:
AVAILABLE

Decision:
APPROVAL REQUIRED
```

After user approval:

```text
Snapshot
   ↓
Execute
   ↓
Verify
```

If verification fails:

```text
ROLLBACK
```

---

# 11. Rollback

Rollback is a core feature, not an optional visual feature.

Before risky modifications, ANCHOR should preserve the affected state.

The implementation should remain lightweight.

Initially, use Git/checkpoints and a small custom snapshot mechanism where necessary.

ANCHOR should track:

```text
snapshot_id
affected files
previous state
action
timestamp
verification result
```

The user should be able to run:

```bash
anchor undo
```

and restore the previous state when a rollback point exists.

---

# 12. Demo Mode

ANCHOR must have a deterministic demo mode.

Example:

```bash
anchor demo
```

This must require:

- No API key
- No paid service
- No cloud account
- No external database

The demo should show:

```text
Allowed action
      ↓
Blocked secret access
      ↓
Dangerous action
      ↓
Approval
      ↓
Execution
      ↓
Failure
      ↓
Rollback
```

This ensures that anyone cloning the repository can understand and test the project immediately.

---

# 13. Real AI Mode

When a user provides:

```text
NEBIUS_API_KEY
```

the same ANCHOR runtime should use Nemotron for real intent/contract generation.

The user experience should remain almost identical:

```bash
anchor run
```

The only difference is the AI provider.

This means:

```text
No API key
    ↓
Local/demo provider

API key available
    ↓
Nebius/Nemotron provider
```

The safety engine remains the same in both cases.

---

# 14. Design Philosophy

ANCHOR should be:

- Lightweight
- Local-first
- CLI-first
- Deterministic where safety matters
- AI-assisted where reasoning helps
- Provider-independent
- Easy to understand
- Easy to install
- Easy to test
- Easy to extend

Do not turn ANCHOR into a large AI platform.

Do not add unnecessary:

- RAG
- Vector databases
- Web search
- Multi-agent systems
- Cloud databases
- Complex dashboards
- Model training
- Kubernetes
- Large infrastructure

The core product should remain:

```text
CONTRACT
   ↓
POLICY
   ↓
RISK
   ↓
ACTION
   ↓
VERIFY
   ↓
UNDO
```

---

# 15. Core Product Statement

ANCHOR should communicate one simple idea:

> **AI agents don't need to be perfect. They need to be controllable.**

The product is not another AI chatbot or AI wrapper.

The AI model helps understand intent.

ANCHOR provides the deterministic boundary that controls what the AI is actually allowed to do.

Both modes must remain functional:

```text
                    ANCHOR
                       │
             ┌─────────┴─────────┐
             │                   │
        No API Key           User API Key
             │                   │
       Local Provider        Nemotron
             │                   │
             └─────────┬─────────┘
                       ▼
                SAME CORE ENGINE
                       │
              Contract / Policy
                       │
                 Risk / Action
                       │
                 Verify / Undo
```

The final implementation should preserve this architecture throughout development.