"""
CLI command execution routes for the carchive GUI.
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
    api_url = current_app.config.get('API_URL', 'http://localhost:8000')
    api_base_url = current_app.config.get('API_BASE_URL', f"{api_url}/api")
    
    # Get available commands from API
    try:
        response = requests.get(f"{api_base_url}/cli/commands", timeout=10)
        if response.status_code == 200:
            commands = response.json().get('commands', [])
        else:
            logger.error(f"Error retrieving CLI commands: {response.status_code} - {response.text}")
            flash(f"Error retrieving CLI commands: {response.status_code}", "danger")
            commands = []
    except requests.RequestException as e:
        logger.error(f"Error connecting to API: {str(e)}")
        flash(f"Error connecting to API: {str(e)}", "danger")
        commands = []
    
    return render_template(
        'cli/dashboard.html',
        commands=commands
    )

@bp.route('/execute', methods=['POST'])
def execute_command():
    """Execute a CLI command."""
    api_url = current_app.config.get('API_URL', 'http://localhost:8000')
    api_base_url = current_app.config.get('API_BASE_URL', f"{api_url}/api")
    
    # Get command from form
    command = request.form.get('command', '')
    if not command:
        return jsonify({
            'success': False,
            'error': 'No command provided'
        })
    
    # Execute command via API
    try:
        logger.info(f"Executing CLI command: {command}")
        response = requests.post(
            f"{api_base_url}/cli/execute",
            json={'command': command},
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Command executed successfully with exit code: {result.get('exit_code', 0)}")
            return jsonify(result)
        else:
            logger.error(f"API returned status code {response.status_code}: {response.text}")
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