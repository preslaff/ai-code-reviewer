# -------------------------------------------
# File: setup.py
# -------------------------------------------
from setuptools import setup, find_packages

setup(
    name="ai-code-reviewer",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "langgraph",
        "langchain",
        "openai",
        "PyGithub",
        "python-dotenv"
    ],
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "ai-review=langgraph_agent.agent:main"
        ]
    },
)
