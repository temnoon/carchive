"""
API routes for embedding operations.
"""

import json
import logging
import uuid
from typing import List, Optional
from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import func, desc
from carchive.database.session import get_session, db_session
from carchive.database.models import Embedding, Message, AgentOutput
from carchive.embeddings.embed_manager import EmbeddingManager
from carchive.embeddings.schemas import (
    EmbeddingRequestSchema,
    EmbeddingTargetSchema,
    EmbedAllOptions
)

logger = logging.getLogger(__name__)

bp = Blueprint("embeddings", __name__, url_prefix="/api/embeddings")


@bp.route("/", methods=["GET"])
@db_session
def list_embeddings(session):
    """Get a paginated list of embeddings."""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        provider = request.args.get("provider")
        model = request.args.get("model")
        
        query = session.query(Embedding)
        
        if provider:
            query = query.filter(Embedding.model_name == provider)
        
        if model:
            query = query.filter(Embedding.model_version == model)
        
        # Count total results
        total = query.count()
        
        # Paginate results
        query = query.order_by(desc(Embedding.created_at))
        query = query.limit(per_page).offset((page - 1) * per_page)
        
        embeddings = query.all()
        
        # Convert to dictionary representation
        result = []
        for emb in embeddings:
            # Don't include the full vector in the listing to reduce response size
            emb_dict = {
                "id": str(emb.id),
                "model_name": emb.model_name,
                "model_version": emb.model_version,
                "dimensions": emb.dimensions,
                "created_at": emb.created_at.isoformat() if emb.created_at else None,
                "updated_at": emb.updated_at.isoformat() if emb.updated_at else None,
                "parent_type": getattr(emb, "parent_type", None),
                "parent_id": str(emb.parent_id) if getattr(emb, "parent_id", None) else None,
                "parent_message_id": str(emb.parent_message_id) if emb.parent_message_id else None,
                "meta_info": emb.meta_info
            }
            result.append(emb_dict)
        
        return jsonify({
            "embeddings": result,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        })
    except Exception as e:
        logger.error(f"Error listing embeddings: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/", methods=["POST"])
@db_session
def create_embeddings(session):
    """Generate embeddings for text or database items."""
    try:
        data = request.json

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Check if this is a raw text embedding request
        if "text" in data:
            # Handle simple text embedding
            texts = [data["text"]] if isinstance(data["text"], str) else data["text"]
            provider = data.get("provider")
            model = data.get("model")
            
            # Create embeddings
            embedding_manager = EmbeddingManager()
            embeddings = embedding_manager.embed_texts(
                texts=texts,
                provider=provider,
                model_version=model,
                store_in_db=True
            )
            
            # Return embedding IDs
            return jsonify({
                "status": "success",
                "message": f"Generated {len(embeddings)} embeddings",
                "embedding_ids": [str(emb.id) for emb in embeddings]
            })
        
        # Check if this is a batch embedding request with messages
        elif "message_ids" in data:
            # Handle message embedding
            message_ids = data["message_ids"]
            provider = data.get("provider")
            model = data.get("model")
            
            # Create embedding targets
            targets = [
                EmbeddingTargetSchema(message_id=msg_id)
                for msg_id in message_ids
            ]
            
            # Create embeddings
            embedding_manager = EmbeddingManager()
            request_data = EmbeddingRequestSchema(
                provider=provider,
                model_version=model,
                store_in_db=True,
                targets=targets
            )
            
            results = embedding_manager.embed_texts_schema(request_data)
            
            return jsonify({
                "status": "success",
                "message": f"Generated {len(results)} embeddings",
                "results": [r.dict() for r in results]
            })
        
        # Check if this is an "embed all" request
        elif "embed_all" in data:
            # Parse the options
            options_data = data.get("options", {})
            options = EmbedAllOptions(
                min_word_count=options_data.get("min_word_count", 5),
                exclude_empty=options_data.get("exclude_empty", True),
                include_roles=options_data.get("include_roles", ["user", "assistant"])
            )
            
            provider = data.get("provider")
            model = data.get("model")
            
            # Run the embed_all operation as a background task
            # For now, we'll run it synchronously
            embedding_manager = EmbeddingManager()
            count = embedding_manager.embed_all_messages(
                options=options,
                provider=provider,
                model_version=model,
                store_in_db=True
            )
            
            return jsonify({
                "status": "success",
                "message": f"Embedded {count} messages",
                "count": count
            })
        
        else:
            return jsonify({"error": "Invalid request format"}), 400
            
    except Exception as e:
        logger.error(f"Error creating embeddings: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/<embedding_id>", methods=["GET"])
@db_session
def get_embedding(session, embedding_id):
    """Get details for a specific embedding."""
    try:
        embedding = session.query(Embedding).filter_by(id=embedding_id).first()
        
        if not embedding:
            return jsonify({"error": "Embedding not found"}), 404
        
        # Get associated message if available
        message = None
        if embedding.parent_message_id:
            message = session.query(Message).filter_by(id=embedding.parent_message_id).first()
        
        # Format the response
        result = {
            "id": str(embedding.id),
            "model_name": embedding.model_name,
            "model_version": embedding.model_version,
            "dimensions": embedding.dimensions,
            "created_at": embedding.created_at.isoformat() if embedding.created_at else None,
            "updated_at": embedding.updated_at.isoformat() if embedding.updated_at else None,
            "parent_type": getattr(embedding, "parent_type", None),
            "parent_id": str(embedding.parent_id) if getattr(embedding, "parent_id", None) else None,
            "parent_message_id": str(embedding.parent_message_id) if embedding.parent_message_id else None,
            "meta_info": embedding.meta_info,
            "vector": embedding.vector,  # Include the full vector
        }
        
        # Include message details if available
        if message:
            result["message"] = {
                "id": str(message.id),
                "conversation_id": str(message.conversation_id) if message.conversation_id else None,
                "role": message.role,
                "author_name": message.author_name,
                "content_preview": message.content[:200] + "..." if message.content and len(message.content) > 200 else message.content,
                "created_at": message.created_at.isoformat() if message.created_at else None
            }
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting embedding {embedding_id}: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/<embedding_id>", methods=["DELETE"])
@db_session
def delete_embedding(session, embedding_id):
    """Delete a specific embedding."""
    try:
        embedding = session.query(Embedding).filter_by(id=embedding_id).first()
        
        if not embedding:
            return jsonify({"error": "Embedding not found"}), 404
        
        session.delete(embedding)
        session.commit()
        
        return jsonify({
            "status": "success",
            "message": f"Embedding {embedding_id} deleted"
        })
    except Exception as e:
        logger.error(f"Error deleting embedding {embedding_id}: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/status", methods=["GET"])
@db_session
def get_embedding_status(session):
    """Get statistics about embeddings."""
    try:
        # Count total embeddings
        total_count = session.query(func.count(Embedding.id)).scalar()
        
        # Count by provider
        provider_counts = session.query(
            Embedding.model_name,
            func.count(Embedding.id)
        ).group_by(Embedding.model_name).all()
        
        # Count by model version
        model_counts = session.query(
            Embedding.model_version,
            func.count(Embedding.id)
        ).group_by(Embedding.model_version).all()
        
        # Count by dimensions
        dimension_counts = session.query(
            Embedding.dimensions,
            func.count(Embedding.id)
        ).group_by(Embedding.dimensions).all()
        
        # Count by parent type
        try:
            # First try to query using parent_type if it exists
            parent_type_counts = session.query(
                Embedding.parent_type,
                func.count(Embedding.id)
            ).group_by(Embedding.parent_type).all()
        except Exception:
            # Fallback to message/chunk counts
            message_count = session.query(func.count(Embedding.id)).filter(
                Embedding.parent_message_id.isnot(None)
            ).scalar()
            
            parent_type_counts = [("message", message_count)]
        
        return jsonify({
            "total_embeddings": total_count,
            "by_provider": {p: c for p, c in provider_counts},
            "by_model": {m: c for m, c in model_counts},
            "by_dimensions": {d: c for d, c in dimension_counts},
            "by_parent_type": {t if t else "unknown": c for t, c in parent_type_counts}
        })
    except Exception as e:
        logger.error(f"Error getting embedding status: {e}")
        return jsonify({"error": str(e)}), 500