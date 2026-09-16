"""Tiny ipywidgets wrapper so selection dropdowns don't clutter the notebook."""

import ipywidgets as widgets
from IPython.display import display


def make_dropdown(options, description):
    """Create, display, and return a dropdown; read the current choice via `.value`."""
    dd = widgets.Dropdown(
        options=options,
        value=options[0],
        description=description,
        style={'description_width': 'initial'},
    )
    display(dd)
    return dd
