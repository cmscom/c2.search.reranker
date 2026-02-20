"""Shim for zc.buildout compatibility.

All configuration is in pyproject.toml.
"""

from setuptools import setup

setup(
    python_requires=">=3.8,<3.14",
)
