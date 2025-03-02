# Gencom - AI-Generated Comments Feature

Gencom is a feature in Carchive that generates AI-powered comments on content items (messages, conversations, and chunks). These comments can be used for content analysis, summarization, topic labeling, or extracting insights from archived content.

## Overview

The Gencom system allows you to:

1. Generate AI comments on individual messages
2. Generate AI comments on entire conversations
3. Generate AI comments on content chunks (when implemented)
4. Create specialized outputs like categories, summaries, and quality ratings
5. Optionally generate embeddings for the AI comments
6. Batch process collections of content
7. Purge existing gencom outputs to experiment with different prompts
8. Analyze and visualize category distribution

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
poetry run carchive gencom all --target-type message --min-word-count 10 --role assistant

# Generate comments for all conversations in the last 30 days
poetry run carchive gencom all --target-type conversation --days 30

# Generate comments with embeddings for search and analysis
poetry run carchive gencom all --target-type message --min-word-count 20 --embed

# Generate specialized categories for messages
poetry run carchive gencom all --target-type message --min-word-count 20 --output-type category --role assistant
```

#### Purging Existing Outputs

```bash
# Purge all gencom category outputs
poetry run carchive gencom purge --output-type gencom_category

# Purge all gencom outputs for a specific target type
poetry run carchive gencom purge --target-type message

# Purge all gencom outputs from a specific provider
poetry run carchive gencom purge --provider-name claude
```

#### Analyzing Category Distribution

```bash
# Display category distribution as a table
poetry run carchive gencom categories --format table

# Create a chart visualization of categories
poetry run carchive gencom categories --format chart --chart-type pie

# Export category distribution to a CSV file
poetry run carchive gencom categories --format csv > categories.csv
```

#### Custom Templates

You can customize the prompt template for comment generation. **IMPORTANT**: Always include the `{content}` placeholder in your templates - this is where the actual content will be inserted.

```bash
# Use a custom template for analysis
poetry run carchive gencom message <message-id> --prompt-template "Analyze this content for key themes and sentiments: {content}"

# Interactive mode to enter a template when running
poetry run carchive gencom conversation <conversation-id> --interactive

# Specialized category prompt template
poetry run carchive gencom message <message-id> --prompt-template "Analyze the following content and provide ONE specific thematic category that best describes it. Be precise and specific with your category name. Focus on the subject matter, not the format: {content}"
```

### Key Parameters

#### Common Parameters
- `--provider`: Specify the AI provider (ollama, openai, anthropic)
- `--embed`: Generate embeddings for the comments
- `--embed-provider`: Use a different provider for embeddings
- `--target-type`: Type of content to process (message, conversation, chunk)
- `--min-word-count`: Minimum word count for content to process
- `--max-words`: Maximum word count for the generated comment
- `--max-tokens`: Maximum token count for the generated comment
- `--role`: Filter by message role (user, assistant, system)
- `--days`: Only process content from the last N days
- `--override`: Force regeneration even if comments already exist
- `--preview-prompt/--no-preview-prompt`: Control whether to show and confirm prompt before generating content
- `--output-type`: Suffix for specialized output types like "category", "summary", or "quality"

#### Purge Command Parameters
- `--output-type`: Specific gencom output type to purge (e.g., "gencom_category")
- `--target-type`: Type of content to purge comments from (message, conversation, chunk)
- `--provider-name`: Name of the provider to filter by
- `--days`: Only purge outputs created in the last N days
- `--dry-run`: Show what would be deleted without actually deleting

#### Categories Command Parameters
- `--output-type`: Specific output type to analyze (default: "gencom_category")
- `--target-type`: Type of content to analyze (message, conversation)
- `--format`: Output format (table, csv, chart)
- `--chart-type`: Type of chart (pie, bar)
- `--chart-output`: Path to save chart image
- `--exclude-generic`: Exclude generic categories from results
- `--min-count`: Minimum count for a category to be included
- `--limit`: Maximum number of categories to display

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
# Process all assistant messages with at least 20 words
poetry run carchive gencom all --min-word-count 20 --role assistant --embed

# Output:
# Generated comments complete.
# Processed: 142, Failed: 3, Skipped: 12
# Embeddings: 142 created, 0 failed
```

### Generating Categories

```bash
# Generate categories for assistant messages
poetry run carchive gencom all --target-type message --min-word-count 20 --role assistant --output-type category

# Output:
# Generated comments complete.
# Processed: 167, Failed: 2, Skipped: 0
```

### Purging and Regenerating

```bash
# Purge existing category outputs and regenerate with a better prompt
poetry run carchive gencom purge --output-type gencom_category
poetry run carchive gencom all --target-type message --min-word-count 20 --role assistant --output-type category \
    --prompt-template "Analyze the following content and provide ONE specific thematic category that best describes it. Be precise and specific with your category name. Focus on the subject matter, not the format. Avoid generic categories like 'Information' or 'Educational Content'. Instead, use more descriptive categories like 'Vector Embedding Optimization' or 'Philosophy of Mathematics': {content}"

# Output:
# Purged 167 gencom_category outputs.
# Generated comments complete.
# Processed: 167, Failed: 0, Skipped: 0
```

### Analyzing Category Distribution

```bash
# View category distribution as a table
poetry run carchive gencom categories --format table --exclude-generic

# Output:
# Category                                             | Total    | assistant
# ------------------------------------------------------------------
# Vector Index Creation and Optimization Process       | 12       | 12
# Philosophy of Mathematics                            | 8        | 8
# Quantum Computing Theory                             | 7        | 7
# ...
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

### Word-Limited Summaries

```bash
# Generate a concise summary with approximately 200 words
poetry run carchive gencom message 550e8400-e29b-41d4-a716-446655440000 \
    --prompt-template "Summarize the key points from this content: {content}" \
    --max-words 200 \
    --provider anthropic

# Output:
# Prompt template that will be used:
# ---
# Summarize the key points from this content: {content}
# 
# Please limit your response to approximately 200 words.
# ---
# Do you want to proceed with this prompt? [Y/n]: y
# Generated comment for message 550e8400-e29b-41d4-a716-446655440000 (AgentOutput ID: c1d5bf90-3893-4d1a-90d7-991102fa7321).
```

### Skipping Prompt Preview

```bash
# Skip the prompt preview and confirmation step
poetry run carchive gencom message 550e8400-e29b-41d4-a716-446655440000 \
    --prompt-template "Summarize the key points from this content: {content}" \
    --max-words 200 \
    --provider ollama \
    --no-preview-prompt

# Output:
# Generated comment for message 550e8400-e29b-41d4-a716-446655440000 (AgentOutput ID: f2d5bf90-3893-4d1a-90d7-991102fa8765).
```

## Best Practices

### Effective Prompt Design

1. **Always include the `{content}` placeholder** - This is where the actual content will be inserted
2. **Be specific in your instructions** - Clear instructions lead to more useful outputs
3. **Specify requirements** - For categories, ask for "ONE specific category" to avoid lists
4. **Provide examples** - Include examples of good outputs in your prompts
5. **Use appropriate word limits** - Limit summaries to an appropriate length for your use case

### Working with Categories

1. **Start with assistant messages** - These often contain more substantial content
2. **Use the purge command** to experiment with different prompts
3. **Exclude generic categories** with the `--exclude-generic` flag when analyzing results
4. **Visualize distribution** using the chart options to identify patterns
5. **Refine your category prompt** to get more specific, consistent categories

### Workflow Example

```bash
# Step 1: Generate initial categories
poetry run carchive gencom all --target-type message --min-word-count 20 --role assistant --output-type category

# Step 2: Analyze results
poetry run carchive gencom categories --format table

# Step 3: Purge if categories are too generic
poetry run carchive gencom purge --output-type gencom_category

# Step 4: Regenerate with improved prompt
poetry run carchive gencom all --target-type message --min-word-count 20 --role assistant --output-type category \
    --prompt-template "Analyze the following content and provide ONE specific thematic category that best describes it. Be precise and specific with your category name. Focus on the subject matter, not the format: {content}"

# Step 5: Visualize final results
poetry run carchive gencom categories --format chart --chart-type pie --exclude-generic
```