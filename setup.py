import sys
import logging
import subprocess
from setuptools import setup, find_packages

try:
    __version__ = subprocess.check_output(("git", "describe", "--always", "--tags",
                                           "--match", "[0-9].?*",
                                           "--match", "[0-9][0-9].?*",
                                           "--match", "[0-9][0-9][0-9].?*"), text=True).rstrip()
except (subprocess.CalledProcessError, FileNotFoundError):
    logging.exception("Git version not available")
    __version__ = "0.0.1"


def disable_publisher():
    blacklist = ['register', 'upload']
    for command in blacklist:
        if command in sys.argv:
            raise SystemExit('Command "{}" has been blacklisted'.format(command))


metadata = dict(
    name='git-versionify',
    version=__version__,
    author='bromiesTM',
    author_email='78687674+bromiesTM@users.noreply.github.com ',
    url='https://github.com/bromiesTM/git-versionify.git',
    description='semantic git versioning tool',
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown; charset=UTF-8",
    packages=find_packages(exclude=["tests", "docs"]),
    entry_points={
        'console_scripts': ['git-versionify=versionify.versionify_main:argparse_main',
                            'versionify=versionify.versionify_main:argparse_main'],
    },
    include_package_data=True,
    zip_safe=True,
    platforms=['any'],
    install_requires=[req for req in open('requirements.txt').read().split() if not str(req).startswith('#')],
    python_requires=">=3.8",
)

disable_publisher()
setup(**metadata)
