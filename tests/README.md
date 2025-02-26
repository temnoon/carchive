# Carchive Tests

This directory contains tests for the Carchive application, with special focus on the agent system.

## Test Structure

- **Unit tests**: Basic tests that verify initialization and structure
- **Integration tests**: Tests that interact with Ollama and other services
- **End-to-end tests**: Tests that verify complete workflows

## Running Tests

### Basic Test Run

Run all tests:
```
poetry run pytest
```

Run specific test file:
```
poetry run pytest tests/test_agent_system.py
```

Run specific test function:
```
poetry run pytest tests/test_agent_system.py::test_embedding_agent_initialization
```

### Testing with Markers

Run only integration tests:
```
poetry run pytest -m integration
```

Skip integration tests:
```
poetry run pytest -m "not integration"
```

### Testing with Verbosity

For more detailed output:
```
poetry run pytest -v
```

For even more detailed output:
```
poetry run pytest -vv
```

## Test Data

- Place test images in `tests/test_data/` directory
- The default test image path is `tests/test_data/test_image.jpg`

## Requirements

- For all tests: Working Python environment with dependencies installed
- For integration tests: Ollama running locally with the following models:
  - `nomic-embed-text`: for embedding tests
  - `llama3.2`: for chat and content tests
  - `llama3.2-vision`: for multimodal tests