import os
import argparse
import re
import sys
import git.exc
from git import Repo


class Repository:
    def __init__(self, repo_path):
        self.repo = None if repo_path is None else Repo(repo_path, search_parent_directories=True)
        self.last_tag = None
        self.new_version = None
        self.major = None
        self.minor = None
        self.patch = None
        self.relevant_commits = None
        self.changelog = []
        self.not_synced = False

    def tag_lookup(self, initial=None, no_changelog=False, debug=False, increase_pre_release=None):
        """
        Searches tags for last version tag and stores the increments, the last version and the specific tag.
        If there are no version tags, the program will exit with an error message.
        Raises System Exit if no version tags exist or if an attempt is made to create a first version tag although a
        version tag already exists
        Raises System Exit if the last Tag can not be found in the HEAD branch
        :param initial: If not None, a tag is created with the passed value as title and the changelog from
        all previous commits. After that the program is terminated
        :param no_changelog: If True the initial Tag will be created without a changelog
        :param debug: If True the full Git Command Error Message will be printed
        :param increase_pre_release: If True, pre-release tags are considered as LastTag
        """
        tags = self.repo.tags
        self.not_synced = False
        pre_release_version = False
        split_versions = []
        versions = []
        for tag in reversed(tags):
            version_match = re.search(r'^(\d+).(\d+).(\d+)(-?(([a-zA-Z]+)([0-9]+)))?$', str(tag))
            if not version_match:
                continue
            major = int(version_match.group(1))
            minor = int(version_match.group(2))
            patch = int(version_match.group(3))
            pre_release_version = version_match.group(4) is not None
            if pre_release_version and not increase_pre_release:
                continue
            if tag.commit in self.repo.iter_commits("HEAD"):
                versions.append(tag)
                split_versions.append([major, minor, patch])
            else:
                if increase_pre_release:
                    continue
                self.not_synced = True
                unsynced_tag = tag
            if version_match.group(4) is not None:
                pre_release_version = True
        if split_versions:
            max_version = max(split_versions)
            self.last_tag = versions[split_versions.index(max_version)]
            self.major = max_version[0]
            self.minor = max_version[1]
            self.patch = max_version[2]
        try:
            if initial:
                if self.last_tag is None:
                    if not no_changelog:
                        self.relevant_commits = list(self.repo.iter_commits("HEAD"))
                        self.create_changelog()
                        self.repo.create_tag(initial, message="\n".join(self.changelog))
                        self.tag_lookup()
                        print(self.last_tag)
                        print('Changelog:')
                        for change in self.changelog:
                            print(change)
                    else:
                        self.repo.create_tag(initial)
                        self.tag_lookup()
                        print(self.last_tag)
                    exit(0)
                else:
                    sys.exit("There is already a version tag")
            else:
                if self.not_synced and pre_release_version is False:
                    for head in self.repo.heads:
                        if unsynced_tag.commit in self.repo.iter_commits(head):
                            sys.exit(f'Branches not synced ({unsynced_tag.commit.summary} missing in HEAD). Please rebase onto {head}')
        except git.GitCommandError as err:
            if debug:
                raise
            print(str(err.stderr).lstrip("error: "), file=sys.stderr)
            status = re.sub(r'\((\d+)?\)$', r'\1', str(err.status))
            if status == "0":
                status = 1
            elif status.isdigit():
                sys.exit(int(status))
            sys.exit(status)
        if self.last_tag is None and pre_release_version is False:
            sys.exit(f'There are no Version Tags in {self.repo.active_branch}')
        elif pre_release_version is True and not increase_pre_release and self.not_synced:
            sys.exit(f'Last version is a Pre-Release. Use -r "{version_match.group(6)}" option to perform a pre-release-increase')

    def find_relevant_commits(self):
        """
        Searches all commits since the last version tag
        Raises SystemExit if there are no relevant commits
        """
        all_commits = list(self.repo.iter_commits("HEAD"))
        last_tagged_commit = self.last_tag.commit
        last_tagged_index = all_commits.index(last_tagged_commit)
        self.relevant_commits = list(self.repo.iter_commits("HEAD"))[:last_tagged_index]
        if len(self.relevant_commits) < 1:
            sys.exit("There are no new commits")

    def increase_version(self):
        """
        Orders the Relevant commits according to the AngularJS commit standard and increments the new version
        number accordingly
        """
        patch_keywords = ['fix', 'docs', 'style', 'refactor', 'perf', 'test', 'chore']
        major_done = False
        minor_done = False
        patch_done = False
        for commit in self.relevant_commits:
            summary = str(commit.summary)
            parenthesis_index = summary.find('(')
            commit_message_clone = list(commit.message)
            line_ends = []
            commit_type = summary[0:parenthesis_index]
            for char in commit_message_clone:
                if char == "\n":
                    line_ends.append(commit_message_clone.index(char))
                    commit_message_clone[commit_message_clone.index(char)] = 'x'
            for line in line_ends:
                if 'breaking change' in commit.message[line:line+16].lower() and not major_done:
                    self.major += 1
                    self.minor = 0
                    self.patch = 0
                    major_done = True
                    break
            if commit_type.lower() == 'feat' or commit_type.lower() == 'feature' and not minor_done and not major_done:
                self.minor += 1
                self.patch = 0
                minor_done = True
            if not major_done and not minor_done:
                for keyword in patch_keywords:
                    if commit_type == keyword and not patch_done:
                        self.patch = self.patch+1
                        patch_done = True
                        break
                if patch_done is False:
                    self.patch += 1
                    patch_done = True
                    print("Warning: The commits do not correspond to the AngularJS commit format", file=sys.stderr)
        self.new_version = '.'.join([str(self.major), str(self.minor), str(self.patch)])

    def increase_major(self):
        """
        Increments the last versions major increment
        """
        self.major += 1
        self.minor = 0
        self.patch = 0
        self.new_version = '.'.join([str(self.major), str(self.minor), str(self.patch)])

    def increase_minor(self):
        """
        Increments the last versions minor increment
        """
        self.minor += 1
        self.patch = 0
        self.new_version = '.'.join([str(self.major), str(self.minor), str(self.patch)])

    def increase_patch(self):
        """
        Increments the last versions patch increment
        """
        self.patch += 1
        self.new_version = '.'.join([str(self.major), str(self.minor), str(self.patch)])

    def add_tag(self, message, debug=False):
        """
        Add a Tag with the new version to the git repository
        Raises System Exit if a Git Command Error occurs
        :param message: The message of the added git repository
        :param debug: If True the full Git Command Error Message will be raised
        """
        try:
            self.repo.create_tag(self.new_version, message=message)
        except git.GitCommandError as err:
            if debug:
                raise
            print(str(err.stderr).lstrip("error: "), file=sys.stderr)
            status = re.sub(r'\((\d+)?\)$', r'\1', str(err.status))
            if status == "0":
                status = 1
            elif status.isdigit():
                sys.exit(int(status))
            sys.exit(status)

    def create_changelog(self):
        """
        Creates a changelog from the commit-summaries and hashes of the relevant commits
        """
        for commit in reversed(self.relevant_commits):
            self.changelog.append(f"{commit.summary} ({commit.hexsha[:7]})")

    def increase_pre_release(self, pre_release_prefix):
        """
        Searches for the last pre-release version with the given pre-release prefix and increments its version
        accordingly
        If there is no pre-release version with the given prefix a new one will be created after the last
        version is incremented
        Raises System Exit if the last pre-release version can not be found in the HEAD branch
        :param pre_release_prefix: The Prefix that will be used for the pre-release version
        """
        pre_release_versionen = []
        relevant_tags = []
        for tag in reversed(self.repo.tags):
            if str(tag).find(pre_release_prefix) == -1:
                done = False
                continue
            else:
                pre_release_version = re.search(r'[A-Za-z]+([0-9]+)', str(tag)).group(1)
                pre_release_versionen.append(int(pre_release_version))
                relevant_tags.append(tag)
        if len(pre_release_versionen) > 0:
            pre_release_version = max(pre_release_versionen)
            relevant_tag = relevant_tags[pre_release_versionen.index(pre_release_version)]
            if self.new_version != str(relevant_tag)[:str(relevant_tag).find(pre_release_prefix)] and self.new_version is not None:
                self.new_version = f'{self.new_version}{pre_release_prefix}1'
            else:
                self.new_version = f'{str(relevant_tag)[:str(relevant_tag).find(pre_release_prefix)]}{pre_release_prefix}{int(pre_release_version) + 1}'
            self.last_tag = relevant_tag
            done = True
            if relevant_tag.commit not in self.repo.iter_commits("HEAD"):
                self.not_synced = True
                for head in self.repo.heads:
                    if relevant_tag.commit in self.repo.iter_commits(head):
                        sys.exit(f'Pre-Release-Versions not synced ({relevant_tag.commit.summary} missing in HEAD). Please rebase onto {head}')
                sys.exit(f'Branches not synced ({relevant_tag.commit.summary} missing in HEAD)')
        if done is False and self.new_version is not None:
            self.new_version = f'{self.new_version}{pre_release_prefix}1'
        elif done is False and self.new_version is None:
            self.increase_version()
            self.new_version = f'{self.new_version}{pre_release_prefix}1'


def controller(args):
    """
    Searches for a repository and calls functions according to the chosen argparse arguments
    If no path argument is given the current working directory will be used to search a repository
    Raises System Exit if no repository can be found
    :param args: Argparse arguments
    """
    try:
        if args.path:
            repo = Repository(args.path)
        else:
            repo = Repository(os.getcwd())
    except git.exc.InvalidGitRepositoryError:
        sys.exit("No Git repository detected")
    repo.tag_lookup(args.init, args.no_changelog, debug=args.debug, increase_pre_release=args.pre_release)
    repo.find_relevant_commits()
    if args.major:
        repo.increase_major()
    elif args.minor:
        repo.increase_minor()
    elif args.patch:
        repo.increase_patch()
    else:
        if not args.pre_release:
            repo.increase_version()
    if args.pre_release:
        repo.increase_pre_release(args.pre_release)
    print(repo.new_version)
    if args.tag and args.no_changelog:
        repo.add_tag(None, debug=args.debug)
    elif args.tag:
        repo.create_changelog()
        repo.add_tag("\n".join(repo.changelog), debug=args.debug)
        for change in repo.changelog:
            print(change)


def argparse_main():
    """
    Argument parser to use versionify with the CLI
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-P', '--path', help='Path of the repository')
    parser.add_argument('-M', '--major', action='store_true', help='Raise current major version')
    parser.add_argument('-m', '--minor', action='store_true', help="Raise current minor version")
    parser.add_argument('-p', '--patch', action='store_true', help="Raise current patch version")
    parser.add_argument('-t', '--tag', action='store_true', help="Add Version-Tag with changelog")
    parser.add_argument('-c', '--no-changelog', action='store_true', help="Exclude Changelog when adding a git tag")
    parser.add_argument('-r', '--pre-release', help="Raise pre-release version")
    parser.add_argument('-i', '--init', nargs='?', const="0.0.1", help="Add Initial Version-Tag")
    parser.add_argument('--debug', help="Raise Git Command Errors if they occur")
    controller(parser.parse_args())


if __name__ == "__main__":
    argparse_main()
