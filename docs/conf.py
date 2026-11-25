# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import suricata_check_mcp

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "suricata-check-mcp"
copyright = "2026, Koen Teuwen"
author = "Koen Teuwen"

# Version / release information
version = suricata_check_mcp.__version__.split("+")[0]
release = suricata_check_mcp.__version__.split("+")[0]

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
    "autoapi.extension",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_sitemap",
    "sphinx_copybutton",
    "sphinxext.opengraph",
]

templates_path = ["_templates"]
source_suffix = [".rst", ".md"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master", None),
    "suricata-check": ("https://suricata-check.teuwen.net/", None),
}

root_doc = "index"
master_doc = "index"

suppress_warnings = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_theme_options = {}
html_favicon = "https://docs.readthedocs.io/favicon.ico"

html_js_files = ["js/script.js"]

# -- Options for MyST     -------------------------------------------------
# https://myst-parser.readthedocs.io/en/latest/

myst_enable_extensions = ["linkify"]
myst_heading_anchors = 5
# -- Options for AutoAPI     -------------------------------------------------
# https://sphinx-autoapi.readthedocs.io/en/latest/index.html

autoapi_dirs = ["../suricata_check_mcp"]
autoapi_options = [
    "members",
    "show-inheritance",
    "show-module-summary",
    "special-members",
    "imported-members",
    "undoc-members",
]
autoapi_add_toctree_entry = False
autoapi_python_class_content = "both"
autoapi_member_order = "groupwise"
autoapi_own_page_level = "module"

# -- Options for viewcode     -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/viewcode.html

viewcode_line_numbers = True

# -- Options for sphinx-sitemap    -------------------------------------------------
# https://sphinx-sitemap.readthedocs.io/en/latest/index.html

html_baseurl = "https://suricata-check-mcp.teuwen.net/"
sitemap_url_scheme = "{link}"
sitemap_locales = ["en"]
sitemap_excludes = ["search.html", "genindex.html"]
html_extra_path = ["robots.txt"]
