"""Industrial dark palette for the Echo UI.

Single source of truth for colour literals. `TranscriberApp` maps these into the
legacy `self.<name>_color` attributes so every widget builder keeps working
unchanged.
"""

COLORS = {
    "bg": "#252525",
    "panel": "#303030",
    "panel_dark": "#1D1D1D",
    "accent": "#F2A900",
    "accent_dark": "#B87900",
    "text": "#E6E6E6",
    "muted": "#929292",
    "success": "#7DBE3C",
    "error": "#D9534F",
}
