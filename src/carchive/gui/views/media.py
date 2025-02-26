"""
Media routes for the carchive2 GUI.
"""

import requests
from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash, jsonify
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('media', __name__, url_prefix='/media')

@bp.route('/')
def list_media():
    """List media files with pagination and filtering."""
    # TODO: Implement media listing
    return render_template('media/list.html')

@bp.route('/<media_id>')
def view_media(media_id):
    """View a single media file."""
    # TODO: Implement media view
    return render_template('media/view.html')