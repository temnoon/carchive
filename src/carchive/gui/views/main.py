"""
Main routes for the carchive2 GUI.
"""

import requests
from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash, jsonify
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('main', __name__, url_prefix='/')

@bp.route('/')
def index():
    """Home page."""
    # Get API health status
    try:
        api_url = current_app.config['API_URL']
        response = requests.get(f"{api_url}/api/health", timeout=2)
        if response.status_code == 200:
            api_status = True
            api_info = response.json()
        else:
            api_status = False
            api_info = {'error': f"API returned status code {response.status_code}"}
    except requests.RequestException as e:
        logger.error(f"Error connecting to API: {str(e)}")
        api_status = False
        api_info = {'error': f"Cannot connect to API: {str(e)}"}
    
    # Get basic stats
    stats = {}
    if api_status:
        # Get conversation count
        try:
            response = requests.get(f"{api_url}/api/conversations?per_page=1", timeout=5)
            if response.status_code == 200:
                stats['conversations'] = response.json().get('pagination', {}).get('total', 0)
        except requests.RequestException:
            stats['conversations'] = "Error"
        
        # Get message count
        try:
            response = requests.get(f"{api_url}/api/messages?per_page=1", timeout=5)
            if response.status_code == 200:
                stats['messages'] = response.json().get('pagination', {}).get('total', 0)
        except requests.RequestException:
            stats['messages'] = "Error"
            
        # Get media count
        try:
            response = requests.get(f"{api_url}/api/media?per_page=1", timeout=5)
            if response.status_code == 200:
                stats['media'] = response.json().get('pagination', {}).get('total', 0)
        except requests.RequestException:
            stats['media'] = "Error"
    
    return render_template(
        'index.html',
        api_status=api_status,
        api_info=api_info,
        stats=stats
    )

@bp.route('/about')
def about():
    """About page."""
    return render_template('about.html')