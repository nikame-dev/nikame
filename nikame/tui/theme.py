
# NIKAME "Amber Core" Design System
# Adapted from ui_ux.md specification

COLORS: dict[str, str] = {
    # Brand Colors
    "accent": "#D4933A",
    "accent_dim": "#8B6025",
    "accent_glow": "#F0B55A",
    
    # Semantic Colors
    "success": "#5A9E6F",
    "warning": "#C4933A",
    "danger": "#B85450",
    "info": "#5A7FA3",
    
    # Neutrals
    "background": "#121212",   # Deep Charcoal
    "surface": "#1E1E1E",      # Subtle elevation
    "panel_bg": "#161616",     # Panel background
    
    # Text
    "text_primary": "#E8E0D0",   # Warm white
    "text_secondary": "#8A8070", # Muted taupe
    "text_muted": "#524B40",    # Dark taupe
    "text_accent": "#D4933A",   # Amber text
}


# CSS Variables for Textual
CSS_VARIABLES = {
    "primary": COLORS["accent"],
    "primary-lighten-1": COLORS["accent_glow"],
    "primary-darken-1": COLORS["accent_dim"],
    "background": COLORS["background"],
    "surface": COLORS["surface"],
    "panel": COLORS["panel_bg"],
    "success": COLORS["success"],
    "warning": COLORS["warning"],
    "error": COLORS["danger"],
}


def get_css_variables_str() -> str:
    """Returns CSS variable definitions for Textual stylesheets."""
    lines = [f"${name}: {value};" for name, value in CSS_VARIABLES.items()]
    return "\n".join(lines)
