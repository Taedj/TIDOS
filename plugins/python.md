# TIDOS Plugin: Python Services (v3.0)

## 1. Detection Rules
- **Signature Files**: `pyproject.toml`, `requirements.txt`, `setup.py`, `Pipfile`
- **File Extensions**: `.py`

## 2. Initialization Steps
- Verify Python version (`python --version` ≥ 3.10).
- Validate virtual environment activation and dependency installation.

## 3. Documentation to Generate
- `PYTHON_ARCHITECTURE.md`: Document module layout, type annotation strategy, and dependency injection.

## 4. Best Practices
- Use Pydantic models for data validation and serialization.
- Structure projects using `src/` layout with clear `__init__.py` module boundaries.

## 5. Coding Standards
- Enforce PEP 8 style compliance via `ruff` or `black` formatter.
- Require type annotations on all public function signatures.

## 6. Review & Quality Rules
- Validate zero bare `except:` clauses (require typed exception handling).
- Verify `mypy --strict` or `pyright` type checking passes cleanly.

## 7. Research Topics
- UV package manager benchmarks, FastAPI Strawberry GraphQL, Pydantic v2 performance.
