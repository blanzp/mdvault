from setuptools import setup, find_packages

setup(
    name="mdvault",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "rich>=10.0.0",
        "prompt-toolkit>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "mdvault=mdvault.cli:cli",
        ],
    },
    author="Paul Blanz",
    description="A CLI tool for managing markdown note repositories",
    python_requires=">=3.8",
)
