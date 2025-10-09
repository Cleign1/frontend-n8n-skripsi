# blueprints/__init__.py

def register_blueprints(app):
    """
    Initializes and registers all blueprints for the application.

    This function is called from the application factory in app.py.
    It imports each blueprint object and attaches it to the Flask app instance.
    """
    # Import the blueprint objects from their respective route files
    from .main.routes import main_bp
    from .upload.routes import upload_bp
    from .summary.routes import summary_bp
    from .tasks.routes import tasks_bp
    from .api.routes import api_bp
    from .chat.routes import chat_bp
    from .workflow.routes import workflow_bp

    # Register each blueprint with the Flask app instance
    app.register_blueprint(main_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(summary_bp)

    # It's good practice to give UI blueprints a unique name if their
    # module name ('tasks') might be confused with other variables.
    app.register_blueprint(tasks_bp, name='tasks_ui')

    # For the API, we add a URL prefix so all its routes
    # will start with /api (e.g., /api/status, /api/tasks)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(chat_bp)
    app.register_blueprint(workflow_bp)
