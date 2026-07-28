# Best Practices

## Project Setup

1. Always initialize with TIDOS startup sequence before writing code
2. Use Git submodule for TIDOS integration when possible
3. Enable all 8 quality gates from the start
4. Record ADRs for every significant architectural decision
5. Maintain project memory digest after each session

## Code Quality

1. Follow Clean Architecture layering strictly
2. Keep domain layer pure with zero framework dependencies
3. Write tests before implementation (TDD when feasible)
4. Perform self-review against quality gates before PR submission
5. Run linter and type checker before every commit

## Evolution

1. Never modify protected system files
2. Submit all improvement proposals to evolution/SUGGESTIONS.md
3. Validate patterns through 3+ project repetitions before promotion
4. Maintain backward compatibility across minor versions
