# my_plot_style.py

import matplotlib.pyplot as plt
import seaborn as sns
# No need for numpy in this style file itself, unless the setup function used it directly

# --- CUSTOM MOVIE GENRE COLORS (Exportable) ---
MOVIE_GENRES = [
    'Drama', 'Comedy', 'Documentary', 'Romance', 'Action',
    'Crime', 'Thriller', 'Horror', 'Adventure', 'Mystery'
]

GENRE_COLORS_HEX = [
    '#003f5c', # Drama: Deep Blue
    '#f9a602', # Comedy: Bright Orange-Yellow
    '#7a7a7a', # Documentary: Medium Gray
    '#ff7b9c', # Romance: Soft Pink
    '#ef562f', # Action: Vibrant Orange-Red
    '#2f4f4f', # Crime: Dark Slate Gray (almost black)
    '#008080', # Thriller: Teal
    '#8b0000', # Horror: Deep Red
    '#556b2f', # Adventure: Dark Olive Green
    '#6a0dad', # Mystery: Rich Purple
]

GENRE_COLOR_MAP = dict(zip(MOVIE_GENRES, GENRE_COLORS_HEX))

# --- TEMPLATE SETTINGS FUNCTION (Exportable) ---
def activate_plot_style():
    """
    Applies a set of styling rules for publication-quality plots,
    including a custom movie genre color palette.
    Call this function once at the beginning of your script/notebook.
    """
    # Use a seaborn style for a good base
    plt.style.use('seaborn-v0_8-whitegrid') # Or 'seaborn-v0_8-ticks' for less prominent grid

    # Set the custom color palette as the default
    sns.set_palette(GENRE_COLORS_HEX)

    # --- Matplotlib rcParams for fine-tuning ---
    plt.rcParams.update({
        # Font settings
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'], # Common sans-serif fonts
        'font.size': 10,                   # Base font size for text elements
        'axes.titlesize': 14,              # Title font size (for individual subplots)
        'axes.labelsize': 12,              # X and Y axis label font size
        'xtick.labelsize': 9,             # X-tick label font size
        'ytick.labelsize': 9,             # Y-tick label font size
        'legend.fontsize': 9,              # Legend font size
        'figure.titlesize': 16,            # Figure suptitle font size (for the whole figure)

        # Text colors (ensure high contrast)
        'text.color': 'black',             # Default text color
        'axes.labelcolor': 'black',        # Axis labels
        'xtick.color': 'black',            # X tick labels and ticks
        'ytick.color': 'black',            # Y tick labels and ticks
        'axes.titlecolor': 'black',        # Title color for subplots

        # Line and marker settings
        'lines.linewidth': 1.5,
        'lines.markersize': 5,

        # Axes settings
        'axes.labelpad': 8.0,              # Padding for axis labels
        'axes.titlepad': 12.0,             # Padding for subplot title
        'axes.grid': True,                 # Enable grid
        'grid.color': '#cccccc',           # Light gray grid lines
        'grid.linestyle': '--',            # Dashed grid lines
        'grid.linewidth': 0.5,             # Thinner grid lines
        'grid.alpha': 0.7,                 # Slightly transparent grid

        # Figure settings
        'figure.dpi': 100,                 # Good for screen; increase for print if saving directly
        'figure.facecolor': 'white',
        'savefig.dpi': 300,                # Default DPI for saving figures
        'savefig.bbox': 'tight',           # Remove excess whitespace
        'savefig.pad_inches': 0.05,        # Minimal padding around saved figure

        # Legend settings
        'legend.frameon': False,           # Cleaner look without legend frame by default
        'legend.loc': 'best',
    })
    print("Custom plot style 'publication_quality_plots' applied.")

# --- Optional: A function to reset to Matplotlib defaults if needed ---
def reset_plot_style():
    """Resets Matplotlib to its default settings."""
    plt.rcdefaults()
    # You might need to reset seaborn styles too if you used sns.set_theme() extensively
    # For this setup, plt.rcdefaults() and then re-applying a base seaborn style is often enough
    sns.set_theme() # Resets to seaborn's defaults
    print("Plot style reset to Matplotlib/Seaborn defaults.")

if __name__ == '__main__':
    # This block runs if you execute my_plot_style.py directly
    # Good for testing the style module
    print("Testing 'my_plot_style.py'...")
    activate_plot_style()

    # Create a quick test plot
    x_test = [1, 2, 3, 4, 5]
    y_test1 = [1, 3, 2, 4, 3]
    y_test2 = [3, 1, 4, 2, 5]

    plt.figure(figsize=(6, 4))
    plt.plot(x_test, y_test1, label='Sample A')
    plt.plot(x_test, y_test2, label='Sample B', linestyle='--')
    plt.title('Test Plot with Custom Style')
    plt.xlabel('X-axis')
    plt.ylabel('Y-axis')
    plt.legend()
    sns.despine()
    plt.tight_layout()
    plt.show()

    print("\nAvailable colors from this module:")
    print(f"GENRE_COLORS_HEX: {GENRE_COLORS_HEX}")
    print(f"GENRE_COLOR_MAP for 'Drama': {GENRE_COLOR_MAP.get('Drama')}")

    reset_plot_style() # Example of resetting
    plt.figure(figsize=(6,4))
    plt.plot(x_test, y_test1, label='Sample A - Default Style')
    plt.title('Test Plot with Default Style (After Reset)')
    plt.show()