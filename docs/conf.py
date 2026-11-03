"""Sphinx/PyData documentation; gallery examples run without provider requests."""
from energyclimates import __version__

project = "EnergyClimates"
author = "ASVA Consulting and EnergyClimates contributors"
copyright = "2026, ASVA Consulting and EnergyClimates contributors"
release = version = __version__
extensions = [
    "sphinx.ext.autodoc", "sphinx.ext.autosummary", "sphinx.ext.napoleon",
    "sphinx.ext.mathjax", "sphinx.ext.viewcode", "sphinx.ext.githubpages",
    "myst_parser", "sphinx_design", "sphinx_gallery.gen_gallery",
]
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
exclude_patterns = ["_build", "_generated", ".DS_Store"]
autodoc_typehints = "description"
autodoc_member_order = "bysource"
myst_enable_extensions = ["colon_fence", "dollarmath"]
myst_heading_anchors = 4
html_theme = "pydata_sphinx_theme"
html_title = project
html_static_path = ["_static"]
html_css_files = ["energyclimates.css"]
html_show_sourcelink = False
html_baseurl = "https://julianascencio.github.io/energyclimates/"
html_theme_options = {
    "github_url": "https://github.com/julianascencio/energyclimates",
    "navbar_align": "left", "show_prev_next": False, "show_toc_level": 2,
    "navigation_depth": 3, "header_links_before_dropdown": 6,
    "logo": {"text": "EnergyClimates"},
}
sphinx_gallery_conf = {
    "examples_dirs": "../examples/gallery", "gallery_dirs": "auto_examples",
    "filename_pattern": r"/plot_", "download_all_examples": False,
    "abort_on_example_error": True, "remove_config_comments": True,
    "within_subsection_order": "FileNameSortKey", "reference_url": {},
    "capture_repr": (),
}
