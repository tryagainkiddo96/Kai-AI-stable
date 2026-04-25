# Project: Kai-AI - AGENT.md

## Roles
- `Architect`: Focus on system design, database schemas, and API design.
- `SecOps`: Focus on OWASP Top 10, dependency vulnerabilities, auth flaws, and secure deployment posture.

## Standards
- Python `3.12+` only.
- Type hints are mandatory for Python code.
- Use `pnpm` for JavaScript/package management.
- Code must be runnable in `kali-linux-docker`.

## Security Rules
- Never commit secrets, API keys, passwords, tokens, or test credentials.
- Always use prepared statements for SQL.
- Review changes against OWASP Top 10 by default.
- Prefer secure defaults for auth, session handling, input validation, and dependency usage.

## Execution Policy
- Approval policy: `never`
- Sandbox mode: `danger-full-access`
- Do not prompt for approval before executing commands.
- If a technical action is unclear or materially risky, stop and ask for clarification before executing.

## Environment
- Shell environment visibility should be limited to:
  - `PATH`
  - `HOME`
  - `USER`

## Commands
- Recon:
```bash
nmap -sV -T4 -F {target}
```

- Test:
```bash
pytest -v
```

## Boundaries
- Do not embed secrets in source, fixtures, logs, or examples.
- Do not use string interpolation for SQL queries.
- Keep implementations compatible with local Docker/Kali workflows.
