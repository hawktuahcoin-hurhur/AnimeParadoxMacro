"""
Roblox Macro with OCR - Main Application
A macro for automating gameplay in Roblox games with OCR-based detection.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import keyboard
import threading
from config import load_config, save_config
from macro_engine import MacroEngine
from placement_editor import PlacementEditor

class MacroApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Anime Paradox Macro")
        self.root.geometry("500x650")
        self.root.resizable(False, False)
        
        # Load configuration
        self.config = load_config()
        
        # Macro engine
        self.engine = None
        
        # Hotkey state
        self.hotkeys_registered = False
        
        # Setup UI
        self._setup_styles()
        self._setup_ui()
        self._register_hotkeys()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _setup_styles(self):
        """Setup ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Custom styles
        style.configure('Title.TLabel', font=('Segoe UI', 16, 'bold'))
        style.configure('Section.TLabelframe.Label', font=('Segoe UI', 10, 'bold'))
        style.configure('Status.TLabel', font=('Segoe UI', 9))
        style.configure('Start.TButton', font=('Segoe UI', 10, 'bold'))
        style.configure('Stop.TButton', font=('Segoe UI', 10, 'bold'))
    
    def _setup_ui(self):
        """Setup the main UI"""
        # Main container
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = ttk.Label(main_frame, text="🎮 Anime Paradox Macro", style='Title.TLabel')
        title.pack(pady=(0, 15))
        
        # Stage Selection Section
        stage_frame = ttk.LabelFrame(main_frame, text="Stage Selection", padding=10, style='Section.TLabelframe')
        stage_frame.pack(fill=tk.X, pady=5)
        
        # Mode selection
        mode_frame = ttk.Frame(stage_frame)
        mode_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(mode_frame, text="Mode:").pack(side=tk.LEFT, padx=(0, 10))
        self.mode_var = tk.StringVar(value=self.config.get("mode", "Story"))
        self.mode_combo = ttk.Combobox(
            mode_frame, 
            textvariable=self.mode_var,
            values=["Story", "Raids", "Siege"],
            state="readonly",
            width=20
        )
        self.mode_combo.pack(side=tk.LEFT)
        self.mode_combo.bind("<<ComboboxSelected>>", self._on_mode_change)
        
        # Location selection (Story only)
        self.location_frame = ttk.Frame(stage_frame)
        self.location_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.location_frame, text="Location:").pack(side=tk.LEFT, padx=(0, 10))
        self.location_var = tk.StringVar(value=self.config.get("location", "Leaf Village"))
        self.location_combo = ttk.Combobox(
            self.location_frame,
            textvariable=self.location_var,
            values=["Leaf Village", "Planet Namek", "Dark Hollow"],
            state="readonly",
            width=20
        )
        self.location_combo.pack(side=tk.LEFT)
        
        # Act selection (Story only)
        self.act_frame = ttk.Frame(stage_frame)
        self.act_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.act_frame, text="Act:").pack(side=tk.LEFT, padx=(0, 10))
        self.act_var = tk.StringVar(value=self.config.get("act", "Act 1"))
        self.act_combo = ttk.Combobox(
            self.act_frame,
            textvariable=self.act_var,
            values=["Act 1", "Act 2", "Act 3", "Act 4", "Act 5", "Act 6"],
            state="readonly",
            width=20
        )
        self.act_combo.pack(side=tk.LEFT)
        
        # Update visibility based on mode
        self._on_mode_change()
        
        # Keybind Section
        keybind_frame = ttk.LabelFrame(main_frame, text="Keybinds", padding=10, style='Section.TLabelframe')
        keybind_frame.pack(fill=tk.X, pady=5)
        
        # Start keybind
        start_key_frame = ttk.Frame(keybind_frame)
        start_key_frame.pack(fill=tk.X, pady=3)
        
        ttk.Label(start_key_frame, text="Start:").pack(side=tk.LEFT, padx=(0, 10))
        self.start_key_var = tk.StringVar(value=self.config.get("start_keybind", "f1").upper())
        self.start_key_entry = ttk.Entry(start_key_frame, textvariable=self.start_key_var, width=10)
        self.start_key_entry.pack(side=tk.LEFT)
        ttk.Button(start_key_frame, text="Set", command=lambda: self._capture_key("start")).pack(side=tk.LEFT, padx=5)
        
        # Stop keybind
        stop_key_frame = ttk.Frame(keybind_frame)
        stop_key_frame.pack(fill=tk.X, pady=3)
        
        ttk.Label(stop_key_frame, text="Stop:").pack(side=tk.LEFT, padx=(0, 10))
        self.stop_key_var = tk.StringVar(value=self.config.get("stop_keybind", "f3").upper())
        self.stop_key_entry = ttk.Entry(stop_key_frame, textvariable=self.stop_key_var, width=10)
        self.stop_key_entry.pack(side=tk.LEFT)
        ttk.Button(stop_key_frame, text="Set", command=lambda: self._capture_key("stop")).pack(side=tk.LEFT, padx=5)
        
        # Apply keybinds button
        ttk.Button(keybind_frame, text="Apply Keybinds", command=self._register_hotkeys).pack(pady=5)
        
        # Placement Configuration Section
        placement_frame = ttk.LabelFrame(main_frame, text="Placement Configuration", padding=10, style='Section.TLabelframe')
        placement_frame.pack(fill=tk.X, pady=5)
        
        # Placement area status
        self.placement_status = ttk.Label(
            placement_frame,
            text=self._get_placement_status(),
            style='Status.TLabel'
        )
        self.placement_status.pack(pady=5)
        
        # Configure button
        ttk.Button(
            placement_frame,
            text="📐 Configure Placement Area & Slots",
            command=self._open_placement_editor
        ).pack(pady=5)
        
        # Slot summary
        self.slot_summary = ttk.Label(
            placement_frame,
            text=self._get_slot_summary(),
            style='Status.TLabel',
            justify=tk.LEFT
        )
        self.slot_summary.pack(pady=5)
        
        # Control Section
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding=10, style='Section.TLabelframe')
        control_frame.pack(fill=tk.X, pady=5)
        
        # Start/Stop buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.start_btn = ttk.Button(
            button_frame,
            text="▶ Start Macro",
            style='Start.TButton',
            command=self._start_macro
        )
        self.start_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        self.stop_btn = ttk.Button(
            button_frame,
            text="⏹ Stop Macro",
            style='Stop.TButton',
            command=self._stop_macro,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        # Status Section
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding=10, style='Section.TLabelframe')
        status_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Status text
        self.status_text = tk.Text(status_frame, height=8, state=tk.DISABLED, wrap=tk.WORD)
        self.status_text.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.status_text, command=self.status_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.configure(yscrollcommand=scrollbar.set)
        
        self._update_status("Ready. Press Start or use hotkey to begin.")
    
    def _get_placement_status(self):
        """Get placement area status text"""
        area = self.config.get("placement_area")
        if area:
            return f"✅ Placement Area: ({area['x']}, {area['y']}) - {area['width']}x{area['height']}"
        return "⚠️ No placement area configured"
    
    def _get_slot_summary(self):
        """Get slot configuration summary"""
        slots = self.config.get("slots", [])
        enabled = [s for s in slots if s.get("enabled", False)]
        
        if not enabled:
            return "No slots enabled"
        
        lines = ["Enabled Slots:"]
        for slot in enabled:
            lines.append(f"  • {slot.get('name', 'Unnamed')}: Place P{slot.get('placement_priority', '?')}, Upgrade P{slot.get('upgrade_priority', '?')}, Limit: {slot.get('placement_limit', 3)}")
        
        return "\n".join(lines)
    
    def _on_mode_change(self, event=None):
        """Handle mode selection change"""
        mode = self.mode_var.get()
        
        if mode == "Story":
            self.location_frame.pack(fill=tk.X, pady=5)
            self.act_frame.pack(fill=tk.X, pady=5)
        else:
            self.location_frame.pack_forget()
            self.act_frame.pack_forget()
    
    def _capture_key(self, key_type):
        """Capture a key press for keybind"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Set {key_type.title()} Key")
        dialog.geometry("250x100")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Press any key...", font=('Segoe UI', 12)).pack(expand=True)
        
        def on_key(event):
            key_name = event.keysym.upper()
            if key_type == "start":
                self.start_key_var.set(key_name)
            else:
                self.stop_key_var.set(key_name)
            dialog.destroy()
        
        dialog.bind("<Key>", on_key)
        dialog.focus_set()
    
    def _register_hotkeys(self):
        """Register global hotkeys"""
        # Unregister existing hotkeys
        if self.hotkeys_registered:
            keyboard.unhook_all_hotkeys()
        
        try:
            start_key = self.start_key_var.get().lower()
            stop_key = self.stop_key_var.get().lower()
            
            keyboard.add_hotkey(start_key, self._start_macro)
            keyboard.add_hotkey(stop_key, self._stop_macro)
            
            self.hotkeys_registered = True
            self._update_status(f"Hotkeys registered: Start={start_key.upper()}, Stop={stop_key.upper()}")
            
            # Save to config
            self.config["start_keybind"] = start_key
            self.config["stop_keybind"] = stop_key
            save_config(self.config)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to register hotkeys: {str(e)}")
    
    def _open_placement_editor(self):
        """Open the placement area editor"""
        def on_save(updated_config):
            self.config = updated_config
            save_config(self.config)
            self.placement_status.config(text=self._get_placement_status())
            self.slot_summary.config(text=self._get_slot_summary())
        
        PlacementEditor(self.root, self.config, on_save)
    
    def _start_macro(self):
        """Start the macro"""
        if self.engine and self.engine.running:
            return
        
        # Save current settings
        self.config["mode"] = self.mode_var.get()
        self.config["location"] = self.location_var.get()
        self.config["act"] = self.act_var.get()
        save_config(self.config)
        
        # Check for placement area
        if not self.config.get("placement_area"):
            messagebox.showwarning("Warning", "Please configure a placement area first!")
            return
        
        # Check for enabled slots
        enabled_slots = [s for s in self.config.get("slots", []) if s.get("enabled", False)]
        if not enabled_slots:
            messagebox.showwarning("Warning", "Please enable at least one slot!")
            return
        
        # Create and start engine
        self.engine = MacroEngine(self.config, self._update_status)
        self.engine.start()
        
        # Update UI
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        self._update_status("Macro started!")
    
    def _stop_macro(self):
        """Stop the macro"""
        if self.engine:
            self.engine.stop()
        
        # Update UI
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        self._update_status("Macro stopped.")
    
    def _update_status(self, message):
        """Update the status display"""
        def update():
            self.status_text.config(state=tk.NORMAL)
            self.status_text.insert(tk.END, f"{message}\n")
            self.status_text.see(tk.END)
            self.status_text.config(state=tk.DISABLED)
        
        # Schedule on main thread
        self.root.after(0, update)
    
    def _on_close(self):
        """Handle window close"""
        if self.engine and self.engine.running:
            self.engine.stop()
        
        if self.hotkeys_registered:
            keyboard.unhook_all_hotkeys()
        
        self.root.destroy()
    
    def run(self):
        """Run the application"""
        self.root.mainloop()


if __name__ == "__main__":
    app = MacroApp()
    app.run()
