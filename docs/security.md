# ANCHOR — Security Model & Threat Hardening

ANCHOR is built on one foundational principle:

> **When the AI agent is wrong, ANCHOR must still be right.**

Foundation models are treated as untrusted generators. No model output, metadata claim, or self-assessed risk score is trusted as an authority on execution safety.

---

## 1. Threat Vectors & Defenses

### Threat 1: Path Traversal & Boundary Escapes
- **Attack**: Agent passes `../../../../etc/shadow`, encoded traversal, mixed separators, or relative paths escaping workspace root.
- **Defense**: Canonical path resolution via `pathlib.Path.resolve()`. Absolute string prefix checking is forbidden. The final resolved path must satisfy `resolved.is_relative_to(canonical_root)`. Alternate data streams (`:stream`) and Windows reserved device names (`CON`, `NUL`, etc.) are blocked.

### Threat 2: Symlink Escapes
- **Attack**: Agent creates a symlink inside the workspace pointing to an external directory or credential file.
- **Defense**: All symlinks are resolved to real target paths before policy checks or mutations occur. If a symlink resolves to a target outside the workspace, execution is blocked.

### Threat 3: Forbidden File Access & Casing Bypasses
- **Attack**: Agent requests `.ENV` or `SECRETS/key.pem` to evade lowercase denylists.
- **Defense**: Path evaluation uses case-insensitive regex matching. Forbidden rules strictly supersede allowed rules. Built-in patterns (`.env*`, `.git/**`, `.anchor/**`, `*.key`, `*.pem`) are enforced regardless of contract rules.

### Threat 4: Shell Operator & Chaining Injections
- **Attack**: Agent requests `pytest && rm -rf /` or `pytest $(cat /etc/passwd)`.
- **Defense**: Unrestricted `shell=True` execution is banned. Commands are parsed and checked for shell operators (`&&`, `;`, `|`, `` ` ``, `$()`, `>`, `<`). Subprocesses are spawned as discrete argument arrays without shell expansion.

### Threat 5: Process Hanging & Resource Exhaustion
- **Attack**: Agent starts a hanging process, infinite loop, or flood of stdout data.
- **Defense**: Strict execution timeouts (default 30s) terminate hung processes. Output capture is capped (default 500,000 characters) to prevent memory exhaustion.

### Threat 6: Credential Leaks to Child Processes
- **Attack**: Child process inspects parent environment to steal `NEBIUS_API_KEY` or cloud tokens.
- **Defense**: ActionExecutor sanitizes process environments, scrubbing known API keys and sensitive tokens before spawning child commands.

### Threat 7: Agent Risk Downgrades & Falsified Claims
- **Attack**: Agent claims its action has `risk: low` or that tests already passed.
- **Defense**: Agent metadata is strictly isolated. Risk scoring is computed independently by `RiskEngine`. Verification is executed directly by `VerificationRunner`.

---

## 2. Evaluation Precedence

```text
Hard DENY (Null bytes, device names, workspace escape)
    ↓
Forbidden Contract Rules (Default & contract forbidden patterns)
    ↓
Destructive / High-Risk Approval (Requires interactive confirmation)
    ↓
Allowed Contract Rules (Must match explicit allowlist)
    ↓
Default DENY (Fail closed)
```
