# db_setup.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy import MetaData

# 1. Initialize SQLAlchemy
db = SQLAlchemy()

# 2. Create the 'automap' base
# This object will hold our auto-discovered tables
metadata = MetaData(schema="public")
Base = automap_base()

def init_db_and_models(app):
    """
    Initializes the db connection and reflects all tables.
    """
    # Connect Flask-SQLAlchemy to the app
    db.init_app(app)
    
    # Inside an app context, reflect the database
    with app.app_context():
        # This is the magic part:
        # It connects to your DB, reads all table schemas,
        # and creates model classes for them in Base.classes
        Base.prepare(db.engine)