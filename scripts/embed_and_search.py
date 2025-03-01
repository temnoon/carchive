#!/usr/bin/env python
"""
Script to perform vector similarity search and generate summaries for found content.
"""

import argparse
import sys
import uuid
import numpy as np
from sqlalchemy import func
from typing import List

# Add the src directory to the Python path
sys.path.append(".")

from src.carchive.database.session import get_session
from src.carchive.database.models import Conversation, Message, Embedding
from src.carchive.agents.manager import AgentManager
from src.carchive.pipelines.content_tasks import ContentTaskManager

def embed_query(query_text: str, provider: str = "ollama", model_name: str = "nomic-embed-text") -> List[float]:
    """Generate an embedding for the query text using the specified provider and model."""
    agent_manager = AgentManager()
    embedding_agent = agent_manager.get_embedding_agent(provider)
    
    try:
        vector = embedding_agent.generate_embedding(query_text)
        print(f"Successfully generated embedding with dimensions: {len(vector)}")
        return vector
    except Exception as e:
        print(f"Error generating embedding: {e}")
        raise

def find_similar_conversations(query_vector: List[float], limit: int = 5) -> List[dict]:
    """Find conversations similar to the query vector using pgvector."""
    results = []
    with get_session() as session:
        # First try the direct method using parent_message_id
        try:
            similar_embeddings = (
                session.query(
                    Embedding,
                    Message,
                    Conversation
                )
                .join(Message, Embedding.parent_message_id == Message.id)
                .join(Conversation, Message.conversation_id == Conversation.id)
                .filter(Embedding.parent_message_id.isnot(None))
                .order_by(Embedding.vector.l2_distance(query_vector))
                .limit(limit)
                .all()
            )
            
            if similar_embeddings:
                print("Found embeddings with direct message links.")
            else:
                # If no results, fall back to using parent_id and parent_type
                print("No direct message links found, trying generic parent links...")
                similar_embeddings = (
                    session.query(
                        Embedding,
                        Message,
                        Conversation
                    )
                    .join(Message, Embedding.parent_id == Message.id)
                    .filter(Embedding.parent_type == 'message')
                    .join(Conversation, Message.conversation_id == Conversation.id)
                    .order_by(Embedding.vector.l2_distance(query_vector))
                    .limit(limit)
                    .all()
                )
        except Exception as e:
            print(f"Error with direct join: {e}")
            # Try the text search as a final fallback
            print("Using text similarity search based on your query...")
            
            # Find messages containing keywords from the query
            query_words = set(w.lower() for w in args.query.replace(".", "").replace(",", "").split() 
                             if len(w) > 3 and w.lower() not in ["that", "with", "this", "from", "there", "their", "have", "been"])
            query_pattern = "|".join(query_words)
            
            similar_messages = (
                session.query(Message, Conversation)
                .join(Conversation, Message.conversation_id == Conversation.id)
                .filter(Message.content.op("~*")(query_pattern))
                .limit(limit * 2)
                .all()
            )
            
            # Format results manually since we don't have embeddings
            for message, conversation in similar_messages:
                if conversation.id not in seen_conversation_ids:
                    seen_conversation_ids.add(conversation.id)
                    results.append({
                        "conversation_id": str(conversation.id),
                        "title": conversation.title,
                        "message_id": str(message.id),
                        "message_content": message.content[:500] + ("..." if len(message.content) > 500 else ""),
                        "note": "Found via text search (no embeddings available)"
                    })
                    
                    if len(results) >= limit:
                        break
            
            return results
        
        # Extract unique conversations
        seen_conversation_ids = set()
        for embedding, message, conversation in similar_embeddings:
            if conversation.id not in seen_conversation_ids:
                seen_conversation_ids.add(conversation.id)
                results.append({
                    "conversation_id": str(conversation.id),
                    "title": conversation.title,
                    "message_id": str(message.id),
                    "message_content": message.content[:500] + ("..." if len(message.content) > 500 else "")
                })
                
                if len(results) >= limit:
                    break
    
    return results

def generate_summary(conversation_id: str, max_words: int = 200) -> str:
    """Generate a summary for the conversation using the gencom functionality."""
    manager = ContentTaskManager(provider="ollama")
    prompt = f"Summarize the key points from this conversation in approximately {max_words} words, focusing on the main concepts and ideas presented:"
    
    try:
        output = manager.run_task_for_target(
            target_type="conversation",
            target_id=conversation_id,
            task="gencom",
            prompt_template=prompt
        )
        return output.content
    except Exception as e:
        print(f"Error generating summary: {e}")
        return "Failed to generate summary."

def main():
    parser = argparse.ArgumentParser(description="Find similar conversations and generate summaries based on semantic similarity.")
    parser.add_argument("query", help="The query text to search for")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of conversations to return")
    parser.add_argument("--provider", default="ollama", help="Provider for embeddings (default: ollama)")
    parser.add_argument("--model", default="nomic-embed-text", help="Model name for embeddings (default: nomic-embed-text)")
    parser.add_argument("--max-words", type=int, default=200, help="Maximum words for each summary")
    parser.add_argument("--summarize", action="store_true", help="Generate summaries for the found conversations")
    parser.add_argument("--text-only", action="store_true", help="Skip vector search and use text search only")
    
    global args
    args = parser.parse_args()
    
    print(f"Searching for conversations similar to: '{args.query}'")
    
    try:
        if not args.text_only:
            # Generate embedding for the query
            query_vector = embed_query(args.query, args.provider, args.model)
            
            # Find similar conversations
            similar_convs = find_similar_conversations(query_vector, args.limit)
        else:
            # Use text search only
            print("Using text search only (skipping vector similarity)...")
            with get_session() as session:
                seen_conversation_ids = set()
                similar_convs = []
                
                # Find messages containing keywords from the query
                query_words = set(w.lower() for w in args.query.replace(".", "").replace(",", "").split() 
                                if len(w) > 3 and w.lower() not in ["that", "with", "this", "from", "there", "their", "have", "been"])
                query_pattern = "|".join(query_words)
                
                if not query_pattern:
                    print("Query pattern is empty after filtering. Using original query.")
                    query_pattern = args.query
                
                print(f"Searching for pattern: {query_pattern}")
                similar_messages = (
                    session.query(Message, Conversation)
                    .join(Conversation, Message.conversation_id == Conversation.id)
                    .filter(Message.content.op("~*")(query_pattern))
                    .limit(args.limit * 2)
                    .all()
                )
                
                # Format results manually
                for message, conversation in similar_messages:
                    if conversation.id not in seen_conversation_ids:
                        seen_conversation_ids.add(conversation.id)
                        similar_convs.append({
                            "conversation_id": str(conversation.id),
                            "title": conversation.title,
                            "message_id": str(message.id),
                            "message_content": message.content[:500] + ("..." if len(message.content) > 500 else ""),
                            "note": "Found via text search"
                        })
                        
                        if len(similar_convs) >= args.limit:
                            break
        
        if not similar_convs:
            print("No similar conversations found.")
            return
        
        print(f"\nFound {len(similar_convs)} similar conversations:")
        
        for i, conv in enumerate(similar_convs, 1):
            print(f"\n{i}. {conv['title']} (ID: {conv['conversation_id']})")
            print(f"From message: {conv['message_id']}")
            print(f"Sample content: {conv['message_content'][:100]}...")
            
            if args.summarize:
                print("\nGenerating summary...")
                summary = generate_summary(conv['conversation_id'], args.max_words)
                print(f"\nSummary (max {args.max_words} words):\n{summary}")
                
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())