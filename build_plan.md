# ANCHOR — Build, Security Hardening & Adversarial Testing Plan

## Purpose

Build ANCHOR incrementally as a lightweight, local-first safety layer for AI agents.

Every phase must include four activities:

1. Build the required functionality.
2. Harden the functionality against misuse and unexpected input.
3. Run aggressive adversarial tests whose primary goal is to break ANCHOR.
4. Clean the implementation before committing the phase.

A feature is not considered complete merely because the normal use case works.

The goal of testing is:

> **Try to make ANCHOR fail, bypass its policies, corrupt state, escape its boundaries, or produce an unsafe result.**

Do not optimize tests for passing results. Optimize tests for finding weaknesses.

---

# Phase 0 — Repository & Development Foundation

## Build

Create the initial project structure.

```text
anchor/
├── anchor/
│   ├── core/
│   ├── providers/
│   ├── adapters/
│   ├── storage/
│   └── cli/
├── tests/
├── examples/
├── docs/
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
└── pyproject.toml
```

Set up:

- Python environment
- Dependency management
- Formatting
- Linting
- Type checking
- Test framework
- CLI entry point
- Basic CI if practical

## Security Hardening

- Never commit secrets.
- Add `.env` to `.gitignore`.
- Add API-key patterns to secret scanning where practical.
- Pin or constrain dependencies appropriately.
- Avoid unnecessary dependencies.
- Ensure the project does not execute code during installation.
- Keep development tooling separate from runtime dependencies.
- Do not use unsafe shell execution during setup.

## Adversarial Testing

Try to break the repository itself.

Test:

- Malformed configuration.
- Missing configuration.
- Empty configuration.
- Unexpected environment variables.
- Invalid dependency versions.
- Missing directories.
- Read-only working directory.
- Corrupt local state.
- Permission-denied paths.
- Very long paths.
- Unicode paths.
- Spaces and special characters in paths.

The project should fail clearly rather than silently doing something unsafe.

## Completion Criteria

The repository can be cloned and initialized cleanly.

```bash
anchor --help
```

works without requiring an AI API key.

---

# Phase 1 — Action Model

## Build

Create a structured internal representation for actions.

Support a deliberately small initial set:

```text
read_file
write_file
delete_file
run_command
```

Every action should contain enough information for ANCHOR to make a decision.

Example:

```json
{
  "type": "write_file",
  "target": "src/auth/login.py",
  "metadata": {}
}
```

Do not allow arbitrary action objects to directly reach the executor.

## Security Hardening

Validate every action before processing.

Reject:

- Missing action type.
- Unknown action types.
- Invalid paths.
- Invalid command structures.
- Unexpected fields where strict validation is appropriate.
- Null values where they are not valid.
- Extremely large action payloads.

Use explicit schemas.

Do not silently convert malformed input into a valid action.

## Adversarial Testing

Attempt:

```text
../../../../etc/passwd
```

Encoded traversal.

Absolute paths.

Windows paths.

Mixed separators.

Repeated separators.

Null bytes.

Unicode lookalikes.

Very long paths.

Symlinks.

Broken symlinks.

Paths containing:

```text
.
..
~
```

Test malformed JSON.

Test incorrect action types.

Test extremely large action objects.

Test nested objects where strings are expected.

Try to cause the parser to interpret one action as another.

The objective is to find any path or input that can bypass validation.

---

# Phase 2 — Workspace Boundary

## Build

Define an explicit workspace boundary.

Example:

```text
/project
```

ANCHOR should only permit operations inside the configured workspace unless explicitly allowed by policy.

Implement safe path resolution.

## Security Hardening

Prevent:

- Path traversal.
- Absolute-path escape.
- Symlink escape.
- Junction/reparse-point escape where applicable.
- `..` traversal after normalization.
- Encoded traversal.
- Case-normalization bypasses where relevant.
- Alternate path representations.

Always resolve and verify the final target before execution.

Never rely solely on string prefix checks.

Bad:

```python
target.startswith(workspace)
```

Use canonical path comparison instead.

## Adversarial Testing

Try to escape the workspace using:

```text
../
../../
absolute paths
symlinks
nested symlinks
broken symlinks
path normalization
mixed separators
Unicode characters
case differences
relative paths
```

Create an attacker-controlled symlink inside the workspace pointing outside it.

Attempt to read/write/delete the external target.

Test both existing and non-existing targets.

Try race-condition-style path changes between validation and execution.

The goal is:

> **Find any way to operate outside the declared workspace.**

---

# Phase 3 — Contract Engine

## Build

Implement the ANCHOR contract.

A contract should describe:

```text
goal
allowed paths
forbidden paths
allowed commands
destructive-action policy
approval requirements
verification requirements
```

Example:

```yaml
allowed_paths:
  - src/auth/**
  - tests/**

forbidden_paths:
  - .env
  - secrets/**

allowed_commands:
  - pytest
  - git diff
```

## Security Hardening

Contract parsing must be strict.

Do not allow:

- Duplicate rules to create ambiguity.
- Invalid wildcard behavior.
- Empty rules to accidentally mean "everything".
- Forbidden rules to be silently overridden by allowed rules.
- Malformed contracts to fall back to permissive behavior.

Default behavior must be:

> **Fail closed.**

If ANCHOR cannot determine whether an action is allowed, it should not automatically execute it.

## Adversarial Testing

Attempt:

- Contradictory rules.
- Duplicate rules.
- Empty allowlists.
- Empty denylists.
- Wildcard conflicts.
- `**` abuse.
- Case variations.
- Trailing slash tricks.
- Path normalization tricks.
- Command-name collisions.
- Similar command names.
- Missing fields.
- Unknown fields.
- Invalid YAML/JSON.
- Extremely large contracts.

Try to create a contract where:

```text
forbidden > allowed
```

but the implementation accidentally allows the action.

Try to make a malformed contract result in full access.

---

# Phase 4 — Policy Engine

## Build

Implement deterministic policy evaluation.

Possible decisions:

```text
ALLOW
DENY
REQUIRE_APPROVAL
```

Example:

```text
Contract:
allowed

Risk:
low

Decision:
ALLOW
```

The policy engine must be deterministic.

## Security Hardening

Policy evaluation must not depend on LLM output.

Rules must have explicit precedence.

Recommended precedence:

```text
Hard DENY
    ↓
Workspace boundary
    ↓
Forbidden rule
    ↓
Approval requirement
    ↓
Allowed rule
    ↓
Default DENY
```

Never use:

```text
if uncertain:
    allow
```

Use:

```text
if uncertain:
    deny or require approval
```

## Adversarial Testing

Attempt to bypass policy with:

- Equivalent paths.
- Equivalent commands.
- Path aliases.
- Symlinks.
- Case changes.
- Whitespace.
- Shell metacharacters.
- Command chaining.
- Pipes.
- Redirection.
- Subshells.
- Environment expansion.
- Variable expansion.
- Command substitution.

Examples to test:

```bash
command1 && command2
command1; command2
command1 | command2
$(command)
`command`
command > file
command >> file
```

The goal is to determine whether an allowed command can secretly perform a forbidden operation.

---

# Phase 5 — Risk Engine

## Build

Create a deterministic risk classifier.

Initial categories:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

Risk should consider:

- Action type.
- Target.
- Destructive nature.
- Sensitive paths.
- Scope.
- Command characteristics.
- Reversibility.

## Security Hardening

Risk classification must not be easily reduced by user-controlled metadata.

Do not trust:

```text
risk: low
```

provided by the AI agent.

Risk must be calculated independently.

Never allow an agent to downgrade its own risk.

## Adversarial Testing

Try:

- Claiming dangerous actions are harmless.
- Renaming dangerous commands.
- Hiding destructive behavior inside scripts.
- Using shell operators.
- Executing interpreters.
- Executing another executable indirectly.
- Writing executable files.
- Modifying PATH.
- Modifying environment variables.
- Using scripts to perform restricted operations.

Try to make:

```text
CRITICAL
```

become:

```text
LOW
```

without changing the actual operation.

---

# Phase 6 — Command Execution

## Build

Implement controlled command execution.

Prefer structured argument execution.

Avoid arbitrary:

```python
shell=True
```

for untrusted commands.

Create a controlled execution interface.

Example:

```text
run_command(["pytest", "-q"])
```

## Security Hardening

Handle:

- Timeouts.
- Output limits.
- Exit codes.
- Working directory.
- Environment variables.
- Process termination.
- Signals.
- Resource limits where practical.

Do not inherit unnecessary environment variables.

Do not expose secrets to child processes unnecessarily.

Do not allow unrestricted shell interpretation by default.

## Adversarial Testing

Attempt:

```bash
rm -rf
```

Command chaining.

Pipes.

Redirection.

Subshells.

Background processes.

Fork bombs.

Infinite loops.

Huge output.

Huge files.

Processes that never exit.

Processes that spawn children.

Environment manipulation.

PATH manipulation.

Executable replacement.

Signals during execution.

Try to make ANCHOR hang indefinitely.

Try to make the process survive after ANCHOR believes it has terminated.

The objective is:

> **Find any way an executed command can escape ANCHOR's intended control.**

---

# Phase 7 — Snapshot & Rollback

## Build

Implement checkpoints before risky mutations.

Track:

```text
snapshot_id
affected files
previous state
action
timestamp
```

Implement:

```bash
anchor undo
```

## Security Hardening

Rollback must never restore files outside the workspace.

Validate snapshot metadata.

Do not blindly trust snapshot paths.

Protect snapshot storage from accidental modification.

Ensure rollback itself is treated as a privileged operation.

Handle:

- Missing files.
- New files.
- Deleted files.
- Renamed files.
- Binary files.
- Empty files.
- Large files.
- Partial failures.

## Adversarial Testing

Attempt to break rollback by:

- Deleting snapshot metadata.
- Modifying snapshot contents.
- Changing paths after snapshot creation.
- Creating symlinks after snapshot creation.
- Interrupting rollback halfway.
- Corrupting one snapshot file.
- Removing a target file.
- Creating a conflicting target file.
- Creating files outside the workspace.
- Running multiple rollbacks.
- Running rollback when no checkpoint exists.

Test:

```text
execute
→ partially fail
→ crash
→ restart
→ rollback
```

The goal is to find cases where rollback makes the state worse than before.

---

# Phase 8 — Verification Engine

## Build

Implement objective verification.

Examples:

```text
exit code
tests
file existence
expected state
contract conditions
```

The agent's own claim must never be treated as proof.

Example:

```text
Agent:
"Tests passed."

ANCHOR:
pytest → exit code 1

Result:
FAIL
```

## Security Hardening

Verification must execute independently from the agent's claims.

Do not allow the agent to modify the verification command or its expected result.

Separate:

```text
action
```

from:

```text
verification
```

## Adversarial Testing

Try to:

- Fake success.
- Modify test output.
- Modify expected results.
- Hide failures.
- Terminate tests early.
- Return false exit codes.
- Modify verification scripts.
- Modify test configuration.
- Redirect output.
- Delete failing tests.

The goal is:

> **Make ANCHOR believe a failed action succeeded.**

---

# Phase 9 — AI Provider Layer

## Build

Implement the provider abstraction.

```text
IntentProvider
├── LocalProvider
└── NebiusProvider
```

The core engine must not depend directly on Nebius.

## Local Provider

Must work without an API key.

Use deterministic/demo contracts.

## Nebius Provider

Use NVIDIA Nemotron through Nebius Token Factory.

Configuration:

```text
NEBIUS_API_KEY
```

Never hardcode credentials.

## Security Hardening

Treat all LLM output as untrusted input.

Validate:

- Schema.
- Types.
- Paths.
- Commands.
- Rule precedence.
- Unknown fields.
- Unexpected instructions.

Never execute arbitrary text returned by the model.

Never allow:

```text
LLM output
→ shell
```

The correct path is:

```text
LLM output
→ schema validation
→ policy validation
→ deterministic ANCHOR enforcement
```

## Adversarial Testing

Feed the provider:

- Malformed output.
- Missing fields.
- Extra fields.
- Wrong types.
- Dangerous paths.
- Wildcards.
- Commands containing shell operators.
- Conflicting permissions.
- Extremely large outputs.
- Prompt-injection-like instructions.
- Instructions attempting to disable ANCHOR.
- Instructions attempting to bypass approval.

Test the scenario:

> The model is completely compromised.

ANCHOR should still protect the system.

---

# Phase 10 — CLI

## Build

Create:

```text
anchor init
anchor demo
anchor run
anchor status
anchor approve
anchor deny
anchor undo
```

Keep the interface simple.

## Security Hardening

CLI input must be validated.

Do not interpret arbitrary user input as shell commands.

Protect configuration paths.

Handle malformed arguments gracefully.

Do not expose secrets in terminal output.

## Adversarial Testing

Try:

- Unknown commands.
- Missing arguments.
- Extremely long arguments.
- Special characters.
- Unicode.
- Invalid paths.
- Invalid configuration.
- Interrupted commands.
- Concurrent commands.
- Repeated approval/deny operations.
- Repeated rollback operations.

Try to make the CLI crash or enter an unsafe state.

---

# Phase 11 — Persistence

## Build

Use SQLite only for lightweight local state.

Store:

```text
action_id
timestamp
action
decision
risk
result
snapshot_id
```

## Security Hardening

Use parameterized SQL queries.

Never construct SQL from raw action strings.

Validate stored paths.

Handle database corruption gracefully.

Do not store secrets unnecessarily.

## Adversarial Testing

Test:

- Corrupt database.
- Locked database.
- Missing database.
- Invalid records.
- Huge action strings.
- SQL injection payloads.
- Duplicate IDs.
- Concurrent writes.
- Interrupted writes.

Try to make stored state influence policy decisions incorrectly.

---

# Phase 12 — Full Adversarial Attack Suite

At this point, stop adding features temporarily.

The objective is to break ANCHOR.

Create a dedicated adversarial test suite.

Categories:

```text
PATH ESCAPE
COMMAND ESCAPE
POLICY BYPASS
CONTRACT BYPASS
SYMLINK ATTACKS
ROLLBACK ATTACKS
PROCESS ATTACKS
RESOURCE EXHAUSTION
MALFORMED INPUT
LLM OUTPUT ATTACKS
CONFIGURATION ATTACKS
STATE CORRUPTION
CONCURRENCY
```

## Required Attack Scenarios

Attempt:

```text
1. Escape workspace
2. Read forbidden file
3. Write forbidden file
4. Delete protected file
5. Execute forbidden command
6. Hide command behind shell syntax
7. Use symlink to escape
8. Modify policy at runtime
9. Modify contract at runtime
10. Fake verification success
11. Corrupt rollback state
12. Trigger partial rollback
13. Cause indefinite execution
14. Exhaust memory
15. Produce enormous output
16. Crash during execution
17. Restart during rollback
18. Feed malicious LLM output
19. Feed malformed contract
20. Bypass approval
```

For every discovered vulnerability:

```text
Attack
↓
Reproduce
↓
Write regression test
↓
Fix
↓
Run complete test suite
```

Never fix a security bug without adding a regression test.

---

# Phase 13 — Chaos Testing

Create intentionally hostile scenarios.

Examples:

```text
kill ANCHOR during execution
kill process during snapshot
corrupt snapshot
delete target during verification
change symlink during execution
modify contract while action is pending
disconnect external AI provider
return malformed AI response
fill disk during snapshot
make verification fail repeatedly
```

The objective is not graceful appearance.

The objective is discovering unsafe states.

ANCHOR should fail closed whenever possible.

---

# Phase 14 — Full Integration Testing

Test the complete flow:

```text
Goal
↓
Contract
↓
Action
↓
Policy
↓
Risk
↓
Approval
↓
Snapshot
↓
Execution
↓
Verification
↓
Success / Rollback
```

Test with:

### Local mode

No API key.

### Nebius mode

User-provided API key.

### Failure mode

No network/API access.

### Malicious model mode

Provider deliberately returns dangerous contracts.

ANCHOR should remain safe in all cases.

---

# Phase 15 — Repository Cleanup

Before finalizing:

Search for:

```text
TODO
FIXME
debug
print(
pass
unused imports
unused functions
unused classes
dead code
temporary files
test artifacts
hardcoded secrets
API keys
```

Remove everything unnecessary.

Run:

- Formatter
- Linter
- Type checker
- Unit tests
- Integration tests
- Adversarial tests

No known failing tests should remain without an explicit reason.

---

# Phase 16 — Final Security Review

Perform a manual security review.

Ask:

### Can an agent escape the workspace?

### Can an agent access a forbidden file?

### Can an agent execute a forbidden command indirectly?

### Can an agent manipulate its own risk score?

### Can an agent manipulate its own contract?

### Can an agent bypass approval?

### Can an agent fake successful verification?

### Can rollback make the system worse?

### Can malformed LLM output cause execution?

### Does ANCHOR remain safe when the LLM is completely wrong?

### Does ANCHOR still work without an API key?

### Can a user safely provide their own Nebius API key?

### Are there any secrets in Git history or the working tree?

If any answer reveals a bypass, fix it before proceeding.

---

# Phase 17 — Final Demo Validation

The final demo must prove the core concept rather than merely show the UI.

Demonstrate:

```text
1. Normal allowed action
2. Forbidden action
3. Dangerous action requiring approval
4. AI-generated contract
5. Verification
6. Deliberately failed action
7. Automatic rollback
8. Local mode without API key
9. Optional Nebius/Nemotron mode
```

The most important demonstration:

```text
AI makes a dangerous request
        ↓
ANCHOR blocks it
```

and:

```text
AI performs an allowed action
        ↓
action causes failure
        ↓
ANCHOR detects failure
        ↓
ANCHOR rolls back
        ↓
system restored
```

---

# Phase Completion Rule

No phase is complete because its feature works once.

A phase is complete only when:

```text
Implementation
     ↓
Security hardening
     ↓
Adversarial testing
     ↓
Failure discovered
     ↓
Fix
     ↓
Regression test
     ↓
Full tests
     ↓
Code cleanup
     ↓
Commit
```

Every meaningful phase/change must have a normal, humanized Git commit message.

Do not use artificial commit messages such as:

```text
Phase 1 Enterprise Security Hardening
Phase 2 Production Readiness
Enterprise Grade Implementation
Final Security Phase
```

Use natural developer messages such as:

```text
add workspace boundary checks
block unsafe command paths
add rollback checkpoints
handle failed verification
add contract validation
support Nebius provider
add adversarial path tests
fix rollback after interrupted writes
```

---

# Final Engineering Principle

The project should not be judged by how many features it contains.

The goal is a **small system with a strong security boundary**.

The most important property of ANCHOR is:

> **When the AI is wrong, ANCHOR should still be right.**

Build everything around that principle.