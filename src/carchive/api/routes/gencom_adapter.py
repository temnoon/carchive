"""
Flask adapter for gencom routes that were originally written in FastAPI.
This provides a compatibility layer while we transition to a fully Flask-based API.
"""

import json
import logging
from uuid import UUID
from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from carchive.api.routes.gencom import (
    GencomRequest, GencomResponse, 
    BatchGencomRequest, BatchGencomResponse,
    GencomPurgeRequest, GencomCategoryStats,
    GencomListResponse
)

# Configure logging
logger = logging.getLogger(__name__)

# Create Flask blueprint
bp = Blueprint('gencom', __name__, url_prefix='/api/gencom')

# Helper function to validate request data with Pydantic models
def validate_request_json(model_class):
    """Decorator to validate request JSON data using Pydantic models."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                # Parse JSON data
                data = request.json if request.is_json else {}
                
                # Validate with Pydantic model
                model_instance = model_class(**data)
                
                # Add validated model to kwargs
                kwargs['validated_data'] = model_instance
                
                # Call the actual function
                return func(*args, **kwargs)
            except ValidationError as e:
                logger.error(f"Validation error: {str(e)}")
                return jsonify({"detail": str(e)}), 422
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                return jsonify({"detail": str(e)}), 500
        
        # Preserve function's metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        
        return wrapper
    return decorator

# Route implementations that map to the original FastAPI endpoints
@bp.route('/generate', methods=['POST'])
@validate_request_json(GencomRequest)
def generate_comment(validated_data):
    """Generate an AI comment for a specific content item."""
    from carchive.api.routes.gencom import generate_comment as gencom_fastapi
    
    try:
        # Call the FastAPI route function directly
        response = gencom_fastapi(validated_data)
        return jsonify(response.dict())
    except Exception as e:
        logger.error(f"Error in generate_comment: {str(e)}")
        return jsonify({"detail": str(e)}), 500

@bp.route('/batch', methods=['POST'])
@validate_request_json(BatchGencomRequest)
def batch_generate_comments(validated_data):
    """Generate AI comments for multiple content items based on criteria."""
    from carchive.api.routes.gencom import batch_generate_comments as batch_fastapi
    
    try:
        # Call the FastAPI route function directly
        response = batch_fastapi(validated_data)
        return jsonify(response.dict())
    except Exception as e:
        logger.error(f"Error in batch_generate_comments: {str(e)}")
        return jsonify({"detail": str(e)}), 500

@bp.route('/purge', methods=['POST'])
@validate_request_json(GencomPurgeRequest)
def purge_gencom(validated_data):
    """Purge generated AI comments of a specific type."""
    from carchive.api.routes.gencom import purge_gencom as purge_fastapi
    
    try:
        # Call the FastAPI route function directly
        response = purge_fastapi(validated_data)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error in purge_gencom: {str(e)}")
        return jsonify({"detail": str(e)}), 500

@bp.route('/list', methods=['GET'])
def list_gencom():
    """List AI-generated comments matching the criteria."""
    from carchive.api.routes.gencom import list_gencom as list_fastapi
    
    try:
        # Extract query parameters
        output_type = request.args.get('output_type', 'gencom')
        target_type = request.args.get('target_type')
        target_id = request.args.get('target_id')
        include_target_content = request.args.get('include_target_content', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Convert target_id to UUID if present
        if target_id:
            target_id = UUID(target_id)
        
        # Call the FastAPI route function with extracted parameters
        response = list_fastapi(
            output_type=output_type,
            target_type=target_type,
            target_id=target_id,
            include_target_content=include_target_content,
            limit=limit,
            offset=offset
        )
        
        # Convert the response to JSON
        return jsonify([item.dict() for item in response])
    except Exception as e:
        logger.error(f"Error in list_gencom: {str(e)}")
        return jsonify({"detail": str(e)}), 500

@bp.route('/categories', methods=['GET'])
def list_categories():
    """List and analyze gencom category statistics."""
    from carchive.api.routes.gencom import list_categories as categories_fastapi
    
    try:
        # Extract query parameters
        target_type = request.args.get('target_type', 'message')
        output_type = request.args.get('output_type', 'gencom_category')
        min_count = int(request.args.get('min_count', 3))
        limit = int(request.args.get('limit', 20))
        exclude_generic = request.args.get('exclude_generic', 'false').lower() == 'true'
        role = request.args.get('role')
        
        # Call the FastAPI route function with extracted parameters
        response = categories_fastapi(
            target_type=target_type,
            output_type=output_type,
            min_count=min_count,
            limit=limit,
            exclude_generic=exclude_generic,
            role=role
        )
        
        # Convert the response to JSON
        return jsonify([item.dict() for item in response])
    except Exception as e:
        logger.error(f"Error in list_categories: {str(e)}")
        return jsonify({"detail": str(e)}), 500