# Evolution Suggestions

This file tracks non-invasive improvement proposals for TIDOS. All suggestions are reviewed before any protected system files are modified.

## Suggestion Template

```markdown
### Title: [Short descriptive name]

- **Reason**: Why this change is needed
- **Benefits**: What improvements it brings
- **Risks**: Potential downsides or breaking changes
- **Priority**: Critical / High / Medium / Low
- **Affected Modules**: Which directories/files would be affected
- **Recommended Version**: Target SemVer version
```

## Submitted Suggestions

*No suggestions recorded yet. Use the template above to submit proposals.*

---

### Suggestion Format Example

### Title: Add MCP Server Support

- **Reason**: Many AI agents support MCP protocol for tool-based context hydration
- **Benefits**: Direct OS context injection without manual file reads
- **Risks**: Requires new dependency and maintenance
- **Priority**: Medium
- **Affected Modules**: `engines/`, `docs/tools/`, `scripts/`
- **Recommended Version**: 2.1.0
