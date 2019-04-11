## Git workflow
TBD:  use pull request model with 2 branches:

`develop` -- for active development and testing
`master` -- for release/production code



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
