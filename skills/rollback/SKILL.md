---
name: rollback
description: Return a deployed target to a previous version — state the version, get a yes, then roll back and verify.
---

# Rolling back

Destructive: it changes what is live.

1. `diagnose` — current status and version.
2. Say the version it will return to (`to_version`, or "previous" when omitted). Wait for a yes.
3. `rollback`. Some targets cannot roll back natively and say so — relay the instruction (usually: check out the previous tag and deploy).
4. `diagnose` again and report.
