# TIDOS Plugin: Firestore Database & Cost Optimizer (v3.0)

## 1. Detection Rules
- **Signature File**: `firestore.rules`, `firestore.indexes.json`
- **Dependencies**: `cloud_firestore`, `@google-cloud/firestore`

## 2. Initialization Steps
- Verify `firestore.indexes.json` structure.
- Validate security rules syntax (`firebase deploy --only firestore:rules --dry-run`).

## 3. Documentation to Generate
- `FIRESTORE_SCHEMA.md`: Document collection schemas, subcollections, and cost optimizations.

## 4. Best Practices
- Structure collections to optimize read volume; denormalize static lookup data.
- Use subcollections for document-owned sub-entities.

## 5. Coding Standards
- Require `.limit()` clause on every collection query.
- Use batch writes (`WriteBatch`) or transactions (`runTransaction`) for multi-document mutations.

## 6. Review & Quality Rules
- Reject unbound `.snapshots()` listeners on broad collections.
- Ensure composite index declarations match query filters.

## 7. Research Topics
- Firestore Vector Search (pgvector equivalents), Bundle caching, Aggregation query count optimizations.
