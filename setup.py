from setuptools import setup, find_packages

with open("README.md", "r") as file:
    long_description = file.read()

setup(
    name="spock",
    version="0.0.1",
    author="Team Vulcan",
    author_email="",
    description="A package to allow developers to control Spotify from common tools like the command line and vim.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MJez29/spock",
    packages=find_packages(),
)
