"""Python setup script.  """
import os

from setuptools import find_packages, setup

__about__ = {}
with open(os.path.join(os.path.dirname(__file__),
                       'cgtwq_uploader', '__about__.py')) as f:
    exec(f.read(), __about__)  # pylint: disable=exec-used

setup(
    name='cgtwq_uploader',
    version=__about__['__version__'],
    author=__about__['__author__'],
    packages=find_packages(),
    package_data={'': ['*.ui']},
    install_requires=[
        'wlf @ git+https://github.com/WuLiFang/wlf@0.5.3',
        'cgtwq @ git+https://github.com/WuLiFang/cgtwq@3.0.0-alpha.8',
        'Qt.py~=1.1'
    ],
)
