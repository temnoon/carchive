# Carchive Agent System

This package provides a flexible system for interacting with various AI models and providers through a consistent interface.

## Architecture

The agent system is organized around different agent types and providers:

### Agent Types

- **Base Agents**: Common base classes that define interfaces
- **Embedding Agents**: Generate vector embeddings from text
- **Chat Agents**: Generate text responses through conversational interfaces
- **Content Agents**: Process content with specific tasks (summarization, analysis)
- **Multimodal Agents**: Handle multiple modalities (text, images, etc.)

### Providers

- **OpenAI**: Interface with OpenAI's API services
- **Ollama**: Interface with locally hosted models through Ollama
- **Anthropic**: Interface with Anthropic's Claude models
- **Local**: Direct interface with locally installed models

## Directory Structure

```
agents/
├── base/                  # Base agent classes
│   ├── agent.py           # Common base class
│   ├── embedding_agent.py # Base for embedding agents
│   ├── chat_agent.py      # Base for chat agents
│   ├── content_agent.py   # Base for content agents
│   └── multimodal_agent.py # Base for multimodal agents
├── providers/             # Provider-specific implementations
│   ├── openai/            # OpenAI implementations
│   ├── ollama/            # Ollama implementations
│   ├── anthropic/         # Anthropic implementations
│   └── local/             # Local model implementations
└── manager.py             # Agent factory
```

## Usage

### Basic Usage

```python
from carchive.agents import get_agent

# Get a chat agent using OpenAI
chat_agent = get_agent("chat", "openai")
response = chat_agent.chat("Hello, how are you?")

# Get an embedding agent using Ollama
embedding_agent = get_agent("embedding", "ollama")
vector = embedding_agent.generate_embedding("This is a sample text")

# Get a content agent for summarization
content_agent = get_agent("content", "ollama")
summary = content_agent.summarize("This is a long text that needs to be summarized...")

# Get a multimodal agent
multimodal_agent = get_agent("multimodal", "openai")
description = multimodal_agent.chat_with_images(
    "What's in this image?",
    ["path/to/image.jpg"]
)
```

### Using the Agent Manager

For more control, you can use the `AgentManager` directly:

```python
from carchive.agents.manager import AgentManager

manager = AgentManager()

# Get provider options for a specific agent type
providers = manager.available_providers("chat")
print(f"Available chat providers: {providers}")

# Get specific agent instances
embedding_agent = manager.get_embedding_agent("openai")
chat_agent = manager.get_chat_agent("anthropic")
content_agent = manager.get_content_agent("ollama")
```

## Extending the System

### Adding a New Provider

To add a new provider:

1. Create a new directory in `providers/` for your provider
2. Implement the necessary agent classes for your provider
3. Update the `AgentManager` class to include your new provider

### Adding a New Agent Type

To add a new agent type:

1. Create a new base class in `base/` defining the interface
2. Implement provider-specific versions in each provider directory
3. Update the `AgentManager` to handle the new agent type