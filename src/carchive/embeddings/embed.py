"""
Handles embedding generation and storage in the DB, using agents for model calls.
"""

from typing import Optional
import uuid
import datetime

from carchive.database.session import get_session
from carchive.database.models import Embedding
from carchive.agents.manager import AgentManager

def embed_text(text: str, provider: str = "ollama", model_version: str = "nomic-embed-text"):
    """
    Example function that uses an agent to generate an embedding and stores it.
    """
    agent = AgentManager().get_agent(provider)
    vector = agent.generate_embedding(text)
    if not vector:
        return None

    with get_session() as session:
        emb_obj = Embedding(
            id=uuid.uuid4(),
            model_name=provider,
            model_version=model_version,
            dimensions=len(vector),
            vector=vector,
            created_at=datetime.datetime.utcnow(),
            meta_info={"source": text}
        )
        session.add(emb_obj)
        session.commit()
        session.refresh(emb_obj)
        return emb_obj
