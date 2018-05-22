"""Python setup script.  """
import os
from setuptools import setup, find_packages

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
        'wlf>=0.3.4',
        'cgtwq>=1.2.0',
    ],
    dependency_links=[
        ('https://github.com/WuLiFang/wlf/archive/0.3.4.tar.gz'
         '#egg=wlf-0.3.4'),
        ('https://github.com/WuLiFang/cgtwq/archive/1.3.2.tar.gz'
         '#egg=cgtwq-1.3.2'),
    ],
)
