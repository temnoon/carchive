"""
API module for carchive2.
"""

from flask import Flask, jsonify
from flask_cors import CORS

def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    
    # Enable CORS for all routes and origins
    CORS(app)
    
    # Load configuration
    if test_config is None:
        app.config.from_mapping(
            SECRET_KEY='dev',
            JSON_SORT_KEYS=False,  # Preserve the order of JSON keys
            JSON_AS_ASCII=False,   # Support UTF-8
        )
    else:
        app.config.from_mapping(test_config)
    
    @app.route('/api/health')
    def health_check():
        """Health check endpoint."""
        return jsonify({'status': 'ok', 'version': '0.1.0'})
    
    @app.route('/api')
    def api_root():
        """API root endpoint."""
        return jsonify({
            'status': 'ok',
            'message': 'carchive API',
            'endpoints': [
                '/api/health',
                '/api/conversations',
                '/api/messages',
                '/api/media',
                '/api/search',
                '/api/collections',
                '/api/render',
                '/api/gencom',
                '/api/embeddings',
                '/api/clusters',
                '/api/cli'
            ]
        })
    
    # Register blueprints
    from carchive.api.routes.conversations import bp as conversations_bp
    from carchive.api.routes.messages import bp as messages_bp
    from carchive.api.routes.media import bp as media_bp
    from carchive.api.routes.search import bp as search_bp
    from carchive.api.routes.cli import bp as cli_bp
    from carchive.api.routes.collections import bp as collections_bp
    from carchive.api.routes.render import bp as render_bp
    from carchive.api.routes.gencom_adapter import gencom_bp
    from carchive.api.routes.embeddings import bp as embeddings_bp
    from carchive.api.routes.clusters import bp as clusters_bp
    
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
    
    return app