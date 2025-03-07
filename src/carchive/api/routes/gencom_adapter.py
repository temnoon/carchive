"""
Adapter for the gencom API routes.

This module adapts the FastAPI-based gencom router to work with Flask.
"""

from flask import Blueprint, request, jsonify
from carchive.database.session import get_session, db_session
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Create Flask blueprint
gencom_bp = Blueprint("gencom", __name__, url_prefix="/api/gencom")

@gencom_bp.route("/", methods=["GET"])
@db_session
def gencom_root(session):
    """Root endpoint for gencom API"""
    return jsonify({
        "message": "Gencom API - Use endpoints: /generate, /batch, /list, /categories, /purge",
        "status": "active"
    })

@gencom_bp.route("/generate", methods=["POST"])
@db_session
def generate_comment(session):
    """Generate an AI comment for a specific content item"""
    try:
        # Load necessary modules here to avoid circular imports
        from carchive.pipelines.content_tasks import ContentTaskManager
        
        # Get request data
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        # Extract parameters
        target_type = data.get("target_type")
        target_id = data.get("target_id")
        output_type = data.get("output_type", "gencom")
        provider = data.get("provider", "ollama")
        prompt_template = data.get("prompt_template")
        max_words = data.get("max_words")
        max_tokens = data.get("max_tokens")
        override = data.get("override", False)
        generate_embedding = data.get("generate_embedding", False)
        embedding_provider = data.get("embedding_provider")
        
        # Validate required parameters
        if not target_type or not target_id:
            return jsonify({"error": "Missing required parameters"}), 400
            
        # Create content task manager
        manager = ContentTaskManager(provider=provider)
        
        # Run the task
        output = manager.run_task_for_target(
            target_type=target_type,
            target_id=str(target_id),
            task=output_type,
            prompt_template=prompt_template,
            override=override,
            max_words=max_words,
            max_tokens=max_tokens
        )
        
        # Generate embedding if requested
        if generate_embedding:
            from carchive.embeddings.embed_manager import EmbeddingManager
            embed_provider = embedding_provider or provider
            embedding_manager = EmbeddingManager(provider=embed_provider)
            
            # Generate embedding for the gencom content
            embedding = embedding_manager.embed_texts(
                texts=[output.content],
                parent_ids=[str(output.id)],
                parent_type="agent_output"
            )
            logger.info(f"Generated embedding for comment (Embedding ID: {embedding[0].id})")
        
        # Return response
        return jsonify({
            "id": str(output.id),
            "target_type": output.target_type,
            "target_id": str(output.target_id),
            "output_type": output.output_type,
            "content": output.content,
            "agent_name": output.agent_name,
            "created_at": output.created_at.isoformat() if output.created_at else None
        })
        
    except Exception as e:
        logger.error(f"Error generating comment: {e}")
        return jsonify({"error": str(e)}), 500

@gencom_bp.route("/list", methods=["GET"])
@db_session
def list_gencom(session):
    """List AI-generated comments matching the criteria"""
    try:
        from carchive.database.models import AgentOutput, Message, Conversation, Chunk
        
        # Get query parameters
        output_type = request.args.get("output_type", "gencom")
        target_type = request.args.get("target_type")
        target_id = request.args.get("target_id")
        include_target_content = request.args.get("include_target_content", "false").lower() == "true"
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        
        # Build base query
        query = session.query(AgentOutput).filter(
            AgentOutput.output_type == output_type
        )
        
        # Apply filters
        if target_type:
            query = query.filter(AgentOutput.target_type == target_type)
            
        if target_id:
            query = query.filter(AgentOutput.target_id == target_id)
            
        # Apply pagination
        query = query.order_by(AgentOutput.created_at.desc())
        query = query.offset(offset).limit(limit)
        
        results = query.all()
        
        # Prepare response
        response = []
        for result in results:
            item = {
                "id": str(result.id),
                "target_type": result.target_type,
                "target_id": str(result.target_id),
                "output_type": result.output_type,
                "content": result.content,
                "agent_name": result.agent_name,
                "created_at": result.created_at.isoformat() if result.created_at else None,
                "target_content": None
            }
            
            # Add target content if requested
            if include_target_content:
                target_content = None
                if result.target_type == "message":
                    message = session.query(Message).filter_by(id=result.target_id).first()
                    if message:
                        target_content = message.content
                elif result.target_type == "conversation":
                    # For conversations, get title as content
                    conversation = session.query(Conversation).filter_by(id=result.target_id).first()
                    if conversation:
                        target_content = conversation.title
                elif result.target_type == "chunk":
                    chunk = session.query(Chunk).filter_by(id=result.target_id).first()
                    if chunk:
                        target_content = chunk.content
                        
                item["target_content"] = target_content
            
            response.append(item)
            
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error listing gencom: {e}")
        return jsonify({"error": str(e)}), 500