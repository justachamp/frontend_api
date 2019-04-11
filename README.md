# Payment API

## What
This is a REST API service built on top of [Django REST Framework](https://django-rest-framework.readthedocs.io) and
[JSON API](https://jsonapi.org) spec for communication with client.


## Install python3.7
Use [pyenv](https://github.com/pyenv/pyenv) to avoid versioning hell or your preferred tool to setup isolated python environment.

## Install dependencies
```
cd customate
pip install -r requirements.txt
```

## Install PostgreSQL10 database `customate`
Use schema and sample data from `sql/`
```
psql -U myuser --host=127.0.0.1 customate < sql/schema.sql
psql -U myuser --host=127.0.0.1 customate < sql/data.sql

```

## Setup env file
Use `env.sh.sample` as example:
```
cd customate
cp env.sh.sample env.sh
```

## Run django devserver
```
source env.sh
./manage.py runserver

# check that service is running
curl "http://localhost:8000/"
```





### other useful commands

    list out the docker containers and check their statuses
    > docker ps

    stop all docker containers
    > docker-compose down

    get a shell on a named container
    > docker exec -i -t container_name bash

    clean up old containers that have exited
    > docker rm -v $(docker ps -a -q -f status=exited)

### accessing services running on docker containers
    services running on docker containers are accessed via the port mappings in
    docker/docker-compose.yml.

    For example
    psql -U customate -h 127.0.0.1 -p 5442
    ssh -p 2222 root@localhost


### S3 static 
    add to environemnt next variables:
    AWS_ACCESS_KEY_ID=
    AWS_SECRET_ACCESS_KEY=
    AWS_S3_STORAGE_BUCKET_NAME=customate-dev-django
    
    For sync static files need execute:
    python3.7 manage.py collectstatic
