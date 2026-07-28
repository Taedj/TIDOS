# TIDOS Plugin: Python Systems & Microservices

## 1. Detection Rules
- **Signature Files**: `pyproject.toml`, `requirements.txt`, `Pipfile`, `setup.py`
- **File Extensions**: `.py`

## 2. Initialization Steps
- Verify Python runtime (`python --version`) and package manager (`uv`, `poetry`, `pip`).
- Validate virtual environment activation (`.venv`).

## 3. Documentation to Generate
- `PYTHON_ARCHITECTURE.md`: Document module structure, type annotations, and virtual environment setup.

## 4. Best Practices
- Enforce strict type hints (`typing` module / Python 3.10+ union types `X | Y`).
- Use Pydantic for data validation and configuration schemas.

## 5. Coding Standards
- Adhere strictly to PEP 8 styling enforced by `ruff` or `black` & `flake8`.
- Use `pytest` for unit and integration testing.

## 6. Review & Quality Rules
- Validate 100% type checker clean pass using `mypy` or `pyright`.
- Check async non-blocking concurrency for FastAPI / asyncio routines.

## 7. Research Topics
- Python 3.13 JIT compiler, `uv` ultra-fast package manager, Polars for data processing.
