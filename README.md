# git-versionify

Versionify proposes the next appropriate version of a Git repository and follows the guidelines of [semantic versioning](https://semver.org/) and the [AngularJS Commit Message Format](https://github.com/angular/angular.js/blob/master/DEVELOPERS.md#commit-message-format).
To do this, the new commits are searched for keywords (see below).

The version number is increased by a maximum of 1, regardless of the number of commits.

## Installation
````bash
pip install git+https://github.com/bromiesTM/git-versionify.git
````
## Keywords

- "**breaking change**" → **+1.0.0**

- "**feature**" & "**feat**" (+ variations) → MAJOR.**+1.0**

- "**fix**", "**docs**", "**style**", "**refactor**", "**perf**", "**test**", "**chore**" → MAJOR.MINOR.**+1**


Upper & lower case are ignored


## Synopsis
````
versionify [option]

Options:
- -h Help
- -P <PATH>, --path <PATH>                  Path of the repository
- -M, --major                               Raise current major version
- -m, --minor                               Raise current minor version
- -p, --patch                               Raise current patch version
- -t, --tag                                 Add Version-Tag with changelog
- -c, --no-changelog                        Exclude Changelog when adding a git tag
- -r [<prefix>], --pre-release [<prefix>]   Raise pre-release version
- -i, --init                                Add inital version tag (0.0.1)
--debug                                     Raise Git Command Errors if they occur
````
Example:
````bash
~/my-git-projekt$ versionify
0.0.2
````