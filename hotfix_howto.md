# Hotfix deployment procedure

## Motivation
To able to quickly roll out new code to production environment and fix critical issues.


## Steps


1) Commit new code to one(or many) of our git repositories under branch name `hotfix_{issue description}`. Git branch name should be the same accross all repositories.

2) Open pull request(s) in bitbucket to merge new code to `stage` branch(es)

3) Once code review is done, `hotfix_{issue description}` pull requests should be closed using `squash` merge strategy(!IMPORTANT!).
   After pull request is closed, hotfix code is now at `stage` branches of corresponding repos

4) Deploy to stage. Given the list of Jenkins build jobs:

  * http://local-jenkins.customate.net:8080/job/BUILD_Frontend/  (builds `frontend-spa` repo)
  * http://local-jenkins.customate.net:8080/job/BUILD_Frontend-API/ (builds `frontend-api` repo)
  * http://local-jenkins.customate.net:8080/job/BUILD_Payment-API/ (builds `payment-api` repo)

  Always select `stage` branch and run each job separately, based on actual changes to each repo.

5) QA should verify that hotfix was indeed successfull on `stage` environment.

6) Prepare `master` branch(es) for production deploy for every repo in question.


```bash
$ git fetch origin +stage:stage
$ git fetch origin +master:master
$ git checkout master
# Apply the change introduced by the commit at the tip of the stage branch and create a new commit with this change.
$ git cherry-pick stage
# optional conflict resolition steps 
$ git push origin stage

```

7) Backport hotfix to `develop` branch as well

```bash
$ git fetch origin +stage:stage
$ git fetch origin +develop:develop
$ git checkout develop
# Apply the change introduced by the commit at the tip of the stage branch and create a new commit with this change.
$ git cherry-pick stage
# optional conflict resolition steps 
$ git push origin develop
```

For more info, see https://git-scm.com/docs/git-cherry-pick

8) Run Jenkins build jobs as in step 4, but this time, selecting `master` branch.

