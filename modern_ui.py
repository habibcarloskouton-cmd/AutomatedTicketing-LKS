import tkinter as tk

class ModernUI:
    """Configuration des couleurs et styles modernes"""
    COLORS = {
        "bg_dark": "#1a1a2e",
        "bg_card": "#16213e",
        "bg_input": "#0f3460",
        "text_main": "#e94560",
        "text_white": "#ffffff",
        "text_gray": "#a0a0a0",
        "btn_primary": "#e94560",
        "btn_secondary": "#0f3460",
        "success": "#2ecc71",
        "hover": "#ff6b81"
    }

    FONTS = {
        "header": ("Segoe UI", 18, "bold"),
        "subheader": ("Segoe UI", 12, "bold"),
        "body": ("Segoe UI", 10),
        "mono": ("Consolas", 9)
    }

class HoverButton(tk.Button):
    def __init__(self, master, **kwargs):
        self.original_bg = kwargs.get("bg", ModernUI.COLORS["btn_secondary"])
        self.hover_bg = self._lighten_color(self.original_bg)
        super().__init__(master, **kwargs)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, e):
        self.config(bg=self.hover_bg, relief=tk.FLAT)

    def _on_leave(self, e):
        self.config(bg=self.original_bg)

    def _lighten_color(self, hex_color):
        highlights = {
            ModernUI.COLORS["btn_primary"]: "#5d5dff",
            ModernUI.COLORS["btn_secondary"]: "#4e5d6d",
            ModernUI.COLORS["success"]: "#2ed573"
        }
        return highlights.get(hex_color, "#555555")

class CardFrame(tk.Frame):
    def __init__(self, parent, title="", **kwargs):
        self.shadow = tk.Frame(parent, bg="#000000")
        super().__init__(parent, bg=ModernUI.COLORS["bg_card"], bd=0, **kwargs)
        self.header = tk.Frame(self, bg=ModernUI.COLORS["bg_card"])
        self.header.pack(fill=tk.X, padx=15, pady=(10, 5))

        tk.Label(self.header, text=title, font=("Segoe UI", 11, "bold"),
                 bg=ModernUI.COLORS["bg_card"], fg=ModernUI.COLORS["text_main"]).pack(side=tk.LEFT)

        sep = tk.Frame(self, bg=ModernUI.COLORS["bg_dark"], height=1)
        sep.pack(fill=tk.X, padx=15, pady=5)

    def pack(self, **kwargs):
        super().configure(highlightbackground="#30363d", highlightthickness=1)
        super().pack(**kwargs)
