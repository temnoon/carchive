# Carchive2

Carchive2 is a modern conversation archiving and analysis system designed to store, organize, search, and analyze text-based conversations using vector embeddings and AI.

## Features

- **Conversation Archiving**: Store and organize text-based conversations
- **Vector Search**: Find semantically similar content using pgvector
- **AI Analysis**: Generate summaries, insights, and connections between conversations
- **Media Management**: Link media files with conversation messages
- **Clustering**: Automatically group similar content
- **Content Generation**: Create documents from conversation snippets

## Prerequisites

- Python 3.10+
- PostgreSQL with pgvector extension
- Poetry for dependency management

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/carchive.git
   cd carchive
   ```

2. Install dependencies:
   ```
   poetry install
   ```

3. Set up environment variables (create a `.env` file):
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/carchive
   ANTHROPIC_API_KEY=your_anthropic_api_key  # Optional for AI features
   OPENAI_API_KEY=your_openai_api_key  # Optional for AI features
   ```

4. Run database migrations:
   ```
   poetry run alembic upgrade head
   ```

## Usage

```
# Run CLI
poetry run carchive

# Search conversations
poetry run carchive search "your search query"

# Generate embeddings
poetry run carchive embed

# Cluster similar content
poetry run carchive cluster

# Run API server
poetry run carchive api
```

## Development

```
# Run tests
poetry run pytest

# Add dependency
poetry add package_name
```

## License

[MIT License](LICENSE)