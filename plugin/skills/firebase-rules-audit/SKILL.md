---
name: firebase-rules-audit
description: Audit Firestore/Storage security rules and their cost: least privilege, validation, no open reads/writes. Use before deploying rules or when data access changes.
---

# Firebase rules audit
1. **No open access**: search for `allow read, write: if true`, `if request.auth != null` on sensitive paths
   (any signed-in user is not authorization).
2. **Least privilege** per collection: owner checks (`request.auth.uid == resource.data.ownerId`), role checks
   from a trusted source (custom claims or an admin-only doc), separate read/create/update/delete.
3. **Validate writes**: allowed fields (`keys().hasOnly`), types, sizes, immutable fields on update.
4. **Test** with the emulator or rules unit tests: allowed and denied cases for each role.
5. **Cost**: queries must be allowed by rules; avoid listeners on huge collections; mind write counts.
6. **Deploy only with the user's OK**: `firebase deploy --only firestore:rules`.

---
With the TIDOS MCP server: `tidos_recall` for what was learned in this project, `tidos_verify` to run the checks. Report: what changed, the check output, and anything still unverified.
