"""
API endpoints for executing CLI commands.
"""

import subprocess
import json
import os
from typing import Dict, List, Optional, Any
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.orm import Session

from carchive.database.session import get_session
from carchive.api.routes.utils import db_session, error_response
from carchive.cli.main_cli import main_app

bp = Blueprint('cli', __name__, url_prefix='/api/cli')

@bp.route('/commands', methods=['GET'])
def get_available_commands():
    """Get a list of available CLI commands."""
    commands = []
    
    # Extract commands from Typer app
    for command_name, command in main_app.registered_commands.items():
        commands.append({
            'name': command_name,
            'help': command.help or command.callback.__doc__ or "No help available",
            'params': [
                {
                    'name': param.name,
                    'type': str(param.type),
                    'required': param.required,
                    'default': param.default if not callable(param.default) else None,
                    'help': param.help
                }
                for param in command.params
            ]
        })
    
    # Extract subcommands from Typer app
    for group_name, group in main_app.registered_groups.items():
        subcommands = []
        for subcommand_name, subcommand in group.typer_instance.registered_commands.items():
            subcommands.append({
                'name': subcommand_name,
                'help': subcommand.help or subcommand.callback.__doc__ or "No help available",
                'params': [
                    {
                        'name': param.name,
                        'type': str(param.type),
                        'required': param.required,
                        'default': param.default if not callable(param.default) else None,
                        'help': param.help
                    }
                    for param in subcommand.params
                ]
            })
        
        commands.append({
            'name': group_name,
            'help': group.help or "No help available",
            'subcommands': subcommands
        })
    
    return jsonify({
        'commands': commands
    })

@bp.route('/execute', methods=['POST'])
def execute_command():
    """Execute a CLI command."""
    try:
        data = request.json
        if not data:
            return error_response(400, "Request must include JSON body with command")
        
        command = data.get('command')
        if not command:
            return error_response(400, "Missing required parameter: command")
        
        # Convert command to list format for subprocess
        if isinstance(command, str):
            command_parts = ['python', '-m', 'carchive2.cli.main_cli'] + command.split()
        elif isinstance(command, list):
            command_parts = ['python', '-m', 'carchive2.cli.main_cli'] + command
        else:
            return error_response(400, "Command must be a string or array")
        
        # Execute command using subprocess
        try:
            env = os.environ.copy()
            env['PYTHONPATH'] = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            result = subprocess.run(
                command_parts,
                capture_output=True,
                text=True,
                check=False,
                env=env
            )
            
            # Prepare response
            response = {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'exit_code': result.returncode,
                'success': result.returncode == 0
            }
            
            # Try to parse output as JSON if possible
            if result.stdout.strip() and result.stdout.strip()[0] in '{[':
                try:
                    parsed_output = json.loads(result.stdout)
                    response['parsed_output'] = parsed_output
                except json.JSONDecodeError:
                    pass
            
            return jsonify(response)
        
        except Exception as e:
            current_app.logger.error(f"Error executing CLI command: {str(e)}")
            return error_response(500, f"Error executing command: {str(e)}")
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return error_response(500, f"Unexpected error: {str(e)}")