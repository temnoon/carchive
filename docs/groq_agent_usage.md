# Using the Groq Agent with Carchive

This document explains how to set up and use the Groq agent with Carchive for fast LLM responses.

## Setup

1. Install the Groq Python package:
   ```bash
   ./install_groq.sh
   ```

2. Set your Groq API key as an environment variable:
   ```bash
   export GROQ_API_KEY=your_api_key_here
   ```

3. Verify the installation by running the test script:
   ```bash
   python tests/test_groq_agent.py
   ```

## Available Models

Groq offers several models with exceptional speed:

- `llama-3.2-3b-preview` - Default model for the agent (small, very fast)
- `llama-3.2-8b-instant` - Slightly larger model with better quality
- `llama-3.2-70b-versatile` - Full-sized model with best quality
- `llama-3.2-1b-preview` - The smallest, fastest model
- `mixtral-8x7b-instruct` - Alternative architecture with good performance

To change the model, modify the `provider_config` in `AgentManager` or provide it when creating the agent directly.

## Using Groq Agent in Your Code

```python
from carchive.agents.manager import AgentManager

# Create the agent manager
manager = AgentManager()

# Get a Groq chat agent
chat_agent = manager.get_chat_agent("groq")

# Generate a response
response = chat_agent.chat("Tell me about vector databases")
print(response)

# Get a Groq content agent
content_agent = manager.get_content_agent("groq")

# Summarize text
summary = content_agent.summarize(long_text)
print(summary)

# Process other content tasks
analysis = content_agent.process_task("analyze", content_text)
```

## Changing the Default Model

To use a different model, you can customize the agent configuration:

```python
from src.carchive.agents.providers.groq.chat_agent import GroqChatAgent

# Create a Groq agent with a specific model
agent = GroqChatAgent(
    api_key="your_api_key",
    model_name="llama-3.2-70b-versatile",
    temperature=0.5
)

response = agent.chat("Tell me about vector databases")
```

## Performance

The Groq API is designed for speed. You should see response times in the milliseconds to low seconds range, depending on the model size and complexity of the prompt.

For optimal performance:
1. Use the smallest model suitable for your task
2. Keep prompts concise and focused
3. Use simple questions for the fastest responses

## Troubleshooting

If you encounter issues:

1. Check your API key is correctly set in the environment
2. Verify you have installed the groq package (v0.4.1 or newer)
3. Ensure your internet connection is stable
4. Check the Groq status page if you experience service disruptions