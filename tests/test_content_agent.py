# tests/test_content_agent.py

import logging
from carchive.agents.providers.ollama.content_agent import OllamaContentAgent

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def test_direct_content_agent():
    """
    Test the ContentAgent directly with a text string input.
    """
    # Sample text to process
    test_text = "This is a lengthy text that discusses important philosophical concepts. The text delves into the nature of consciousness and reality. It examines how perception shapes our understanding of the world around us. Some key points include the relationship between mind and matter, the subjective nature of experience, and the role of language in constructing reality. The author argues that consciousness is fundamental to existence and not merely an emergent property of physical processes."
    
    # Initialize the ContentAgent
    agent = OllamaContentAgent(model_name="llama3.2")
    
    # Process the text directly using the gencom task
    result = agent.process_task(
        task="gencom",
        content=test_text,
        prompt_template="Please provide a thoughtful analysis of the following text:\n\n{content}"
    )
    
    logger.info(f"Generated comment: {result}")
    return result

if __name__ == "__main__":
    test_direct_content_agent()