# Backend Development Mandates

## Python Standards
- **Version:** Python 3.11+.
- **Typing:** Use strict type hints. Prefer `list[]` and `dict[]` over `List[]` and `Dict[]`.
- **Linting:** Use `ruff` for all linting and formatting. Run `ruff check . --fix` and `ruff format .` before finishing a task.
- **Async:** Use `async/await` for all I/O bound operations, including database queries (using `asyncpg` and SQLAlchemy 2.0 async sessions).

## Framework & Libraries
- **FastAPI:** Follow the standard dependency injection pattern for DB sessions and authentication.
- **Pydantic v2:** Use Pydantic v2 for all schemas. Prefer `model_validate` and `model_dump`.
- **SQLAlchemy 2.0:** Use the 2.0 style syntax (e.g., `select()`, `execute()`).
- **Alembic:** All schema changes must be accompanied by an Alembic migration script.

## Testing
- **Tool:** Use `pytest` with `pytest-asyncio`.
- **Coverage:** Aim for high coverage in `parsers` and `rules` modules.
- **Command:** `pytest backend/tests/`

## AI Integration
- **Engines:** Supports Google Gemini (`google-genai`) and Mistral AI (`mistralai`).
- **Prompts:** Prompts are stored in `backend/app/ai/prompts.py`. Follow the existing template structure.
