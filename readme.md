# introduction

ini adalah front end untuk n8n skripsi saya.

for starting the flask app

```flask --app app --debug run```

running celery worker command

```celery -A make_celery.celery worker --loglevel=info --pool=solo -n worker1@%h```

Using UV now

### 1. Create the environment
uv venv

### 2. Activate it
source .venv/bin/activate

### 3. Install all packages from the lock file
uv pip sync requirements.txt