# CLAUDE.md - carchive Development Guide

## Build and Run Commands
- Setup: `poetry install`
- Run CLI: `poetry run carchive`
- Run single test: `poetry run pytest tests/test_filename.py::test_function_name -v`
- Run all tests: `poetry run pytest`
- Add dependency: `poetry add package_name`

## Code Style Guidelines
- **Structure**: Follow modular design with core/, database/, agents/, etc. folders
- **Imports**: Group stdlib, then third-party, then local imports with a blank line between groups
- **Types**: Use type hints for function parameters and return values
- **Naming**: snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
- **Docstrings**: Include docstrings for all modules, classes, and functions (triple quotes)
- **Error handling**: Use specific exceptions with informative messages
- **SQLAlchemy**: Follow established patterns for models with descriptive relationships
- **CLI**: Implement with Typer, with clear help text and logical command structure
- **Testing**: Test files should be in tests/ directory with clear test_* naming

## PostgreSQL and pgvector
This project uses PostgreSQL with pgvector for vector embeddings, requiring proper database setup.
