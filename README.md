# Payment API

## What
        This is a REST API service built on top of [Django REST Framework](https://django-rest-framework.readthedocs.io) and
        [JSON API](https://jsonapi.org) spec for communication with client.

### Prerequisites
    install docker https://www.docker.com/products/overview

### Installation steps
    checkout the source code
    > git clone repo
    > cd customate_app/docker
    > docker-compose build
    > docker-compose up


## Working on the project

### project location
    The code accessed by all the docker servers/instances is in the folder
    /path/to/your/install/customate_app

### bring up the docker work environment
    start docker and set docker-machine environment variables
    > cd /path/to/your/install/customate_app/docker/
    > docker-compose up

## Adding project requirements

### add new packages to container
    when adding new requirements to the requirements.txt a new image must be
    built in order to persist the changes across container restarts

    go inside the container
    > docker exec -i -t customate_app_customate_1 bash

    to update requirements.txt
    > pip install --upgrade --force-reinstall -r requirements.txt

    to insall a new package
    > pip install some-packege-name

    to freeze changes
    > pip freeze > requirements.txt

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
