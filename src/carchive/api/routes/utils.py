"""
Utility functions for API routes.
"""

from functools import wraps
from typing import Callable, Any, Dict, List, Optional, Tuple, TypeVar, Union
import uuid
from datetime import datetime, timedelta

from flask import request, jsonify, Response, current_app
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from carchive.database.session import get_session

T = TypeVar('T')

def validate_uuid(uuid_string: str) -> bool:
    """Validate that a string is a valid UUID."""
    try:
        uuid_obj = uuid.UUID(uuid_string)
        return str(uuid_obj) == uuid_string
    except (ValueError, AttributeError):
        return False


def parse_pagination_params() -> Tuple[int, int]:
    """Parse pagination parameters from request."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Ensure reasonable values
    page = max(1, page)
    per_page = max(1, min(100, per_page))
    
    return page, per_page


def paginate_query(query, page: int, per_page: int) -> Tuple[List[Any], int]:
    """Paginate SQLAlchemy query results."""
    total = query.count()
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    return items, total


def error_response(status_code: int, message: str, details: Optional[Dict[str, Any]] = None) -> Response:
    """Create a standardized error response."""
    response = {
        'error': message,
        'code': status_code
    }
    if details:
        response['details'] = details
    
    return jsonify(response), status_code


def db_session(f: Callable[..., T]) -> Callable[..., T]:
    """Decorator that provides a database session to the route."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        with get_session() as session:
            try:
                return f(*args, session=session, **kwargs)
            except HTTPException as e:
                # Let Flask handle HTTP exceptions
                raise
            except SQLAlchemyError as e:
                current_app.logger.error(f"Database error: {str(e)}")
                return error_response(500, "Database error occurred", 
                                     {"detail": str(e)})
            except Exception as e:
                current_app.logger.error(f"Unexpected error: {str(e)}")
                return error_response(500, "An unexpected error occurred", 
                                     {"detail": str(e) if current_app.debug else None})
    return wrapper