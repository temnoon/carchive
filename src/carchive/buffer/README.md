# Results Buffer System

The Results Buffer System is a component of the carchive application that enables storing, manipulating, and transforming search results and other collection of entities across multiple commands.

## Overview

The buffer system allows users to:

1. Store search results for later use
2. Filter, merge, and transform results using set operations
3. Convert results to collections for permanent storage
4. Chain multiple search operations together

## Components

The system consists of the following key components:

### Database Models

- `ResultsBuffer`: Stores metadata about a buffer
- `BufferItem`: Stores references to various entity types (messages, conversations, chunks, agent outputs)

### Core Implementation Files

- `schemas.py`: Pydantic models for buffer operations
- `buffer_manager.py`: Core functionality for CRUD operations on buffers
- `operations.py`: Higher-level operations (filtering, set operations)

### CLI Interface

The buffer system is exposed through the CLI interface in `buffer_cli.py` with the following commands:

- `create`: Create a new buffer
- `list`: List available buffers
- `show`: Display buffer contents
- `clear`: Remove all items from a buffer
- `delete`: Delete a buffer completely
- `filter`: Filter buffer contents by various criteria
- `to-collection`: Convert buffer to a collection
- Set operations: `intersect`, `union`, `difference`

## Buffer Types

The system supports three types of buffers:

1. `EPHEMERAL`: In-memory buffers that are lost when the session ends
2. `SESSION`: Persist within a CLI session (default)
3. `PERSISTENT`: Saved to the database, persists across sessions

## Entity Support

The buffer system can store references to:

- Messages
- Conversations
- Chunks
- Agent outputs (gencom)

## Set Operations

The system provides several set operations:

- `union`: Combine multiple buffers, optionally removing duplicates
- `intersect`: Find items present in all specified buffers
- `difference`: Find items in one buffer that are not in others

## Integration Points

The buffer system integrates with:

- Search system through the `--buffer` flag in the find command
- Collection system through the `to-collection` command

## Example Workflows

### Filtering Search Results

```bash
# Search for messages containing "AI"
carchive search find --buffer search_results "AI"

# Filter to only user messages
carchive buffer filter search_results --role user --target user_messages

# Filter those to messages with images
carchive buffer filter user_messages --has-image --target user_messages_with_images
```

### Combining Multiple Searches

```bash
# Perform multiple searches
carchive search find --buffer results1 "machine learning"
carchive search find --buffer results2 "neural networks"

# Find items present in both searches
carchive buffer intersect results1 results2 --target common_results

# Convert to a permanent collection
carchive buffer to-collection common_results "ML and Neural Networks" --description "Common results about ML and neural networks"
```

## Converting AgentOutputs (gencom) to Collections

The Results Buffer System properly handles agent outputs (gencom) when converting to collections. When a buffer containing agent output references is converted to a collection:

1. Each agent output is evaluated based on its target type and target ID
2. The actual entity referenced by the agent output is added to the collection
3. Duplicates are automatically removed, ensuring a clean collection

This enables seamless conversion of gencom search results to collections.