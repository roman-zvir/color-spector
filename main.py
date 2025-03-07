import tkinter as tk
from tkinter import ttk
import pyautogui
import webcolors
from PIL import Image, ImageTk
import pyperclip
from functools import partial
import logging

# Set up logging
logging.basicConfig(filename="ColorSpector.log", level=logging.ERROR, 
                    format="%(asctime)s - %(levelname)s - %(message)s")

# Precompute CSS3 color data once
CSS3_COLORS = [(webcolors.hex_to_rgb(hex_code), name)
               for hex_code, name in webcolors.CSS3_HEX_TO_NAMES.items()]

class ColorDetectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ColorSpector")
        self.root.geometry("555x380")
        self.root.minsize(450, 320)

        # Initialize 'frozen' here
        self.frozen = False  # Add this line to initialize the 'frozen' variable


        # Define theme colors
        self.bg_dark = "#1e1e2e"        # Background
        self.bg_medium = "#282838"       # Panels
        self.bg_light = "#313145"        # Highlights
        self.text_primary = "#ffffff"    # Primary text
        self.text_secondary = "#a0a0c0"  # Secondary text
        self.accent = "#7d56f4"          # Accent color
        
        self.root.configure(bg=self.bg_dark)
        self.setup_ui()
        
        # App state variables
        self.frozen = False
        self.current_rgb = (255, 255, 255)
        self.current_hex = "#FFFFFF"
        self.current_name = "White"
        self.color_history = []
        
        # Load application icon
        try:
            icon = Image.open("icon.png")
            self.icon = ImageTk.PhotoImage(icon)
            self.root.iconphoto(False, self.icon)
        except Exception as e:
            logging.error(f"Error loading icon: {str(e)}")

        # Key bindings for copying and freezing
        self.root.bind('<Control-c>', self.copy_color)
        self.root.bind('<Control-f>', self.toggle_freeze)

    def setup_ui(self):
        # Configure custom theme style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Custom style configurations
        self.style.configure("TFrame", background=self.bg_medium)
        
        self.style.configure("TLabel", 
                            background=self.bg_medium, 
                            foreground=self.text_primary, 
                            font=("Segoe UI", 10))
                            
        self.style.configure("Title.TLabel", 
                            font=("Segoe UI", 10, "bold"),
                            foreground=self.text_secondary)
                            
        self.style.configure("Color.TLabel", 
                            font=("Consolas", 11),
                            foreground=self.text_primary)
                            
        self.style.configure("Status.TLabel", 
                            background=self.bg_dark,
                            foreground=self.text_primary, 
                            font=("Segoe UI", 9))
                            
        self.style.configure("Accent.TButton", 
                            background=self.accent,
                            foreground=self.text_primary)
                            
        self.style.map("Accent.TButton",
                      background=[('active', self.accent)],
                      relief=[('pressed', 'sunken')])
                      
        self.style.configure("History.TFrame",
                            background=self.bg_light)

        # Main container with padding
        main_frame = ttk.Frame(self.root, padding=(20, 15))
        main_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Top section with app title
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        app_title = ttk.Label(title_frame, 
                             text="ColorSpector", 
                             font=("Segoe UI", 16, "bold"),
                             foreground=self.accent)
        app_title.pack(side=tk.LEFT)

        # Freeze button
        self.freeze_var = tk.StringVar(value="Freeze Color")
        self.freeze_btn = ttk.Button(title_frame, 
                                    textvariable=self.freeze_var,
                                    command=self.toggle_freeze,
                                    style="Accent.TButton",
                                    width=12)
        self.freeze_btn.pack(side=tk.RIGHT)

        # Content section (preview + info)
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left section - Color preview
        preview_frame = ttk.Frame(content_frame, padding=(0, 0, 15, 0))
        preview_frame.pack(side=tk.LEFT, fill=tk.BOTH)
        
        # Color preview canvas with larger preview
        self.color_preview = tk.Canvas(preview_frame, 
                                      width=140, 
                                      height=140,
                                      highlightthickness=0, 
                                      bg=self.bg_medium)
        self.preview_oval = self.color_preview.create_oval(10, 10, 130, 130,
                                                          fill="#ffffff",
                                                          outline=self.bg_light,
                                                          width=2)
        self.color_preview.pack(pady=5)

        # Preview label
        ttk.Label(preview_frame, 
                 text="COLOR PREVIEW", 
                 style="Title.TLabel"
                ).pack(pady=(5, 0))

        # Right section - Information panel
        info_frame = ttk.Frame(content_frame, padding=(5))
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Color information with copy buttons
        labels_with_copy = [
            ("COLOR NAME", "name_label", lambda: pyperclip.copy(self.current_name)),
            ("HEX CODE", "hex_label", lambda: pyperclip.copy(self.current_hex)),
            ("RGB VALUES", "rgb_label", lambda: pyperclip.copy(f"{self.current_rgb[0]}, {self.current_rgb[1]}, {self.current_rgb[2]}"))
        ]

        for idx, (title, var_name, copy_func) in enumerate(labels_with_copy):
            frame = ttk.Frame(info_frame)
            frame.pack(fill=tk.X, pady=5)
            
            # Title label
            ttk.Label(frame, 
                     text=title, 
                     style="Title.TLabel"
                    ).pack(side=tk.LEFT, anchor=tk.W)
            
            # Copy button
            copy_btn = ttk.Button(frame, 
                                 text="Copy", 
                                 command=copy_func,
                                 width=6)
            copy_btn.pack(side=tk.RIGHT, padx=(10, 0))
            
            # Value label
            label = ttk.Label(frame, 
                             text="—", 
                             style="Color.TLabel")
            label.pack(side=tk.RIGHT)
            setattr(self, var_name, label)

        # Color history section
        history_frame = ttk.Frame(main_frame, padding=(0, 15, 0, 0))
        history_frame.pack(fill=tk.X)
        
        ttk.Label(history_frame, 
                 text="COLOR HISTORY", 
                 style="Title.TLabel"
                ).pack(anchor=tk.W)
        
        # History swatches container
        self.history_swatches = ttk.Frame(history_frame, 
                                         style="History.TFrame")
        self.history_swatches.pack(fill=tk.X, pady=(5, 0))
        
        # Initialize empty swatches
        self.swatch_buttons = []
        for i in range(8):
            swatch = tk.Button(self.history_swatches, 
                              width=4, 
                              height=2,
                              bd=0,
                              bg=self.bg_light,
                              activebackground=self.bg_light)
            swatch.pack(side=tk.LEFT, padx=2, pady=2)
            self.swatch_buttons.append(swatch)

        # Status bar
        self.status_bar = ttk.Label(self.root, 
                                  text="Point your cursor anywhere to detect colors...",
                                  style="Status.TLabel", 
                                  padding=(10, 5))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Start updates
        self.update_color()

    def closest_color(self, requested_rgb):
        min_distance = float('inf')
        closest_name = ""
        for rgb, name in CSS3_COLORS:
            distance = sum((c1 - c2)**2 for c1, c2 in zip(rgb, requested_rgb))
            if distance < min_distance:
                min_distance, closest_name = distance, name
        return closest_name

    def toggle_freeze(self, event=None):
        self.frozen = not self.frozen
        if self.frozen:
            self.freeze_var.set("Unfreeze")
            self.status_bar.config(text="Color frozen. Click 'Unfreeze' to continue detecting.")
            self.add_to_history(self.current_rgb, self.current_hex)
        else:
            self.freeze_var.set("Freeze Color")
            self.status_bar.config(text="Point your cursor anywhere to detect colors...")

   
   
    def copy_color(self, event=None):
        pyperclip.copy(self.current_name)
        self.status_bar.config(text="Copied the color name to clipboard.")
    
    
    def add_to_history(self, rgb, hex_code):
        # Add color to history if it's not already the most recent
        if not self.color_history or self.color_history[0] != hex_code:
            self.color_history.insert(0, hex_code)
            self.color_history = self.color_history[:8]  # Keep only 8 most recent
            self.update_history_swatches()

    def update_history_swatches(self):
        # Update history swatch buttons
        for i, swatch in enumerate(self.swatch_buttons):
            if i < len(self.color_history):
                color = self.color_history[i]
                swatch.config(bg=color, activebackground=color)
                swatch.config(command=partial(self.select_history_color, color))
            else:
                swatch.config(bg=self.bg_light, activebackground=self.bg_light)
                swatch.config(command=None)

    def select_history_color(self, hex_code):
        # When a history color is selected
        rgb = webcolors.hex_to_rgb(hex_code)
        self.update_ui_with_color(rgb, hex_code)
        self.frozen = True
        self.freeze_var.set("Unfreeze")
        self.status_bar.config(text=f"Selected color from history: {hex_code}")

    def update_ui_with_color(self, rgb, hex_code):
        try:
            color_name = webcolors.rgb_to_name(rgb).title()
        except ValueError:
            color_name = self.closest_color(rgb).title()
            
        # Save current values
        self.current_rgb = rgb
        self.current_hex = hex_code.upper()
        self.current_name = color_name

        # Update UI elements
        self.color_preview.itemconfig(self.preview_oval, fill=hex_code)
        self.name_label.config(text=color_name)
        self.hex_label.config(text=hex_code.upper())
        self.rgb_label.config(text=f"{rgb[0]:<3}, {rgb[1]:<3}, {rgb[2]:<3}")

    def update_color(self):
        if not self.frozen:
            try:
                x, y = self.root.winfo_pointerx(), self.root.winfo_pointery()
                rgb = pyautogui.pixel(x, y)
                hex_code = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
                
                self.update_ui_with_color(rgb, hex_code)
                self.status_bar.config(text=f"Detecting color at X: {x:4} Y: {y:4}")

            except pyautogui.FailSafeException:
                logging.error("PyAutoGUI fail-safe triggered.")
                self.status_bar.config(text="PyAutoGUI fail-safe triggered. Please check your cursor position.")
            except Exception as e:
                logging.error(f"Error during color detection: {str(e)}")
                self.status_bar.config(text="An error occurred while detecting the color.")

        self.root.after(50, self.update_color)

if __name__ == "__main__":
    root = tk.Tk()
    app = ColorDetectorApp(root)
    root.mainloop()
