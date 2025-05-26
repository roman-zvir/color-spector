import tkinter as tk
from tkinter import ttk
import pyautogui
import webcolors
from PIL import Image, ImageTk
import pyperclip
from functools import partial
import logging
import sys
import platform

# Set up logging for error tracking
logging.basicConfig(filename="ColorSpector.log", level=logging.ERROR, 
                    format="%(asctime)s - %(levelname)s - %(message)s")

# Precompute CSS3 color data once - handle different webcolors versions
# This ensures compatibility across different versions of the webcolors library
try:
    # Try the newer webcolors API first
    CSS3_COLORS = [(webcolors.hex_to_rgb(hex_code), name)
                   for hex_code, name in webcolors.CSS3_HEX_TO_NAMES.items()]
except AttributeError:
    # Fallback for older webcolors versions
    try:
        CSS3_COLORS = [(webcolors.hex_to_rgb(hex_code), name)
                       for name, hex_code in webcolors.css3_hex_to_names.items()]
    except AttributeError:
        # If neither works, use a minimal color set as last resort
        CSS3_COLORS = [
            ((255, 255, 255), "white"),
            ((0, 0, 0), "black"),
            ((255, 0, 0), "red"),
            ((0, 255, 0), "lime"),
            ((0, 0, 255), "blue"),
            ((255, 255, 0), "yellow"),
            ((255, 0, 255), "magenta"),
            ((0, 255, 255), "cyan"),
        ]

class ColorProcessor:
    """Handles color detection, conversion, and matching logic"""
    
    def __init__(self):
        # Color detection state management
        self.frozen = False  # Whether color detection is paused
        self.current_rgb = (255, 255, 255)  # Current RGB values
        self.current_hex = "#FFFFFF"  # Current hex color code
        self.current_name = "White"  # Current color name
        
    def get_pixel_color(self, x, y):
        """Get RGB color at specific screen coordinates
        
        Args:
            x (int): X coordinate on screen
            y (int): Y coordinate on screen
            
        Returns:
            tuple: RGB color values (r, g, b)
            
        Raises:
            pyautogui.FailSafeException: When fail-safe is triggered
            Exception: For other screen capture errors
        """
        try:
            return pyautogui.pixel(x, y)
        except pyautogui.FailSafeException:
            logging.error("PyAutoGUI fail-safe triggered.")
            raise
        except Exception as e:
            logging.error(f"Error getting pixel color: {str(e)}")
            raise
    
    def rgb_to_hex(self, rgb):
        """Convert RGB tuple to hex string
        
        Args:
            rgb (tuple): RGB values (r, g, b)
            
        Returns:
            str: Hex color code in format #RRGGBB
        """
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    
    def closest_color_name(self, requested_rgb):
        """Find the closest CSS3 color name for the given RGB values
        Uses Euclidean distance in RGB space to find the best match
        
        Args:
            requested_rgb (tuple): RGB values to match
            
        Returns:
            str: Name of the closest CSS3 color
        """
        min_distance = float('inf')
        closest_name = ""
        # Calculate distance to each CSS3 color using Euclidean distance formula
        for rgb, name in CSS3_COLORS:
            distance = sum((c1 - c2) ** 2 for c1, c2 in zip(rgb, requested_rgb))
            if distance < min_distance:
                min_distance, closest_name = distance, name
        return closest_name
    
    def get_color_name(self, rgb):
        """Get the proper color name, falling back to closest match
        
        Args:
            rgb (tuple): RGB values
            
        Returns:
            str: Color name (exact match or closest approximation)
        """
        try:
            # Try to get exact color name first
            return webcolors.rgb_to_name(rgb).title()
        except ValueError:
            # Fall back to closest color approximation
            return self.closest_color_name(rgb).title()
    
    def update_current_color(self, rgb, hex_code):
        """Update the current color state with new values
        
        Args:
            rgb (tuple): RGB color values
            hex_code (str): Hex color code
        """
        self.current_rgb = rgb
        self.current_hex = hex_code.upper()
        self.current_name = self.get_color_name(rgb)
    
    def toggle_freeze(self):
        """Toggle the frozen state of color detection
        
        Returns:
            bool: New frozen state
        """
        self.frozen = not self.frozen
        return self.frozen

class ColorHistory:
    """Manages color history functionality"""
    
    def __init__(self, max_colors=8):
        # History configuration
        self.max_colors = max_colors  # Maximum number of colors to store
        self.history = []  # List of hex color codes in chronological order
        
        # UI components
        self.swatch_buttons = []  # Color swatch buttons for display
        self.history_frame = None  # Container frame for history UI
        self.bg_light = "#313145"  # Default background color for empty swatches
    
    def setup_ui(self, parent_frame, bg_light):
        """Setup the history UI components
        
        Args:
            parent_frame: Parent tkinter frame to contain history UI
            bg_light (str): Background color for empty swatches
        """
        self.bg_light = bg_light
        
        # Create container for history section
        history_container = ttk.Frame(parent_frame, padding=(0, 15, 0, 0))
        history_container.pack(fill=tk.X)
        
        # Add section title
        ttk.Label(history_container, text="COLOR HISTORY", style="Title.TLabel").pack(anchor=tk.W)
        
        # Create frame for color swatches
        self.history_frame = ttk.Frame(history_container, style="History.TFrame")
        self.history_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Create individual color swatch buttons
        self.swatch_buttons = []
        for i in range(self.max_colors):
            swatch = tk.Button(self.history_frame, width=4, height=2, bd=0,
                              bg=self.bg_light, activebackground=self.bg_light)
            swatch.pack(side=tk.LEFT, padx=2, pady=2)
            self.swatch_buttons.append(swatch)
    
    def add_color(self, hex_code):
        """Add a color to history (if it's not already the most recent)
        
        Args:
            hex_code (str): Hex color code to add to history
        """
        # Only add if it's different from the most recent color
        if not self.history or self.history[0] != hex_code:
            self.history.insert(0, hex_code)  # Add to front of list
            self.history = self.history[:self.max_colors]  # Trim to max size
            self.update_swatches()  # Refresh visual display
    
    def update_swatches(self):
        """Update the visual representation of color swatches"""
        for i, swatch in enumerate(self.swatch_buttons):
            if i < len(self.history):
                # Show stored color
                color = self.history[i]
                swatch.config(bg=color, activebackground=color)
            else:
                # Show empty swatch with default background
                swatch.config(bg=self.bg_light, activebackground=self.bg_light)
                swatch.config(command=None)  # Remove click handler for empty swatches
    
    def bind_swatch_callbacks(self, callback):
        """Bind click callbacks to history swatches
        
        Args:
            callback: Function to call when a swatch is clicked, receives color as argument
        """
        for i, swatch in enumerate(self.swatch_buttons):
            if i < len(self.history):
                color = self.history[i]
                # Use partial to bind the specific color to each swatch
                swatch.config(command=partial(callback, color))

class ColorDetectorApp:
    """Main application class that coordinates UI and functionality"""
    
    def __init__(self, root):
        # Basic window setup
        self.root = root
        self.root.title("ColorSpector")
        self.root.geometry("555x380")
        self.root.minsize(450, 320)

        # Initialize core components
        self.color_processor = ColorProcessor()  # Handles color detection and processing
        self.color_history = ColorHistory()  # Manages color history
        
        # OS-specific setup
        self.os_name = platform.system()
        self._setup_os_specific()
        
        # Define application theme colors
        self.bg_dark = "#1e1e2e"        # Main background
        self.bg_medium = "#282838"       # Panel backgrounds
        self.bg_light = "#313145"        # Highlight/accent backgrounds
        self.text_primary = "#ffffff"    # Primary text color
        self.text_secondary = "#a0a0c0"  # Secondary/muted text
        self.accent = "#7d56f4"          # Accent color for buttons/highlights
        
        # Apply theme to root window
        self.root.configure(bg=self.bg_dark)
        
        # Initialize UI and start application
        self.setup_ui()
        self._load_icon()
        self._setup_key_bindings()
        self.check_pyautogui_support()
        
        # Start the main color detection loop
        self.update_color()
    
    def _setup_os_specific(self):
        """Handle OS-specific setup and optimizations"""
        if self.os_name == "Windows":
            try:
                # Enable DPI awareness on Windows for crisp display
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                # Silently fail if DPI awareness can't be set
                pass
    
    def _load_icon(self):
        """Load and set application icon from file"""
        try:
            icon = Image.open("icon.png")
            self.icon = ImageTk.PhotoImage(icon)
            self.root.iconphoto(False, self.icon)
        except Exception as e:
            # Log error but don't crash if icon can't be loaded
            logging.error(f"Error loading icon: {str(e)}")
    
    def _setup_key_bindings(self):
        """Setup keyboard shortcuts for common actions"""
        self.root.bind('<Control-c>', self.copy_color)  # Ctrl+C to copy color
        self.root.bind('<Control-f>', self.toggle_freeze)  # Ctrl+F to freeze/unfreeze
    
    def check_pyautogui_support(self):
        """Check if screen capture is supported on this system"""
        try:
            # Test screenshot capability
            _ = pyautogui.screenshot()
        except Exception as e:
            # Show error message to user if screen capture fails
            self.status_bar.config(
                text="Screen capture not supported or permissions missing. "
                     "Please check OS permissions."
            )
            logging.error(f"Screen capture not supported: {e}")

    def setup_ui(self):
        """Setup the main user interface components"""
        # Configure visual styles first
        self._configure_styles()
        
        # Create main container frame
        main_frame = ttk.Frame(self.root, padding=(20, 15))
        main_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        # Build UI sections
        self._create_title_section(main_frame)
        self._create_content_section(main_frame)
        
        # Setup color history UI
        self.color_history.setup_ui(main_frame, self.bg_light)
        
        # Create status bar at bottom
        self.status_bar = ttk.Label(self.root, text="Point your cursor anywhere to detect colors...",
                                    style="Status.TLabel", padding=(10, 5))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _configure_styles(self):
        """Configure TTK styles for consistent theming across the application"""
        self.style = ttk.Style()
        self.style.theme_use('clam')  # Use clam theme as base

        # Define fonts with cross-platform compatibility
        default_font = ("TkDefaultFont", 10)
        bold_font = ("TkDefaultFont", 10, "bold")
        # Use system-appropriate monospace font
        mono_font = ("Courier New", 11) if self.os_name == "Windows" else ("Monospace", 11)

        # Configure component styles with theme colors
        self.style.configure("TFrame", background=self.bg_medium)
        self.style.configure("TLabel", background=self.bg_medium, foreground=self.text_primary, font=default_font)
        self.style.configure("Title.TLabel", font=bold_font, foreground=self.text_secondary)
        self.style.configure("Color.TLabel", font=mono_font, foreground=self.text_primary)
        self.style.configure("Status.TLabel", background=self.bg_dark, foreground=self.text_primary, font=("TkDefaultFont", 9))
        self.style.configure("Accent.TButton", background=self.accent, foreground=self.text_primary)
        
        # Configure button hover and press states
        self.style.map("Accent.TButton",
                      background=[('active', self.accent)],
                      relief=[('pressed', 'sunken')])
        self.style.configure("History.TFrame", background=self.bg_light)
    
    def _create_title_section(self, parent):
        """Create the title and freeze button section
        
        Args:
            parent: Parent frame to contain this section
        """
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill=tk.X, pady=(0, 15))

        # Application title on the left
        app_title = ttk.Label(title_frame, 
                             text="ColorSpector", 
                             font=("TkDefaultFont", 16, "bold"),
                             foreground=self.accent)
        app_title.pack(side=tk.LEFT)

        # Freeze/Unfreeze button on the right
        self.freeze_var = tk.StringVar(value="Freeze Color")
        self.freeze_btn = ttk.Button(title_frame, 
                                    textvariable=self.freeze_var,
                                    command=self.toggle_freeze,
                                    style="Accent.TButton",
                                    width=12)
        self.freeze_btn.pack(side=tk.RIGHT)
    
    def _create_content_section(self, parent):
        """Create the main content area with preview and info
        
        Args:
            parent: Parent frame to contain this section
        """
        content_frame = ttk.Frame(parent)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side: Color preview
        self._create_preview_section(content_frame)
        
        # Right side: Color information and controls
        self._create_info_section(content_frame)
    
    def _create_preview_section(self, parent):
        """Create the color preview section with circular color display
        
        Args:
            parent: Parent frame to contain this section
        """
        preview_frame = ttk.Frame(parent, padding=(0, 0, 15, 0))
        preview_frame.pack(side=tk.LEFT, fill=tk.BOTH)

        # Canvas for drawing the color circle
        self.color_preview = tk.Canvas(preview_frame, 
                                      width=140, 
                                      height=140,
                                      highlightthickness=0, 
                                      bg=self.bg_medium)
        # Create the color preview circle
        self.preview_oval = self.color_preview.create_oval(10, 10, 130, 130,
                                                          fill="#ffffff",
                                                          outline=self.bg_light,
                                                          width=2)
        self.color_preview.pack(pady=5)

        # Section label
        ttk.Label(preview_frame, 
                 text="COLOR PREVIEW", 
                 style="Title.TLabel"
                ).pack(pady=(5, 0))
    
    def _create_info_section(self, parent):
        """Create the color information section with copy buttons
        
        Args:
            parent: Parent frame to contain this section
        """
        info_frame = ttk.Frame(parent, padding=(5))
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Define info rows with their copy functions
        labels_with_copy = [
            ("COLOR NAME", "name_label", lambda: self.safe_copy(self.color_processor.current_name)),
            ("HEX CODE", "hex_label", lambda: self.safe_copy(self.color_processor.current_hex)),
            ("RGB VALUES", "rgb_label", lambda: self.safe_copy(f"{self.color_processor.current_rgb[0]}, {self.color_processor.current_rgb[1]}, {self.color_processor.current_rgb[2]}"))
        ]

        # Create each info row
        for idx, (title, var_name, copy_func) in enumerate(labels_with_copy):
            frame = ttk.Frame(info_frame)
            frame.pack(fill=tk.X, pady=5)

            # Section title on the left
            ttk.Label(frame, text=title, style="Title.TLabel").pack(side=tk.LEFT, anchor=tk.W)

            # Copy button on the right
            copy_btn = ttk.Button(frame, text="Copy", command=copy_func, width=6)
            copy_btn.pack(side=tk.RIGHT, padx=(10, 0))

            # Value label next to copy button
            label = ttk.Label(frame, text="—", style="Color.TLabel")
            label.pack(side=tk.RIGHT)
            # Store reference to label for later updates
            setattr(self, var_name, label)

    def safe_copy(self, text):
        """Safely copy text to clipboard with error handling
        
        Args:
            text (str): Text to copy to clipboard
        """
        try:
            pyperclip.copy(text)
            self.status_bar.config(text=f"Copied '{text}' to clipboard.")
        except Exception:
            # Handle clipboard errors (common on Linux without xclip/xsel)
            self.status_bar.config(text="Clipboard copy failed. Is xclip or xsel installed?")

    def toggle_freeze(self, event=None):
        """Toggle color detection freeze state
        
        Args:
            event: Optional event object (for keyboard shortcuts)
        """
        frozen = self.color_processor.toggle_freeze()
        if frozen:
            # Update UI for frozen state
            self.freeze_var.set("Unfreeze")
            self.status_bar.config(text="Color frozen. Click 'Unfreeze' to continue detecting.")
            # Add current color to history and enable swatch clicking
            self.color_history.add_color(self.color_processor.current_hex)
            self.color_history.bind_swatch_callbacks(self.select_history_color)
        else:
            # Update UI for active detection state
            self.freeze_var.set("Freeze Color")
            self.status_bar.config(text="Point your cursor anywhere to detect colors...")

    def copy_color(self, event=None):
        """Copy current color name to clipboard
        
        Args:
            event: Optional event object (for keyboard shortcuts)
        """
        self.safe_copy(self.color_processor.current_name)

    def select_history_color(self, hex_code):
        """Select a color from history and update current state
        
        Args:
            hex_code (str): Hex color code from history to select
        """
        # Convert hex to RGB for processing
        rgb = webcolors.hex_to_rgb(hex_code)
        # Update color processor state
        self.color_processor.update_current_color(rgb, hex_code)
        # Refresh UI with selected color
        self.update_ui_with_current_color()
        # Set to frozen state
        self.color_processor.frozen = True
        self.freeze_var.set("Unfreeze")
        self.status_bar.config(text=f"Selected color from history: {hex_code}")

    def update_ui_with_current_color(self):
        """Update all UI elements with current color information"""
        processor = self.color_processor
        
        # Update color preview circle
        self.color_preview.itemconfig(self.preview_oval, fill=processor.current_hex)
        # Update text labels with current color data
        self.name_label.config(text=processor.current_name)
        self.hex_label.config(text=processor.current_hex)
        # Format RGB values with consistent spacing
        self.rgb_label.config(text=f"{processor.current_rgb[0]:<3}, {processor.current_rgb[1]:<3}, {processor.current_rgb[2]:<3}")

    def update_color(self):
        """Main color detection loop - runs continuously"""
        if not self.color_processor.frozen:
            try:
                # Get current mouse position relative to screen
                x, y = self.root.winfo_pointerx(), self.root.winfo_pointery()
                # Sample pixel color at mouse position
                rgb = self.color_processor.get_pixel_color(x, y)
                hex_code = self.color_processor.rgb_to_hex(rgb)

                # Update processor state and UI
                self.color_processor.update_current_color(rgb, hex_code)
                self.update_ui_with_current_color()
                # Show current coordinates in status bar
                self.status_bar.config(text=f"Detecting color at X: {x:4} Y: {y:4}")

            except pyautogui.FailSafeException:
                # Handle fail-safe activation (mouse in corner)
                self.status_bar.config(text="PyAutoGUI fail-safe triggered. Please check your cursor position.")
            except Exception as e:
                # Handle other detection errors
                self.status_bar.config(text="An error occurred while detecting the color.")

        # Schedule next update (20 FPS for smooth detection)
        self.root.after(50, self.update_color)


if __name__ == "__main__":
    # Create and run the application
    root = tk.Tk()
    app = ColorDetectorApp(root)
    root.mainloop()
