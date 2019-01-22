# BASE README

## Development environment setup
    These instructions include commands which must be executed in the terminal.
    All such commands are prefixed with a greater that symbol ">" which should
    not be included in the command executed in the terminal.
    They have currently only been tested on mac os x

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

## Git workflow

###  Branch    

    create branches for your work using the naming convention
    if the branch addresses a story entirely use the story number
        feature/story<mingle story number>-<descriptive but short>
        bugfix/story<mingle story number>-<descriptive but short>
    if the branch addresses a task use the task number
        feature/task<mingle task number>-<descriptive but short>
        bugfix/task<mingle task number>-<descriptive but short>

    if there isn't a story or task number use 000 this
    will give us a way to identify work that doesn't have a story or task

### Sprint

    At the beggining of each sprint we will create a develop branch on the origin
    repo. Update your local develop branch from origin. Create feature
    branches off of your develop branch. Merge develop into your feature branches
    frequently to stay in sync with the team. this will help us resolve conflicts
    quickly.

    At the end of sprint we will merge develop into master, test on ci, push to
    staging for manual qa(if any) and then tag and deploy to production

    Bugfix merge requests will be made against master, tested on ci, tagged and
    deployed

### Merge
#### Pre merge request checklist
    - merge the latest from develop branch into your feature branch
    - all unit tests pass locally
    - all python code is pep8 compliant
    - all javascript code is jshint compliant
    - this merge request has a story or task

#### Send the request    

    When work is ready to be merged into the develop branch create a merge request
    from your fork to the develop branch.  If you just want feedback
    and csomewhere someone can easily review your code prefix your merge request
    with [WIP] for work in progress.

#### Presentation

    Break up commits as discrete units of work. As a rule of thumb use task level
    granularity or even finer. Try to structure commits so that you can do a code
    review and explain it by walking through the commits. If a lot of the code is
    brand new it may be more practical to walk through based on files.

#### Code Reviews
    Code reviews will follow scrum everyday in order to minimize meetings.
    Code must be reviewed by 2 others and "signed" using a comment on the merge
    request
    Code will be merged when it passes review or when only minor modifications
    are needed neccessary post-review.
    If schedules don't allow for a group code review they can be done
    asynchronously using comments on the merge request.

#### Do it
    Once review is passed code will be immediately merged so that developers can
    update their branches.  All developers will have the ability to merge code into
    the develop branch but by convention it will usually be the lead developer.
