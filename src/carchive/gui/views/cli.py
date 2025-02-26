"""
CLI command execution routes for the carchive2 GUI.
"""

import requests
import json
from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash, jsonify
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('cli', __name__, url_prefix='/cli')

@bp.route('/')
def cli_dashboard():
    """CLI commands dashboard."""
    api_url = current_app.config['API_URL']
    
    # Get available commands from API
    try:
        response = requests.get(f"{api_url}/api/cli/commands", timeout=10)
        if response.status_code == 200:
            commands = response.json().get('commands', [])
        else:
            flash(f"Error retrieving CLI commands: {response.status_code}", "error")
            commands = []
    except requests.RequestException as e:
        logger.error(f"Error connecting to API: {str(e)}")
        flash(f"Error connecting to API: {str(e)}", "error")
        commands = []
    
    return render_template(
        'cli/dashboard.html',
        commands=commands
    )

@bp.route('/execute', methods=['POST'])
def execute_command():
    """Execute a CLI command."""
    api_url = current_app.config['API_URL']
    
    # Get command from form
    command = request.form.get('command', '')
    if not command:
        return jsonify({
            'success': False,
            'error': 'No command provided'
        })
    
    # Execute command via API
    try:
        response = requests.post(
            f"{api_url}/api/cli/execute",
            json={'command': command},
            timeout=60
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'success': False,
                'error': f"API returned status code {response.status_code}",
                'details': response.text
            })
    except requests.RequestException as e:
        logger.error(f"Error connecting to API: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Error connecting to API: {str(e)}"
        })