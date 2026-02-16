# SECURITY_AI

<!-- AGENTSGEN:START section=security_ai -->
## Security guardrails
- Never hardcode credentials or secrets.
- Never print secrets in logs.
- Ask before touching auth, payments, crypto, or compliance paths.
- Prefer additive edits over destructive changes.

## Incident handling
- If a potential secret leak is found, stop and report immediately.
- Provide a minimal remediation plan with verification steps.
<!-- AGENTSGEN:END section=security_ai -->
