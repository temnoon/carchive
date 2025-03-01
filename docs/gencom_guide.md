# Gencom - AI-Generated Comments Feature

Gencom is a feature in Carchive that generates AI-powered comments on content items (messages, conversations, and chunks). These comments can be used for content analysis, summarization, topic labeling, or extracting insights from archived content.

## Overview

The Gencom system allows you to:

1. Generate AI comments on individual messages
2. Generate AI comments on entire conversations
3. Generate AI comments on content chunks (when implemented)
4. Optionally generate embeddings for the AI comments
5. Batch process collections of content

## Usage

### Command Line Interface

The gencom CLI provides several commands for generating comments:

#### Individual Content Items

```bash
# Generate a comment for a specific message
poetry run carchive gencom message <message-id> --provider openai --embed

# Generate a comment for a specific conversation
poetry run carchive gencom conversation <conversation-id> --provider anthropic
```

#### Batch Processing

```bash
# Generate comments for messages with specific criteria
poetry run carchive gencom all --target-type message --min-word-count 10 --role user

# Generate comments for all conversations in the last 30 days
poetry run carchive gencom all --target-type conversation --days 30

# Generate comments with embeddings for search and analysis
poetry run carchive gencom all --target-type message --min-word-count 20 --embed
```

#### Custom Templates

You can customize the prompt template for comment generation:

```bash
# Use a custom template for analysis
poetry run carchive gencom message <message-id> --prompt-template "Analyze this content for key themes and sentiments: {content}"

# Interactive mode to enter a template when running
poetry run carchive gencom conversation <conversation-id> --interactive
```

### Key Parameters

- `--provider`: Specify the AI provider (ollama, openai, anthropic)
- `--embed`: Generate embeddings for the comments
- `--embed-provider`: Use a different provider for embeddings
- `--target-type`: Type of content to process (message, conversation, chunk)
- `--min-word-count`: Minimum word count for content to process
- `--role`: Filter by message role (user, assistant, system)
- `--days`: Only process content from the last N days
- `--override`: Force regeneration even if comments already exist

## Technical Details

### Database Structure

Gencom comments are stored in the `agent_outputs` table with:
- `target_type`: "message", "conversation", or "chunk"
- `target_id`: UUID of the target content
- `output_type`: "gencom"
- `content`: The generated comment text
- `agent_name`: The AI model used for generation

### Embeddings Integration

When embeddings are enabled:
1. Comments are generated and stored in the database
2. Embeddings are created for each comment
3. The embeddings reference the agent_output via the `parent_type` and `parent_id` fields

These embeddings can be used for semantic search and content clustering.

## Use Cases

- **Content Analysis**: Generate insights about message content
- **Conversation Summarization**: Create summaries of entire conversations
- **Topic Extraction**: Identify key themes in content
- **Content Organization**: Use gencom with embeddings for semantic clustering

## Examples

### Basic Generation

```bash
# Generate a comment on a message
poetry run carchive gencom message 550e8400-e29b-41d4-a716-446655440000

# Output:
# Generated comment for message 550e8400-e29b-41d4-a716-446655440000 (AgentOutput ID: e7d5bf90-3893-4d1a-90d7-991102fa792c).
```

### Batch Processing with Embeddings

```bash
# Process all user messages with at least 20 words
poetry run carchive gencom all --min-word-count 20 --role user --embed

# Output:
# Generated comments complete.
# Processed: 142, Failed: 3, Skipped: 12
# Embeddings: 142 created, 0 failed
```

### Custom Analysis

```bash
# Analyze sentiment in a conversation
poetry run carchive gencom conversation 550e8400-e29b-41d4-a716-446655440000 \
    --prompt-template "Analyze the emotional tone and key sentiments in this conversation: {content}" \
    --provider openai

# Output:
# Generated comment for conversation 550e8400-e29b-41d4-a716-446655440000 (AgentOutput ID: a8d5bf90-3893-4d1a-90d7-991102fa7654).
```