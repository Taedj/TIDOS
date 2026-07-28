# TIDOS Plugin: Firebase Infrastructure

## 1. Detection Rules
- **Signature Files**: `firebase.json`, `.firebaserc`, `firestore.rules`
- **Dependencies**: `firebase-admin`, `firebase-functions`, `firebase_core`

## 2. Initialization Steps
- Verify Firebase CLI installation (`firebase --version`).
- Validate Firebase project binding in `.firebaserc`.

## 3. Documentation to Generate
- `FIREBASE_RULES.md`: Security rule coverage and authentication specs.

## 4. Best Practices
- Keep Cloud Functions single-purpose, stateless, and idempotent.
- Isolate service account credentials in secure environment secrets.

## 5. Coding Standards
- Wrap Cloud Function handlers in try-catch with `HttpsError` propagation.
- Use explicit region selection (`region('us-central1')`).

## 6. Review & Quality Rules
- Validate zero wildcard `allow read, write: if true;` rules in `firestore.rules`.
- Ensure emulator test suite passes before deployment.

## 7. Research Topics
- Firebase Genkit AI integrations, Cloud Run for Functions v2, App Check security.
