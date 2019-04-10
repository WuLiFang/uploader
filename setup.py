"""Python setup script.  """
import os
import runpy

from setuptools import find_packages, setup

__about__ = runpy.run_path(
    os.path.join(os.path.dirname(__file__), 'cgtwq_uploader', '__about__.py'))

setup(
    name='cgtwq_uploader',
    version=__about__['__version__'],
    author=__about__['__author__'],
    packages=find_packages(),
    package_data={'': ['*.ui']},
    install_requires=[
        'wlf @ https://github.com/WuLiFang/wlf/archive/v0.6.0.tar.gz',
        'cgtwq @ https://github.com/WuLiFang/cgtwq/archive/3.0.0-alpha.8.tar.gz',
        'Qt.py~=1.1'
    ],
)
