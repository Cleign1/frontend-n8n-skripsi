# introduction

ini adalah front end untuk n8n skripsi saya.

## for starting the flask app

```bash
flask --app app --debug run
```

running celery worker command

```bash
celery -A make_celery.celery worker --loglevel=info --pool=solo -n worker1@%h
```

## Using UV now

### 1. Create the environment
```bash
uv venv
```

### 2. Activate it
```bash
source .venv/bin/activate
```

### 3. Install all packages from the lock file
```bash
uv pip sync requirements.txt
```

## Docker Prequisites

### 1. Create volume
```bash
docker volume create fe-n8n
```
### 2. Create network
```bash
docker network create --subnet=10.0.0.0/24 fe-n8n-network
```
### 3. Create volumes
```bash
docker volume create fe-n8n && docker volume create redis-n8n-data
```

