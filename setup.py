"""Python setup script.  """
import os

from setuptools import find_packages, setup

__about__ = {}
execfile(os.path.join(os.path.dirname(__file__),
                      'cgtwq_uploader', '__about__.py'), __about__)

setup(
    name='cgtwq_uploader',
    version=__about__['__version__'],
    author=__about__['__author__'],
    packages=find_packages(),
    package_data={'': ['*.ui']},
    install_requires=[
        'wlf~=0.5',
        'cgtwq~=3.0',
        'Qt.py~=1.1'
    ],
    dependency_links=[
        ('https://github.com/WuLiFang/wlf/archive/0.5.0.tar.gz'
         '#egg=wlf-0.5.0'),
        ('https://github.com/WuLiFang/cgtwq/archive/3.0.0-alpha.0.tar.gz'
         '#egg=cgtwq-3.0.0-alpha.0'),
    ],
)
