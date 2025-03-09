#\!/usr/bin/env python
"""
A script to store embeddings directly to a file.
This allows processing to continue even when database storage fails.
"""
import uuid
import json
import argparse
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description="Store embeddings in JSON file")
    parser.add_argument("--min-word-count", type=int, default=7, 
                        help="Minimum word count for embedding messages")
    parser.add_argument("--output", type=str, default="embeddings_output.jsonl",
                        help="Output file for embeddings")
    parser.add_argument("--batch-size", type=int, default=100,
                        help="Batch size for processing")
    args = parser.parse_args()
    
    from carchive.embeddings.schemas import EmbedAllOptions
    from carchive.embeddings.embed_manager import EmbeddingManager
    from carchive.database.session import get_session
    from carchive.database.models import Message
    from sqlalchemy import func
    import logging
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger("store_embeddings")
    
    # Initialize the embedding manager
    manager = EmbeddingManager()
    
    with get_session() as session:
        # Get message IDs that meet criteria
        word_count_expr = func.array_length(
            func.regexp_split_to_array(Message.content, r'\s+'), 1
        )
        
        query = session.query(Message.id).filter(
            Message.content.isnot(None),
            Message.content \!= "",
            word_count_expr > args.min_word_count
        )
        
        message_ids = [str(row[0]) for row in query.all()]
        logger.info(f"Found {len(message_ids)} messages to process")
        
        # Process in batches and store to file
        output_file = args.output
        
        with open(output_file, 'w') as f:
            for i in range(0, len(message_ids), args.batch_size):
                batch = message_ids[i:i+args.batch_size]
                logger.info(f"Processing batch {i//args.batch_size + 1} of {(len(message_ids) + args.batch_size - 1)//args.batch_size}")
                
                # Get messages for this batch
                messages = session.query(Message).filter(Message.id.in_(batch)).all()
                
                for msg in messages:
                    try:
                        # Get embedding vector
                        text = msg.content or ""
                        if not text.strip():
                            continue
                            
                        from carchive.agents.manager import AgentManager
                        agent = AgentManager().get_embedding_agent("ollama")
                        vector = agent.generate_embedding(text)
                        
                        # Create a record
                        record = {
                            "id": str(uuid.uuid4()),
                            "message_id": str(msg.id),
                            "model_name": "ollama",
                            "model_version": "nomic-embed-text",
                            "dimensions": len(vector),
                            "vector": vector,
                            "created_at": datetime.now().isoformat(),
                            "meta_info": {"source": "direct_file"}
                        }
                        
                        # Write to file
                        f.write(json.dumps(record) + "\n")
                        f.flush()  # Ensure it's written even if interrupted
                    except Exception as e:
                        logger.error(f"Error processing message {msg.id}: {e}")
                
                logger.info(f"Completed batch {i//args.batch_size + 1}")
        
        logger.info(f"Embeddings saved to {output_file}")

if __name__ == "__main__":
    main()
