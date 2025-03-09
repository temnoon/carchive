"""
GUI module for carchive.
"""

import os
import logging
from flask import Flask, render_template, url_for, redirect, flash, request
from flask_cors import CORS

logger = logging.getLogger(__name__)

def create_app(test_config=None):
    """Create and configure the Flask web application."""
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder='templates',
        static_folder='static'
    )
    
    # Enable CORS
    CORS(app)
    
    # Load configuration
    if test_config is None:
        # Import settings from config
        from carchive.core.config import API_URL, API_BASE_URL, CORS_ENABLED
        
        app.config.from_mapping(
            SECRET_KEY='dev',
            API_URL=API_URL,  # URL for the API server
            API_BASE_URL=API_BASE_URL,  # Base URL for API endpoints
            SESSION_TYPE='filesystem',
            SESSION_PERMANENT=False,
            SESSION_USE_SIGNER=True,
            DEBUG=os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1', 't'],
            CORS_ENABLED=CORS_ENABLED
        )
        # Log the configuration
        app.logger.info(f"GUI configured with API_URL: {API_URL}")
        app.logger.info(f"GUI configured with API_BASE_URL: {API_BASE_URL}")
    else:
        app.config.from_mapping(test_config)
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Register blueprints
    from carchive.gui.views.main import bp as main_bp
    from carchive.gui.views.conversations import bp as conversations_bp
    from carchive.gui.views.messages import bp as messages_bp
    from carchive.gui.views.media import bp as media_bp
    from carchive.gui.views.search import bp as search_bp
    from carchive.gui.views.cli import bp as cli_bp
    from carchive.gui.views.collections import bp as collections_bp
    from carchive.gui.views.render import bp as render_bp
    from carchive.gui.views.gencom import bp as gencom_bp
    from carchive.gui.views.embeddings import bp as embeddings_bp
    from carchive.gui.views.clusters import bp as clusters_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(conversations_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(media_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(cli_bp)
    app.register_blueprint(collections_bp)
    app.register_blueprint(render_bp)
    app.register_blueprint(gencom_bp)
    app.register_blueprint(embeddings_bp)
    app.register_blueprint(clusters_bp)
    
    @app.errorhandler(404)
    def page_not_found(e):
        """Handle 404 errors."""
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        """Handle 500 errors."""
        logger.error(f"Server error: {str(e)}")
        return render_template('500.html'), 500
    
    @app.context_processor
    def utility_processor():
        """Add utilities to template context."""
        return {
            'app_name': 'Carchive Explorer'
        }
    
    @app.template_filter('datetime')
    def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
        """Format a datetime object."""
        if value is None:
            return ""
        if isinstance(value, str):
            try:
                from datetime import datetime
                # Try to parse ISO format
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                return value
        return value.strftime(format)
    
    return app