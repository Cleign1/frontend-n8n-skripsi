# introduction

ini adalah front end untuk n8n skripsi saya.

for starting the flask app

```flask --app app --debug run```

running celery worker command

```celery -A make_celery.celery worker --loglevel=info --pool=solo -n worker1@%h```
