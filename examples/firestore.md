# TIDOS + Firestore Integration Example

## Project Type
Firestore NoSQL database project with cost-optimized data modeling.

## TIDOS Connection

```bash
cd firestore_project
git submodule add https://github.com/tidjani/TIDOS.git .tidos
```

## Plugins Mounted

- `plugins/firestore.md` - Firestore specification

## Best Practices Enforced

- Document size limits (< 1 MiB per document)
- Index coverage for all queries
- Batched writes for bulk operations
- Collection group queries for cross-collection access
- Security rules validation

## Example Use Case

Firestore-based chat application with subcollection messages, real-time listeners, and compound index configuration.
