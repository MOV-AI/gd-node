"""Configuration file for the Sphinx documentation builder.

For the full list of built-in configuration values, see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html

"""

import os
import sys
from typing import List

sys.path.insert(0, os.path.abspath("../.."))

# pylint: disable=redefined-builtin
# pylint: disable=invalid-name

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'GD Node'
copyright = '2024, MOV.AI'
author = 'MOV.AI'
version = os.getenv("VERSION", default="TODO")

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions: List[str] = [
    "sphinx.ext.autodoc",  # Include documentation from docstrings
    "sphinx.ext.napoleon",  # Add support for Google style docstrings
    "sphinx.ext.todo",  # Catch and show TODOs within docstrings
    "sphinx_mdinclude",  # Markdown to rst
    "sphinx.ext.inheritance_diagram",  # Classes inheritance diagram
]

# display TODOs
todo_include_todos = True

templates_path = ["_templates"]
exclude_patterns: List[str] = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
html_theme = "sphinx_rtd_theme"
html_favicon = "_static/cropped-Mov.ai-favicon2-32x32.png"
html_static_path = ["_static"]
html_js_files = ["versions.js"]

html_context = {}
# used in versions.html
html_context["current_version"] = version

# -- Theme options -----------------------------------------------------------
# https://sphinx-rtd-theme.readthedocs.io/en/latest/configuring.html#configuration
html_context["display_github"] = True
html_context["github_user"] = "MOV-AI"
html_context["github_repo"] = "gd-node"
branch = version if version == "main" else f"{version}"
html_context["github_version"] = f"{branch}/docs/source/"
