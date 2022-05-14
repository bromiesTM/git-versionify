import unittest
from contextlib import contextmanager
from io import StringIO
from versionify.versionify_main import *
from argparse import Namespace


# Commit class for the simulated git repository
class Commit:
    def __init__(self, summary, message):
        self.summary = summary
        self.message = message
        self.hexsha = "1234567891011"


# Tag class for the simulated git repository
class Tag:
    def __init__(self, text, commit, message=None):
        self.commit = commit
        self.text = text
        self.tag = Namespace(message=message)

    def __str__(self):
        return self.text


# Branch class for the simulated git repository
class Branch:
    def __init__(self, name, commits):
        self.name = name
        self.commits = commits

    def __str__(self):
        return self.name


# Get versionifys stdout & stderr
@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


class VersionifyTest(unittest.TestCase):
    def test_default_versioning_major(self):
        """
        --A-----B-----C-----D --master
          |     |           |
        2.0.0 4.6.3         ? <- 5.0.0
        """
        # List of all commits in the simulated repository
        commits = [
            # Commit from previous Version (2.0.0)
            Commit("feature(...): new feature", "feature(...): new feature\n"),
            # Commit from previous Version (4.6.3)
            Commit("style(...): sth is better now", "style(...): sth is better now\n"),
            # new Minor-Commit
            Commit("feature(...):new feature", "feature(...):new feature\n"),
            # new Patch-Commit with Breaking Change -> Major Increase
            Commit("docs(...):change", "docs(...):change\nBREAKING CHANGE: change\n"),
        ]
        # List of all tags in the simulated repository
        tags = [
            # old Version-Tag
            Tag('2.0.0', commits[0]),
            # last Version-Tag
            Tag('4.6.3', commits[1]),
        ]

        def iter_commits(branch):
            return iter(reversed(commits))

        # Simulated repository
        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=None,
        )
        repo = Repository(None)
        repo.repo = test_repo_instance
        with captured_output() as (out, err):
            repo.tag_lookup()
            repo.find_relevant_commits()
            repo.increase_version()
            print(repo.new_version)
        self.assertEqual("5.0.0\n", out.getvalue())

    def test_default_versioning_minor(self):
        """
        ---A--------B---------C --master
           |        |         |
         1.0.0   2.0.0-rc1    ? <-1.1.0
        """
        commits = [
            # Commit from previous Version (1.0.0)
            Commit("feature(...): new feature", "feature(...): new feature\n"),
            # new Patch-Commit
            Commit("style(...): sth is better now", "style(...): sth is better now\n"),
            # new Minor-Commit
            Commit("feature(...):new feature", "feature(...):new feature\n"),
        ]
        tags = [
            # pre-release version-Tag should be ignored
            Tag("2.0.0-rc", commits[1]),
            # last Version-Tag
            Tag('1.0.0', commits[0]),
        ]

        def iter_commits(branch):
            return iter(reversed(commits))
        
        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=None,
        )
        repo = Repository(None)
        repo.repo = test_repo_instance
        with captured_output() as (out, err):
            repo.tag_lookup()
            repo.find_relevant_commits()
            repo.increase_version()
            print(repo.new_version)
        self.assertEqual("1.1.0\n", out.getvalue())

    def test_default_versioning_patch(self):
        """
        ---A-----B-----C-----D --master
           |     |           |
         4.6.2 4.6.3       4.6.4

        """
        commits = [
            # Commit from previous Version (4.6.2)
            Commit("feature(...): new feature", "feature(...): new feature\n"),
            # Commit from previous Version (4.6.3)
            Commit("style(...): sth is better now", "style(...): sth is better now\n"),
            # new Patch-Commit
            Commit("refactor(...):a refactor", "refactor(...):a refactor\n"),
            # new Patch-Commit
            Commit("docs(...):change", "docs(...):change\n"),
        ]
        tags = [
            # old Version-Tag
            Tag("4.6.2", commits[0]),
            # last Version-Tag
            Tag('4.6.3', commits[1]),
        ]

        def iter_commits(branch):
            return iter(reversed(commits))
        
        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=None,
        )
        repo = Repository(None)
        repo.repo = test_repo_instance
        with captured_output() as (out, err):
            repo.tag_lookup()
            repo.find_relevant_commits()
            repo.increase_version()
            print(repo.new_version)
        self.assertEqual("4.6.4\n", out.getvalue())

    def test_default_versioning_wrong_format(self):
        """
        ---A--------B-----C-----D --master
           |        |           |
         0.0.1   21.3.12        ? <- 21.3.13 + wrong format warning
        """
        commits = [
            # Commit from previous Version (0.0.1)
            Commit("feature(...): new feature", "feature(...): new feature\n"),
            # Commit from previous Version (21.3.12)
            Commit("style(...): sth is better now", "style(...): sth is better now\n"),
            # new Commit with wrong format
            Commit("third commit", "third commit\n"),
            # new Commit with wrong format
            Commit("fourth commit", "fourth commit\n"),
        ]
        tags = [
            # old Version-Tag
            Tag("0.0.1", commits[0]),
            # last Version-Tag
            Tag('21.3.12', commits[1]),
        ]

        def iter_commits(branch):
            return iter(reversed(commits))
        
        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=None,
        )
        repo = Repository(None)
        repo.repo = test_repo_instance
        with captured_output() as (out, err):
            repo.tag_lookup()
            repo.find_relevant_commits()
            repo.increase_version()
            print(repo.new_version)
        self.assertEqual("21.3.13\n", out.getvalue())
        self.assertEqual("Warning: The commits do not correspond to the AngularJS commit format\n", err.getvalue())

    def test_increase_major(self):
        """
        ---A------B --master
           |      |
         3.5.6    ? <-4.0.0
        """
        commits = [Commit("feature(...): new feature", "feature(...): new feature\n",)]
        tags = [Tag("3.5.6", commits[0])]
        branches = [Branch("master", commits)]

        def iter_commits(branch):
            return iter(reversed(commits))

        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=branches[0],
            heads=branches,
        )
        repo = Repository(None)
        repo.repo = test_repo_instance
        with captured_output() as (out, err):
            repo.tag_lookup()
            repo.increase_major()
            print(repo.new_version)
        self.assertEqual("4.0.0\n", out.getvalue())

    def test_increase_minor(self):
        """
        ---A-----B --master
           |     |
        10.4.8   ? <- 10.5.0
        """
        commits = [Commit("feature(...): new feature", "feature(...): new feature\n", )]
        branches = [Branch("master", commits)]
        tags = [Tag("10.4.8", commits[0])]

        def iter_commits(branch):
            return iter(reversed(commits))

        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=branches[0],
            heads=branches,
        )
        repo = Repository(None)
        repo.repo = test_repo_instance
        with captured_output() as (out, err):
            repo.tag_lookup()
            repo.increase_minor()
            print(repo.new_version)
        self.assertEqual("10.5.0\n", out.getvalue())

    def test_increase_patch(self):
        """
        ---A-----B --master
           |     |
         0.0.1   ? <- 0.0.2
        """
        commits = [Commit("feature(...): new feature", "feature(...): new feature\n")]
        branches = [Branch("master", commits)]
        tags = [Tag("0.0.1", commits[0])]

        def iter_commits(branch):
            return iter(reversed(commits))

        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=branches[0],
            heads=branches,
        )
        repo = Repository(None)
        repo.repo = test_repo_instance
        with captured_output() as (out, err):
            repo.tag_lookup()
            repo.increase_patch()
            print(repo.new_version)
        self.assertEqual("0.0.2\n", out.getvalue())

    def test_no_new_commits(self):
        """
        ---A-----B --master
           |     |
         2.0.0 4.6.3
        """
        commits = [
            # Commit from previous Version (2.0.0)
            Commit("feature(...): new feature", "feature(...): new feature\n"),
            # Commit from previous Version (4.6.3)
            Commit("style(...): sth is better now", "style(...): sth is better now\n"),
        ]
        tags = [
            # old Version-Tag
            Tag("2.0.0", commits[0]),
            # last Version-Tag
            Tag('4.6.3', commits[1])
        ]

        def iter_commits(branch):
            return iter(reversed(commits))

        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=None,
        )
        repo = Repository(None)
        repo.repo = test_repo_instance
        with self.assertRaises(SystemExit) as cm:
            repo.tag_lookup()
            repo.find_relevant_commits()
            repo.increase_version()
            print(repo.new_version)
        self.assertEqual(cm.exception.code, "There are no new commits")

    def test_no_tags(self):
        """
        ---A---------B --master
           |         |
        keineVersion ? <- There are no Version Tags
        """
        commits = [
            # Commit from "Ich bin keine Version"
            Commit("feature(...): new feature", "feature(...): new feature\n"),
            # new Commit
            Commit("style(...): sth is better now", "style(...): sth is better now\n"),
        ]
        tags = [Tag("Ich bin keine Version", commits[0])]

        def iter_commits(branch):
            return iter(reversed(commits))

        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=None,
        )
        repo = Repository(None)
        repo.repo = test_repo_instance
        with self.assertRaises(SystemExit) as cm:
            repo.tag_lookup()
            print(repo.new_version)
        self.assertEqual(cm.exception.code, f'There are no Version Tags in {repo.repo.active_branch}')

    def test_add_tag(self):
        """
        ---A-----B --master
           |     |
         4.6.3   ? <- 4.6.4
        """
        commits = [
            # Commit from previous Version (4.6.3)
            Commit("feature(...): new feature", "feature(...): new feature\n"),
            # new Commit
            Commit("style(...): sth is better now", "style(...): sth is better now\n"),
        ]
        tags = [Tag("4.6.3", commits[0])]

        def iter_commits(branch):
            return iter(reversed(commits))

        def create_tag(name, message):
            test_repo_instance.tags.append(Tag(name, commits[1], message))
            return name, message

        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=None,
            create_tag=create_tag,
        )
        repo = Repository(None)
        repo.repo = test_repo_instance
        repo.tag_lookup()
        repo.find_relevant_commits()
        repo.increase_version()
        repo.create_changelog()
        repo.add_tag(repo.changelog)
        repo.tag_lookup()
        self.assertEqual(repo.last_tag.text, '4.6.4')
        self.assertEqual([f"{commits[1].message[:-1]} ({commits[1].hexsha[:7]})"], repo.repo.tags[-1].tag.message)

    def test_changelog(self):
        """
        ---A-----B-----C-----D --master
           |                 |
         4.6.3               ? <- 4.7.0
        """
        commits = [
            # Commit from previous Version (4.6.3)
            Commit("feature(...): new feature", "feature(...): new feature\n"),
            # new Commit
            Commit("style(...): sth is better now", "style(...): sth is better now\n"),
            # new Commit
            Commit("docs(...)document change", "docs(...)document change\n"),
            # new Commit
            Commit("feature(...)second new feature", "feature(...)second new feature\n"),
        ]
        tags = [Tag("4.6.3", commits[0])]

        def iter_commits(branch):
            return iter(reversed(commits))

        def create_tag(name, message):
            test_repo_instance.tags.append(Tag(name, commits[1], message))
            return name, message

        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=None,
            create_tag=create_tag,
        )
        repo = Repository(None)
        repo.repo = test_repo_instance
        repo.tag_lookup()
        repo.find_relevant_commits()
        repo.increase_version()
        repo.create_changelog()
        self.assertEqual(repo.changelog, [f'{commits[1].message[:-1]} ({commits[1].hexsha[:7]})',
                                          f'{commits[2].message[:-1]} ({commits[2].hexsha[:7]})',
                                          f'{commits[3].message[:-1]} ({commits[3].hexsha[:7]})'])

    def test_pre_release_major(self):
        """
        --A---------B-------C-------D --master
          |         |       |       |
        4.6.3rc1  4.6.3 4.7.0rc8    ? <- 5.0.0rc1

        """
        commits = [
            # Commit from previous Version
            Commit("feature(...)...", "feature(...)...\n"),
            # Commit from old Pre Release version Version
            Commit("docs(...)...", "docs(...)...\n"),
            # Commit previous Pre Release Version
            Commit("style(...)...", "style(...)...\n"),
            # new Commit
            Commit("docs(...)...", "docs(...)...\n"),
        ]
        tags = [
            Tag('4.6.3', commits[1]),
            Tag("4.6.3rc1", commits[0]),
            Tag("4.7.0rc8", commits[2]),
        ]

        def iter_commits(branch):
            return iter(reversed(commits))

        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=None,
        )
        repo = Repository(None)
        repo.repo = test_repo_instance
        repo.tag_lookup()
        repo.increase_major()
        repo.tag_lookup()
        repo.increase_pre_release("rc")
        self.assertEqual("5.0.0rc1", repo.new_version)

    def test_pre_release_new(self):
        """
        ---A-----B --master
           |     |
         4.6.3   ? <-4.6.4rc1
        """
        commits = [
            # Commit from previous Version
            Commit("feature(...)...", "feature(...)...\n"),
            # new Commit
            Commit("style(...)...", "style(...)...\n"),
        ]
        tags = [Tag('4.6.3', commits[0])]

        def iter_commits(branch):
            return iter(reversed(commits))

        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=None,
        )
        repo = Repository(None)
        repo.repo = test_repo_instance
        repo.tag_lookup()
        repo.find_relevant_commits()
        repo.increase_version()
        repo.increase_pre_release("rc")
        self.assertEqual(repo.new_version, "4.6.4rc1")

    def test_pre_release_versioning(self):
        """
        ---A--------B--------C---------D --master
           |        |        |         |
        4.6.3rc1  4.6.3  4.7.0rc20     ? <- 4.7.0rc21
        """
        commits = [
            # Commit from previous Version
            Commit("feature(...)...", "feature(...)...\n"),
            # Commit from old Pre Release version Version
            Commit("docs(...)...", "docs(...)...\n"),
            # Commit previous Pre Release Version
            Commit("style(...)...", "style(...)...\n"),
            # new Commit
            Commit("docs(...)...", "docs(...)...\n"),
        ]
        tags = [
             Tag('4.6.3', commits[1]),
             Tag("4.6.3rc1", commits[0]),
             Tag("4.7.0rc20", commits[2]),
        ]

        def iter_commits(branch):
            return iter(reversed(commits))

        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=None,
        )
        repo = Repository(None)
        repo.repo = test_repo_instance
        repo.tag_lookup()
        repo.increase_pre_release("rc")
        self.assertEqual("4.7.0rc21", repo.new_version)

    def test_pre_release_changelog_new_pre_release(self):
        """
        ---A----B----C---D --master
           |             |
         4.6.3           ? <- 4.6.4rc1
        """
        commits = [
            # Commit from previous Version 4.6.3
            Commit("feature(...)...", "feature(...)...\n"),
            # new Commit
            Commit("docs(...)...", "docs(...)...\n"),
            # new Commit
            Commit("style(...)...", "style(...)...\n"),
            # new Commit
            Commit("docs(...)...", "docs(...)...\n"),
        ]
        tags = [Tag('4.6.3', commits[0])]

        def iter_commits(branch):
            return iter(reversed(commits))

        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=None,
        )
        repo = Repository(None)
        repo.repo = test_repo_instance
        repo.tag_lookup()
        repo.find_relevant_commits()
        repo.increase_version()
        repo.increase_pre_release("rc")
        repo.find_relevant_commits()
        repo.create_changelog()
        self.assertEqual(repo.changelog, [f'{commits[1].message[:-1]} ({commits[1].hexsha[:7]})',
                                          f'{commits[2].message[:-1]} ({commits[2].hexsha[:7]})',
                                          f'{commits[3].message[:-1]} ({commits[3].hexsha[:7]})'])

    def test_pre_release_changelog_pre_release_versioning(self):
        """
        --A--------B---------C--------D --master
          |        |         |        |
        4.6.3rc1 4.6.3   4.7.0rc11    ? <- 4.7.0rc12
        """
        commits = [
            # Commit from previous Version 4.6.3
            Commit("feature(...)...", "feature(...)...\n"),
            # Commit from old Pre Release Version 4.6.3rc1
            Commit("docs(...)...", "docs(...)...\n"),
            # Commit previous Pre Release Version #4.7.0rc11
            Commit("style(...)...", "style(...)...\n"),
            # new Commit
            Commit("docs(...)...", "docs(...)...\n"),
        ]
        tags = [
            Tag('4.6.3', commits[0]),
            Tag("4.6.3rc1", commits[1]),
            Tag("4.7.0rc11", commits[2]),
        ]

        def iter_commits(branch):
            return iter(reversed(commits))

        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=None,
        )
        repo = Repository(None)
        repo.repo = test_repo_instance
        repo.tag_lookup()
        repo.increase_pre_release("rc")
        repo.find_relevant_commits()
        repo.create_changelog()
        self.assertEqual(repo.changelog, [f'{commits[1].message[:-1]} ({commits[1].hexsha[:7]})'])

    def test_changelog_meeting(self):
        """
        ---A-----B--------C--------D-----E-F
           |     |                 |       |
         4.6.3 4.7.0rc11         4.8.0 4.9.0rc1
        """
        commits = [
            # Commit from previous Version 4.6.3
            Commit("feature(...)...", "feature(...)...\n"),
            # Commit from previous Version 4.6.3
            Commit("docs(...)...", "docs(...)...\n"),
            # Commit previous Pre Release Version #4.8.0
            Commit("style(...)...", "style(...)...\n"),
            # Commit previous Pre Release Version #4.8.0
            Commit("docs(...)...", "docs(...)...\n"),
            # new Commits
            Commit("feature(...)", "feature(...)\n"),
            Commit("feature(...)", "feature(...)\n"),
        ]
        tags = [
            Tag('4.6.3', commits[0]),
            Tag("4.7.0rc11", commits[1]),
            Tag("4.8.0", commits[3]),
            ]

        def iter_commits(branch):
            return iter(reversed(commits))

        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits), iter_commits=iter_commits, active_branch=None)
        repo = Repository(None)
        repo.repo = test_repo_instance
        repo.tag_lookup()
        repo.find_relevant_commits()
        repo.increase_version()
        repo.increase_pre_release("rc")
        repo.create_changelog()
        repo.tag_lookup()
        self.assertEqual(repo.changelog, [f'{commits[4].message[:-1]} ({commits[4].hexsha[:7]})',
                                          f'{commits[5].message[:-1]} ({commits[5].hexsha[:7]})'])

    def test_init(self):
        """
        ---A-----B --master
                 |
                 ? <- 0.0.1
        """
        commits = [
            Commit("feature(...)", "feature(...)\n"),
            Commit("docs(...)", "docs(...)\n"),
        ]
        tags = []

        def iter_commits(branch):
            return iter(reversed(commits))

        def create_tag(name, message):
            test_repo_instance.tags.append(Tag(name, commits[1], message))
            return name, message

        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=None,
            create_tag=create_tag,
        )
        repo = Repository(None)
        repo.repo = test_repo_instance
        with self.assertRaises(SystemExit) as cm:
            repo.tag_lookup(initial="0.0.1")
        self.assertEqual(cm.exception.code, 0)

    def test_init_not_working(self):
        """
        ---A-----B --master
           |     |
         0.0.1 ? <- Warning
        """
        commits = [
            Commit("feature(...)", "feature(...)\n"),
            Commit("docs(...)", "docs(...)\n"),
        ]
        tags = [Tag("1.0.0", commits[0])]

        def iter_commits(branch):
            return iter(reversed(commits))

        def create_tag(name, message):
            test_repo_instance.tags.append(Tag(name, commits[1], message))
            return name, message

        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=None,
            create_tag=create_tag,
        )
        repo = Repository(None)
        repo.repo = test_repo_instance
        with self.assertRaises(SystemExit) as cm:
            repo.tag_lookup(initial="0.0.1")
        self.assertEqual(cm.exception.code, "There is already a version tag")

    def test_increment_add_tag(self):
        """
        --A-----B --master
          |     |
        4.6.3   ? <- 5.0.0
        """
        commits = [
            # Commit from previous Version (4.6.3)
            Commit("feature(...): new feature", "feature(...): new feature\n"),
            # new Commit
            Commit("style(...): sth is better now", "style(...): sth is better now\n"),
        ]
        tags = [Tag('4.6.3', commits[0])]

        def iter_commits(branch):
            return iter(reversed(commits))

        def create_tag(name, message):
            test_repo_instance.tags.append(Tag(name, commits[1], message))
            return name, message

        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=None,
            create_tag=create_tag,
        )
        repo = Repository(None)
        repo.repo = test_repo_instance
        repo.tag_lookup()
        repo.find_relevant_commits()
        repo.increase_major()
        repo.create_changelog()
        repo.add_tag(repo.changelog)
        self.assertEqual(repo.new_version, '5.0.0')
        self.assertEqual([f"{commits[1].message[:-1]} ({commits[1].hexsha[:7]})"], repo.repo.tags[-1].tag.message)

    def test_branches_pre_release_different_branch(self):
        """
               0.0.2rc1   ? <- Branches not synced error
                  |       |
            C-----D-------F --dev
           /       \
        A--B--------E --master
           |        |
         0.0.1   0.0.2rc2
        """
        commits = [
            # A
            Commit("A", "A\n"),
            # B
            Commit("B", "B\n"),
            # C
            Commit("C", "C\n"),
            # D
            Commit("D", "D\n"),
            # E
            Commit("E", "E\n"),
            # F
            Commit("F", "F\n"),
        ]
        tags = [
            Tag('0.0.1', commits[1]),
            Tag('0.0.2rc1', commits[3]),
            Tag('0.0.2rc2', commits[4]),
        ]
        branches = [
            Branch("master", commits=commits[:2] + commits[4:5]),
            Branch("dev", commits=commits[2:4] + commits[5:]),
        ]

        def iter_commits(branch=None):
            if branch == "HEAD":
                return iter(reversed(branches[1].commits))
            if repo.not_synced:
                return iter(reversed(branch.commits))

        test_repo_instance = Namespace(
            tags=tags,
            commits=commits,
            iter_commits=iter_commits,
            active_branch=branches[1],
            heads=branches,
        )

        repo = Repository(None)
        repo.repo = test_repo_instance
        with self.assertRaises(SystemExit) as cm:
            repo.tag_lookup(increase_pre_release=True)
            repo.find_relevant_commits()
            repo.increase_pre_release("rc")
            print(repo.new_version)
        self.assertEqual("Pre-Release-Versions not synced (E missing in HEAD). Please rebase onto master", cm.exception.code)

    def test_branches_pre_release_same_branch(self):
        """
               0.0.2rc1   ? <- 0.0.2rc2
                  |       |
            C-----D-------F --dev
           /       \
        A--B--------E --master
           |        |
         0.0.1   0.0.2
        """
        commits = [
            # A
            Commit("A", "A\n"),
            # B
            Commit("B", "B\n"),
            # C
            Commit("C", "C\n"),
            # D
            Commit("D", "D\n"),
            # E
            Commit("E", "E\n"),
            # F
            Commit("F", "F\n"),
        ]
        tags = [
            Tag('0.0.1', commits[1]),
            Tag('0.0.2rc1', commits[3]),
            Tag('0.0.2', commits[4]),
        ]
        branches = [
            Branch("master", commits=commits[:2] + commits[4:5]),
            Branch("dev", commits=commits[2:4] + commits[5:]),
        ]

        def iter_commits(branch):
            if branch == "HEAD":
                return iter(reversed(branches[1].commits))
            if repo.not_synced:
                return iter(reversed(branch.commits))

        test_repo_instance = Namespace(
            tags=tags,
            commits=commits,
            iter_commits=iter_commits,
            active_branch=branches[1],
            heads=branches,
        )

        repo = Repository(None)
        repo.repo = test_repo_instance
        repo.tag_lookup(increase_pre_release=True)
        repo.find_relevant_commits()
        repo.increase_pre_release("rc")
        self.assertEqual(repo.new_version, "0.0.2rc2")

    def test_branch_version_different_branch(self):
        """
                0.0.1     ? <- Warning not synced
                  |       |
            C-----D-------F --dev
           /       \
        A--B--------E --master
                    |
                  0.0.2
        """
        commits = [
            # A
            Commit("A", "A\n"),
            # B
            Commit("B", "B\n"),
            # C
            Commit("C", "C\n"),
            # D
            Commit("D", "D\n"),
            # E
            Commit("E", "E\n"),
            # F
            Commit("F", "F\n"),
        ]
        tags = [
            Tag('0.0.1', commits[3]),
            Tag('0.0.2', commits[4]),
        ]
        branches = [
            Branch("master", commits=commits[:2] + commits[4:5]),
            Branch("dev", commits=commits[2:4] + commits[5:]),
        ]

        def iter_commits(branch):
            if branch == "HEAD":
                return iter(reversed(branches[1].commits))
            if repo.not_synced:
                return iter(reversed(branch.commits))

        test_repo_instance = Namespace(
            tags=tags,
            commits=commits,
            iter_commits=iter_commits,
            active_branch=branches[1],
            heads=branches,
        )

        repo = Repository(None)
        repo.repo = test_repo_instance
        with self.assertRaises(SystemExit) as cm:
            repo.tag_lookup()
            repo.find_relevant_commits()
            repo.increase_version()
        self.assertEqual(cm.exception.code, "Branches not synced (E missing in HEAD). Please rebase onto master")
        self.assertEqual(repo.new_version, None)

    def test_branches_version_same_branch(self):
        """
                1.0.0rc1
                  |
            C-----D --dev
           /       \
        A--B--------E --master
           |        |
         0.0.9      ? <- 0.0.10
        """
        commits = [
            # A
            Commit("A", "A\n"),
            # B
            Commit("B", "B\n"),
            # C
            Commit("C", "C\n"),
            # D
            Commit("D", "D\n"),
            # E
            Commit("E", "E\n"),
        ]
        tags = [
            Tag('0.0.9', commits[1]),
            Tag('1.0.0rc1', commits[3]),
        ]
        branches = [
            Branch("master", commits=commits[:2] + commits[4:5]),
            Branch("dev", commits=commits[2:4] + commits[5:]),
        ]

        def iter_commits(branch):
            if branch == "HEAD":
                return iter(reversed(branches[0].commits))
            if repo.not_synced:
                return iter(reversed(branch.commits))

        test_repo_instance = Namespace(
            tags=tags,
            commits=commits,
            iter_commits=iter_commits,
            active_branch=branches[0],
            heads=branches,
        )

        repo = Repository(None)
        repo.repo = test_repo_instance
        repo.tag_lookup()
        repo.find_relevant_commits()
        repo.increase_version()
        self.assertEqual(repo.new_version, "0.0.10")

    def test_multi_digit_version(self):
        """
        --A-----B-----C --master
          |     |     |
        0.0.2 0.0.11  ? <- 0.0.12
        """
        commits = [
            Commit("A", "A\n"),
            Commit("B", "B\n"),
            Commit("C", "C\n"),
        ]
        tags = [
            Tag("0.0.2", commits[0]),
            Tag("0.0.11", commits[1]),
        ]

        def iter_commits(branch):
            return iter(reversed(commits))

        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=None,
        )

        repo = Repository(None)
        repo.repo = test_repo_instance
        repo.tag_lookup()
        repo.find_relevant_commits()
        repo.increase_version()
        self.assertEqual("0.0.12", repo.new_version)

    def test_multi_digit_pre_release_version(self):
        """
        --A---------B----------C --master
          |         |          |
        0.0.2rc2  0.0.2rc11    ? <- 0.0.2rc12
        """
        commits = [
            Commit("A", "A\n"),
            Commit("B", "B\n"),
            Commit("C", "C\n"),
        ]
        tags = [
            Tag("0.0.2rc2", commits[0]),
            Tag("0.0.2rc11", commits[1]),
        ]

        def iter_commits(branch):
            return iter(reversed(commits))

        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=None,
        )

        repo = Repository(None)
        repo.repo = test_repo_instance
        repo.tag_lookup(increase_pre_release=True)
        repo.find_relevant_commits()
        repo.increase_pre_release("rc")
        self.assertEqual("0.0.2rc12", repo.new_version)

    def test_none_pre_release(self):
        """
        --A-----B-----C --master
          |     |     |
        0.0.1 1.0.0   ? <- 1.0.1rc1
        """
        commits = [
            Commit("A", "A\n"),
            Commit("B", "B\n"),
            Commit("C", "C\n"),
        ]
        tags = [
            Tag("0.0.1", commits[0]),
            Tag("1.0.0", commits[1])
        ]

        def iter_commits(branch):
            return iter(reversed(commits))

        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=None,
        )

        repo = Repository(None)
        repo.repo = test_repo_instance
        repo.tag_lookup(increase_pre_release=True)
        repo.find_relevant_commits()
        repo.increase_pre_release("rc")
        self.assertIsNot("Nonerc1", repo.new_version)
        self.assertEqual("1.0.1rc1", repo.new_version)

    def test_default_versioning_previous_is_pre_release(self):
        """
        --A-----B-------C --master
          |     |       |
        0.0.1 0.0.2rc1  ? <- 0.0.2
        """
        commits = [
            Commit("A", "A\n"),
            Commit("B", "B\n"),
            Commit("C", "C\n"),
        ]
        tags = [
            Tag("0.0.1", commits[0]),
            Tag("0.0.2rc1", commits[1]),
        ]

        def iter_commits(branch):
            return iter(reversed(commits))

        test_repo_instance = Namespace(
            tags=tags,
            commits=reversed(commits),
            iter_commits=iter_commits,
            active_branch=None,
        )

        repo = Repository(None)
        repo.repo = test_repo_instance
        repo.tag_lookup()
        repo.find_relevant_commits()
        repo.increase_version()
        self.assertEqual("0.0.2", repo.new_version)


if __name__ == '__main__':
    unittest.main()
