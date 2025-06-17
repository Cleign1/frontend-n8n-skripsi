# make_celery.py
from app import create_app
from celery_app import celery

# By calling create_app(), we ensure that the init_celery() function
# runs. This modifies the 'celery' object that we imported from celery_app,
# making it aware of the Flask application context.
app = create_app()

# Now, when the Celery command line tool imports 'celery' from this file,
# it gets the fully configured instance.