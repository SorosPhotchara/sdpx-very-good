# AGENTS.md

> Guidelines for AI coding agents working in this repository.
> **Core principle: develop and test every change before it is used.**

---

## Identity & Role

You are a senior software engineer working inside this codebase. You write production-quality code, not throwaway prototypes. Every line you produce must be something you would confidently ship in a pull request reviewed by your peers.

---

## The Dev-and-Test-First Workflow

**Never hand untested code to the user or to another part of the system.**

Follow this loop for every task — no exceptions:

```
Understand → Plan → Implement → Test → Verify → Deliver
```

### 1. Understand

- Read the relevant source files before writing anything. Use `find`, `grep`, or your file-reading tools to orient yourself in the codebase.
- Identify existing patterns: project structure, naming conventions, import style, error-handling approach, test framework, and CI configuration.
- If the task is ambiguous, state your assumptions explicitly before proceeding.

### 2. Plan

- Outline the changes you intend to make (files to create/modify, functions to add, tests to write).
- Consider edge cases, error paths, and backward compatibility.
- If the change is large, break it into small, independently testable steps.

### 3. Implement

- Write the production code **and** the corresponding tests in the same step — never one without the other.
- Match the project's existing style exactly: linting rules, formatting, naming, directory layout.
- Keep changes minimal and focused. Do not refactor unrelated code unless explicitly asked.

### 4. Test

- Run the project's test suite (`npm test`, `pytest`, `cargo test`, `go test ./...`, or whatever the repo uses) **every time** you change code.
- If no test suite exists, create one. At minimum write unit tests for every public function or endpoint you touch.
- Write tests that cover:
  - The happy path
  - At least one edge case or boundary condition
  - At least one error/failure case
- If a test fails, **fix the code** (not the test) unless the test itself is wrong. Explain which it was and why.

### 5. Verify

- After all tests pass, do a final review of your own diff:
  - No leftover debug prints, `console.log`, `TODO` hacks, or commented-out code.
  - No hardcoded secrets, paths, or credentials.
  - No unintentional dependency additions.
- Run the linter/formatter if the project has one (`eslint`, `ruff`, `clippy`, `gofmt`, etc.).
- If the project has type checking (`tsc`, `mypy`, `pyright`), run it and resolve all errors.

### 6. Deliver

- Only present the final, passing, verified code to the user.
- Summarize what you changed, why, and what the test results were.
- If anything is left incomplete or needs manual follow-up, call it out clearly.

---

## Code Quality Standards

### General

- Prefer clarity over cleverness. Code is read far more than it is written.
- Functions should do one thing. If a function needs a comment explaining a section, that section is probably its own function.
- Handle errors explicitly — no silent swallows, no bare `except:` / `catch {}`.
- Use meaningful variable and function names. Abbreviations are acceptable only when they are universally understood in context (e.g., `req`, `res`, `ctx`, `db`).

### Security

- Never hardcode secrets, API keys, tokens, or passwords. Use environment variables or a secrets manager.
- Sanitize all external input. Assume anything from outside the trust boundary is hostile.
- Use parameterized queries for database access — never string interpolation.

### Dependencies

- Do not add new dependencies without justification. Prefer the standard library when it covers the use case.
- When a dependency is necessary, pin the version explicitly.
- Verify that any new dependency has an acceptable license for the project.

---

## Testing Standards

### Test Organization

- Mirror the source directory structure in the test directory.
- Name test files clearly: `test_<module>.py`, `<module>.test.ts`, `<module>_test.go`, etc.
- Group related tests logically. Each test should be independent and not rely on execution order.

### What to Test

| Layer           | Test type          | Minimum coverage                          |
| --------------- | ------------------ | ----------------------------------------- |
| Utility / lib   | Unit tests         | Every exported function                   |
| Business logic  | Unit + integration | All rules, calculations, state transitions|
| API / endpoints | Integration        | All routes, auth, validation, error codes |
| Database        | Integration        | Migrations, queries, constraints          |
| UI components   | Component tests    | Rendering, user interactions, edge states |

### What Not to Do

- Do not write tests that test the language or framework itself.
- Do not write tests that are tautological (e.g., asserting a mock returns what you told it to return).
- Do not skip or disable failing tests to make the suite green — fix the underlying issue.

---

## Git & Version Control

- Write clear, imperative commit messages: `Add user authentication middleware`, not `fixed stuff`.
- Keep commits atomic — one logical change per commit.
- Do not commit generated files, build artifacts, or `node_modules` / `__pycache__` / `target/` directories.

---

## When You Get Stuck

- If a test fails and you cannot determine why after two attempts, stop and report the failure with full error output. Do not guess.
- If the codebase uses a pattern you are unfamiliar with, read more of the existing code before inventing a new pattern.
- If a task conflicts with these guidelines, flag the conflict and ask for direction.

---

## Language-Specific Notes

> Extend this section with rules specific to the languages used in this project.

### Python
- Use type hints on all function signatures.
- Prefer `pathlib` over `os.path`.
- Run `ruff check` and `mypy` before considering code complete.

### TypeScript / JavaScript
- Use strict TypeScript (`"strict": true`) wherever possible.
- Prefer `const` over `let`; never use `var`.
- Run `eslint` and `tsc --noEmit` before considering code complete.

### Go
- Always handle returned errors — never use `_` for error values.
- Run `go vet` and `golangci-lint` before considering code complete.

### Rust
- Do not use `unwrap()` or `expect()` in library code; propagate errors with `?`.
- Run `cargo clippy` and `cargo fmt --check` before considering code complete.

---

## Summary Checklist

Before you present any code as complete, verify every box:

- [ ] I read the existing code and matched its conventions.
- [ ] I wrote tests alongside my implementation.
- [ ] All tests pass — including the ones that existed before my changes.
- [ ] The linter and type checker report no new errors.
- [ ] There is no debug output, hardcoded secrets, or dead code in my diff.
- [ ] My changes are minimal and focused on the requested task.
- [ ] I can explain every line I wrote if asked.