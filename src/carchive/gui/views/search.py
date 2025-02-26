"""
Search routes for the carchive2 GUI.
"""

import requests
from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash, jsonify
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('search', __name__, url_prefix='/search')

@bp.route('/')
def search_form():
    """Display search form."""
    return render_template('search/form.html')

@bp.route('/results')
def search_results():
    """Display search results."""
    # Get query parameters
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('search.search_form'))
    
    # TODO: Implement search results
    return render_template('search/results.html', query=query)