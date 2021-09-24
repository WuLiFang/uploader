import codecs

from setuptools import setup, find_packages

with codecs.open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with codecs.open("VERSION", "r", encoding="utf-8") as fh:
    version = fh.read().strip()


setup(
    name="cgtwq_uploader",
    version=version,
    packages=find_packages(),
    description="Uploader application for CGTeamwork.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="NateScarlet",
    author_email="NateScarlet@Gmail.com",
    classifiers=[
        "Private :: Do Not Upload",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    url="https://github.com/WuLiFang/cgtwq",
    install_requires=[
        "Qt.py~=1.1",
        "cgtwq~=3.3",
        "wlf~=0.6",
    ],
    include_package_data=True,
)
