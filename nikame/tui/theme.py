
# NIKAME "Amber Core" Design System - v2.1 (OpenCode Refinement)
# Optimized for high-density, keyboard-driven terminal interfaces.

COLORS: dict[str, str] = {
    # Brand Colors (Vibrant Neon Amber)
    "accent": "#FFA500",      # Pure Orange/Amber
    "accent_dim": "#4D3300",  # Deep Burned Orange
    "accent_glow": "#FFD27F", # Soft Glow
    
    # Semantic Colors
    "success": "#00FF7F",     # Spring Green
    "warning": "#FFD700",     # Gold
    "danger": "#FF4500",      # Orange Red
    "info": "#00BFFF",        # Deep Sky Blue
    
    # Neutrals (Deep Space Black)
    "background": "#0A0A0A",   # Absolute Dark
    "surface": "#121212",      # Low elevation
    "panel_bg": "#181818",     # Contrast panels
    "border": "#262626",       # Muted border
    
    # Text
    "text_primary": "#FFFFFF",   # Crisp white
    "text_secondary": "#B0B0B0", # Silver
    "text_muted": "#555555",    # Dark Grey
    "text_accent": "#FFA500",   # Amber highlight
}


# CSS Variables for Textual
CSS_VARIABLES = {
    "primary": COLORS["accent"],
    "primary-lighten-1": COLORS["accent_glow"],
    "primary-darken-1": COLORS["accent_dim"],
    "background": COLORS["background"],
    "surface": COLORS["surface"],
    "panel": COLORS["panel_bg"],
    "border": COLORS["border"],
    "success": COLORS["success"],
    "warning": COLORS["warning"],
    "error": COLORS["danger"],
    "text-primary": COLORS["text_primary"],
    "text-secondary": COLORS["text_secondary"],
    "text-muted": COLORS["text_muted"],
    "text-accent": COLORS["text_accent"],
}


def get_css_variables_str() -> str:
    """Returns CSS variable definitions for Textual stylesheets."""
    lines = [f"${name}: {value};" for name, value in CSS_VARIABLES.items()]
    return "\n".join(lines)
