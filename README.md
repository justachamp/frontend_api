# Frontend API

## What
This is a REST API service built on top of [Django REST Framework](https://django-rest-framework.readthedocs.io) and
[JSON API](https://jsonapi.org) spec for communication with client.

## Prerequisites

* Python 3.7
* PostgreSQL 10


## Installation steps
### Install [pyenv](https://github.com/pyenv/pyenv) and python 3.7
Following instructions are for OSX
```
$ brew install pyenv
$ echo "eval \"$(pyenv init -)\"" >> ~/.bash_profile
$ pyenv install 3.7.2
```


### Get source code
```bash
$ git clone git@bitbucket.org:customateteam/frontend-api.git
$ cd frontend-api/customate
$ echo "3.7.2" >> .python-version

# Make sure that correct python version is installed
$ source ~/.bash_profile
# python --version
Python 3.7.2

# Install python dependencies
$ pip install -r requirements.txt

```

If there will be an issue with psycopg2, similar to this:
```
ld: library not found for -lssl
    clang: error: linker command failed with exit code 1 (use -v to see invocation)
    error: command 'clang' failed with exit status 1
```

try get paths with 

```
pg_config --ldflags
```

and then run:

```
env LDFLAGS='-L../../src/common -L/usr/local/opt/openssl/lib -L/usr/local/opt/readline/lib -Wl,-dead_strip_dylibs' pip install psycopg2==2.8.2
```

### Setup local env
```
$ cp env.sh.sample env.sh
```


### Setup database
For OS X I would recommend [Postgresapp](http://postgresapp.com/documentation/).

**Import from existings stage/dev env**

The most straitforward way to setup DB would be to grab full dump from stage/dev environments:
```
# schema only, without owners and grant/revoke previleges
PGPASSWORD="******" pg_dump -s -O -x customate_frontend_stage --username=customate_frontend_stage --host=stage-psql.customate.net > schema.sql
# data only
PGPASSWORD="******" pg_dump -a -O -x customate_frontend_stage --username=customate_frontend_stage --host=stage-psql.customate.net > data.sql

```

After that, just import everything into your local db:
```
psql -U mydbuser --host=127.0.0.1 customate< schema.sql
psql -U mydbuser --host=127.0.0.1 customate< data.sql
```

**Fresh DB schema with empty data**

Once your DB is created via `CREATE DATABASE customate`, there is a way to create empty schema by applying migrations
```
# apply your local env
$ source env.sh
# run migrations
$ ./manage.py migrate
```

Make sure that every migration was successfull by running:

```
$ ./manage.py showmigrations
```

### Run tests
*Note:* we are using "ltree" extension for some functionality, this extension is created in migration, but
without [SUPERUSER privilege](https://stackoverflow.com/questions/16527806/cannot-create-extension-without-superuser-role) database user will not be able to create any extension, that's why you should grant this privilege before first test run. After that you can remove an extra permission from user.
```
./manage.py test --keepdb
```

### Run Django web server

```
./manage.py runserver
```

### Run Celery (workers for all queues and celerybeatd)
```
celery worker --app customate --beat --loglevel info
```

Once the server is up, REST APIs should be available at `http://localhost:8080/`


## API documentation

* [Frontend API documentation](https://frontendservice.docs.apiary.io/)
* [Payment API documentation](https://customatepayment.docs.apiary.io/)


## Git workflow
We use pull request model:

* `develop` -- for active development and testing
* `master` -- for release/production code
* `stage` -- branch contains merged code from `develop` branch once release is scheduled

