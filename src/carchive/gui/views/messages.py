"""
Message routes for the carchive2 GUI.
"""

import requests
from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash, jsonify
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('messages', __name__, url_prefix='/messages')

@bp.route('/')
def list_messages():
    """List messages with pagination and filtering."""
    # TODO: Implement message listing
    return render_template('messages/list.html')

@bp.route('/<message_id>')
def view_message(message_id):
    """View a single message with its media."""
    # TODO: Implement message view
    return render_template('messages/view.html')