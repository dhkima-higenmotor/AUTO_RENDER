import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk
import subprocess
import threading
import queue
import os
import sys
import shutil

# Make the process DPI aware to render sharp system fonts on Windows
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import json

def load_config():
    config = {
        "blender_exe": "blender",
        "render_samples": 512,
        "viewport_samples": 64,
        "use_denoising": True,
        "explode_axis": "Y",
        "explode_dir_mode": "POS",
        "explode_duration": 20,
        "resolution_x": 800,
        "resolution_y": 600,
        "resolution_percentage": 200,
        "resolution_percentage_explode": 100,
        "keywords_green_plastic": "ap-, bp-, pcb, connector, T-10-15-25, T-15-20-30, T-20-25-35, T-25-30-40, T-30-35-45, PT-10-20, PT-13-25, PT-14-25, PT-15-25, PT-20-30, PT-25-35, PT-30-40, PT-35-45, stator+bobbin",
        "keywords_brass": "hex_post",
        "keywords_brushed_nickel": "screw, bolt, key, pin, washer, nut, rivet, 나사, 볼트, 핀, 와셔, 너트, 리벳, 키, rotor+magnet",
        "keywords_stainless_steel": "bearing, 베어링, 6803zz, 6905zz, 6807zz, 6808zz, 6809zz, 6903zz, nsk, rau",
        "keywords_copper": "stator+coil",
        "keywords_carbon_steel": "stator+core",
        "keywords_pearl_black_plastic": "housing, case, cover, body, frame, shell, panel, enclosure, 하우징, 케이스, 커버, 외관, 몸체, 프레임, 패널, 셀"
    }
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    template_path = os.path.join(script_dir, "config.json.template")
    
    selected_path = None
    if os.path.exists(config_path):
        selected_path = config_path
    elif os.path.exists(template_path):
        selected_path = template_path
        
    if selected_path:
        try:
            with open(selected_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                config.update(user_config)
        except Exception as e:
            print(f"Warning: Failed to load config from {selected_path}: {e}")
    return config

class ConfigEditorDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Configuration Editor")
        
        width = 800
        height = 620
        self.geometry(f"{width}x{height}")
        self.resizable(True, True)
        
        self.transient(parent)
        self.grab_set()
        
        # Center the dialog relative to parent
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        
        x = parent_x + (parent_w - width) // 2
        y = parent_y + (parent_h - height) // 2
        self.geometry(f"+{x}+{y}")
        
        # Buttons frame at bottom (pack this first so it stays at the bottom)
        frame_buttons = tk.Frame(self)
        frame_buttons.pack(side="bottom", fill="x", pady=10)
        
        btn_save = tk.Button(frame_buttons, text="Save", width=12, command=self.on_save, bg="#4CAF50", fg="white", activebackground="#45a049")
        btn_save.pack(side="right", padx=10)
        
        btn_cancel = tk.Button(frame_buttons, text="Cancel", width=12, command=self.destroy)
        btn_cancel.pack(side="right", padx=10)
        
        # Details frame just above the buttons
        self.frame_details = tk.LabelFrame(self, text="Selected Value Details (Word Wrapped & Editable)", padx=10, pady=5)
        self.frame_details.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        
        self.lbl_selected_key = tk.Label(self.frame_details, text="Select a key from the list above to view/edit", font=("TkDefaultFont", 9, "bold"), anchor="w")
        self.lbl_selected_key.pack(fill="x", pady=(0, 5))
        
        # Text widget for multiline editing
        self.txt_value = tk.Text(self.frame_details, height=5, wrap="word", font="TkDefaultFont")
        self.txt_value.pack(side="left", fill="both", expand=True)
        self.txt_value.config(state="disabled")
        
        txt_scrollbar = ttk.Scrollbar(self.frame_details, orient="vertical", command=self.txt_value.yview)
        self.txt_value.configure(yscrollcommand=txt_scrollbar.set)
        txt_scrollbar.pack(side="right", fill="y")
        
        # Tree and scrollbar frame filling the top remaining space
        frame_tree = tk.Frame(self)
        frame_tree.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        
        # Treeview setup
        self.tree = ttk.Treeview(frame_tree, columns=("Value"), show="tree headings")
        self.tree.heading("#0", text="Key")
        self.tree.heading("Value", text="Value")
        self.tree.column("#0", width=200, anchor="w")
        self.tree.column("Value", width=550, anchor="w")
        
        # Scrollbars
        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Load config.json
        self.config_data = load_config()
        self.populate_tree()
        
        # Event bindings
        self.current_selected_key = None
        self.tree.bind("<<TreeviewSelect>>", self.on_select_item)
        self.txt_value.bind("<KeyRelease>", self.on_text_change)
        self.tree.bind("<Double-1>", self.on_double_click)
        
    def populate_tree(self):
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for key, val in self.config_data.items():
            self.tree.insert("", "end", iid=key, text=key, values=(str(val),))
            
    def on_select_item(self, event):
        selected = self.tree.selection()
        if not selected:
            self.current_selected_key = None
            self.lbl_selected_key.config(text="Select a key from the list above to view/edit")
            self.txt_value.delete("1.0", tk.END)
            self.txt_value.config(state="disabled")
            return
            
        key = selected[0]
        self.current_selected_key = key
        val = self.tree.set(key, "Value")
        
        self.lbl_selected_key.config(text=f"Key: {key}")
        self.txt_value.config(state="normal")
        self.txt_value.delete("1.0", tk.END)
        self.txt_value.insert("1.0", val)
        
    def on_text_change(self, event=None):
        if not self.current_selected_key:
            return
        new_val_str = self.txt_value.get("1.0", "end-1c")
        self.tree.set(self.current_selected_key, "Value", new_val_str)
        
    def on_double_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
            
        column = self.tree.identify_column(event.x)
        item_id = self.tree.identify_row(event.y)
        
        if not item_id:
            return
            
        if column != "#1":
            return
            
        bbox = self.tree.bbox(item_id, column)
        if not bbox:
            return
            
        x, y, w, h = bbox
        
        entry = tk.Entry(self.tree)
        entry.insert(0, self.tree.set(item_id, "Value"))
        entry.select_range(0, tk.END)
        entry.focus_set()
        
        entry.place(x=x, y=y, width=w, height=h)
        
        editing = True
        def save_edit(event_or_none=None):
            nonlocal editing
            if not editing:
                return
            new_val = entry.get()
            orig_val = self.config_data.get(item_id)
            typed_val = new_val
            
            if isinstance(orig_val, bool):
                typed_val = new_val.lower() in ("true", "1", "yes", "on")
            elif isinstance(orig_val, int):
                try:
                    typed_val = int(new_val)
                except ValueError:
                    messagebox.showerror("Error", f"Value for {item_id} must be an integer.")
                    editing = False
                    entry.destroy()
                    return
            elif isinstance(orig_val, float):
                try:
                    typed_val = float(new_val)
                except ValueError:
                    messagebox.showerror("Error", f"Value for {item_id} must be a number.")
                    editing = False
                    entry.destroy()
                    return
            
            self.tree.set(item_id, "Value", str(typed_val))
            editing = False
            entry.destroy()
            
            # Sync details text area
            if self.current_selected_key == item_id:
                self.txt_value.delete("1.0", tk.END)
                self.txt_value.insert("1.0", str(typed_val))
            
        def cancel_edit(event=None):
            nonlocal editing
            if editing:
                editing = False
                entry.destroy()
            
        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)
        entry.bind("<Escape>", cancel_edit)
        
    def on_save(self):
        updated_config = {}
        for key in self.config_data.keys():
            val_str = self.tree.set(key, "Value")
            orig_val = self.config_data[key]
            
            if isinstance(orig_val, bool):
                val_lower = val_str.strip().lower()
                if val_lower in ("true", "1", "yes", "on"):
                    typed_val = True
                elif val_lower in ("false", "0", "no", "off"):
                    typed_val = False
                else:
                    messagebox.showerror("Validation Error", f"Value for '{key}' must be True or False.")
                    self.tree.selection_set(key)
                    self.tree.focus(key)
                    return
            elif isinstance(orig_val, int):
                try:
                    typed_val = int(val_str.strip())
                except ValueError:
                    messagebox.showerror("Validation Error", f"Value for '{key}' must be an integer.")
                    self.tree.selection_set(key)
                    self.tree.focus(key)
                    return
            elif isinstance(orig_val, float):
                try:
                    typed_val = float(val_str.strip())
                except ValueError:
                    messagebox.showerror("Validation Error", f"Value for '{key}' must be a number.")
                    self.tree.selection_set(key)
                    self.tree.focus(key)
                    return
            else:
                typed_val = val_str
                
            updated_config[key] = typed_val
            
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "config.json")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(updated_config, f, indent=2)
            messagebox.showinfo("Success", "Configuration saved successfully.")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config.json: {e}")

class AxisSelectionDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.result = None
        
        self.title("Select Explode Axis & Direction")
        self.geometry("360x260")
        self.resizable(False, False)
        
        # Center the dialog relative to parent
        self.transient(parent)
        self.grab_set()
        
        # Calculate center position
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        
        x = parent_x + (parent_w - 360) // 2
        y = parent_y + (parent_h - 260) // 2
        self.geometry(f"+{x}+{y}")
        
        # UI Elements
        # Label for Axis
        lbl_msg = tk.Label(self, text="Select the disassembly (explode) axis:", font=("TkDefaultFont", 10, "bold"))
        lbl_msg.pack(pady=(15, 5))
        
        config = load_config()
        # Radiobuttons for X, Y, Z
        self.axis_var = tk.StringVar(value=config.get("explode_axis", "Y"))
        frame_radio = tk.Frame(self)
        frame_radio.pack(pady=5)
        
        for axis in ["X", "Y", "Z"]:
            rb = tk.Radiobutton(frame_radio, text=f"{axis} Axis", variable=self.axis_var, value=axis, font=("TkDefaultFont", 10))
            rb.pack(side="left", padx=15)

        # Label for Direction Mode
        lbl_dir = tk.Label(self, text="Select the explosion direction:", font=("TkDefaultFont", 10, "bold"))
        lbl_dir.pack(pady=(15, 5))

        # Radiobuttons for Direction (+, -)
        self.dir_var = tk.StringVar(value=config.get("explode_dir_mode", "POS"))
        frame_dir = tk.Frame(self)
        frame_dir.pack(pady=5)

        directions = [("+ (Positive)", "POS"), ("- (Negative)", "NEG")]
        for text, value in directions:
            rb = tk.Radiobutton(frame_dir, text=text, variable=self.dir_var, value=value, font=("TkDefaultFont", 10))
            rb.pack(side="left", padx=20)
            
        # Buttons Frame
        frame_buttons = tk.Frame(self)
        frame_buttons.pack(pady=20)
        
        btn_ok = tk.Button(frame_buttons, text="OK", width=10, command=self.on_ok, bg="#4CAF50", fg="white", activebackground="#45a049")
        btn_ok.pack(side="left", padx=10)
        
        btn_cancel = tk.Button(frame_buttons, text="Cancel", width=10, command=self.on_cancel)
        btn_cancel.pack(side="left", padx=10)
        
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.wait_window(self)
        
    def on_ok(self):
        self.result = (self.axis_var.get(), self.dir_var.get())
        self.destroy()
        
    def on_cancel(self):
        self.result = None
        self.destroy()

class DurationSelectionDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.result = None
        
        self.title("Select Explode Duration")
        self.geometry("320x180")
        self.resizable(False, False)
        
        # Center the dialog relative to parent
        self.transient(parent)
        self.grab_set()
        
        # Calculate center position
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        
        x = parent_x + (parent_w - 320) // 2
        y = parent_y + (parent_h - 180) // 2
        self.geometry(f"+{x}+{y}")
        
        # UI Elements
        lbl_msg = tk.Label(self, text="Set disassembly duration (seconds):", font=("TkDefaultFont", 10, "bold"))
        lbl_msg.pack(pady=15)
        
        # Entry for duration
        config = load_config()
        self.duration_var = tk.StringVar(value=str(config.get("explode_duration", 20)))
        
        frame_input = tk.Frame(self)
        frame_input.pack(pady=5)
        
        # Spinbox
        self.spin = tk.Spinbox(frame_input, from_=1, to=3600, textvariable=self.duration_var, width=10, font=("TkDefaultFont", 10))
        self.spin.pack(side="left", padx=5)
        
        lbl_sec = tk.Label(frame_input, text="seconds", font=("TkDefaultFont", 10))
        lbl_sec.pack(side="left")
        
        # Buttons Frame
        frame_buttons = tk.Frame(self)
        frame_buttons.pack(pady=15)
        
        btn_ok = tk.Button(frame_buttons, text="OK", width=10, command=self.on_ok, bg="#4CAF50", fg="white", activebackground="#45a049")
        btn_ok.pack(side="left", padx=10)
        
        btn_cancel = tk.Button(frame_buttons, text="Cancel", width=10, command=self.on_cancel)
        btn_cancel.pack(side="left", padx=10)
        
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.wait_window(self)
        
    def on_ok(self):
        val_str = self.duration_var.get().strip()
        try:
            val = int(val_str)
            if val <= 0:
                raise ValueError
            self.result = val
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid positive integer for seconds.")
        
    def on_cancel(self):
        self.result = None
        self.destroy()

class AutoRenderApp:
    def __init__(self, root):
        self.root = root
        self.root.option_add("*Font", "TkDefaultFont")
        self.root.title("Auto Render GUI")
        self.root.geometry("1000x520")
        
        # Variables
        self.selected_file_path = tk.StringVar()
        self.selected_file_path.set("No file selected")
        self.selected_blend_path = tk.StringVar()
        self.selected_blend_path.set("No blend file selected")
        self.resolution_var = tk.StringVar(value="800x600")
        self.log_queue = queue.Queue()
        
        # UI Setup
        self.setup_ui()
        
        # Start queue poller
        self.root.after(100, self.process_log_queue)

    def setup_ui(self):
        # 1. File Selection Frame
        frame_file = tk.LabelFrame(self.root, text="Target File", padx=8, pady=4)
        frame_file.pack(fill="x", padx=10, pady=2)
        
        lbl_file = tk.Label(frame_file, textvariable=self.selected_file_path, fg="blue", wraplength=800, anchor="w")
        lbl_file.pack(side="left", fill="x", expand=True)
        
        btn_browse = tk.Button(frame_file, text="Choose SLDASM", command=self.choose_file)
        btn_browse.pack(side="right")

        # 1.5. Blend File Selection Frame
        frame_blend = tk.LabelFrame(self.root, text="blend File", padx=8, pady=4)
        frame_blend.pack(fill="x", padx=10, pady=2)
        
        lbl_blend = tk.Label(frame_blend, textvariable=self.selected_blend_path, fg="blue", wraplength=800, anchor="w")
        lbl_blend.pack(side="left", fill="x", expand=True)
        
        btn_browse_blend = tk.Button(frame_blend, text="Choose BLEND", command=self.choose_blend_file)
        btn_browse_blend.pack(side="right")
        
        # 2. Action Buttons Frame
        frame_actions = tk.Frame(self.root, padx=10, pady=4)
        frame_actions.pack(fill="x", padx=10, pady=2)
        
        self.btn_stl = tk.Button(frame_actions, text="Make STL", command=self.run_make_stl, width=15, height=1, state="disabled")
        self.btn_stl.pack(side="left", padx=4)
        
        self.btn_blend = tk.Button(frame_actions, text="Make BLEND", command=self.run_make_blend, width=15, height=1, state="disabled")
        self.btn_blend.pack(side="left", padx=4)
        
        self.btn_open = tk.Button(frame_actions, text="Open BLEND", command=self.run_open_blend, width=15, height=1, state="disabled")
        self.btn_open.pack(side="left", padx=4)
        
        # Render UI
        self.btn_render = tk.Button(frame_actions, text="RENDER", command=self.run_render, width=12, height=1, state="disabled", bg="#dddddd")
        self.btn_render.pack(side="left", padx=4)
        
        self.btn_explode = tk.Button(frame_actions, text="EXPLODE", command=self.run_explode, width=12, height=1, state="disabled", bg="#dddddd")
        self.btn_explode.pack(side="left", padx=4)
        
        btn_exit = tk.Button(frame_actions, text="EXIT", command=self.root.quit, width=10, height=1, fg="red")
        btn_exit.pack(side="right", padx=4)
        
        btn_help = tk.Button(frame_actions, text="HELP", command=self.open_help, width=10, height=1)
        btn_help.pack(side="right", padx=4)
        
        btn_config = tk.Button(frame_actions, text="CONFIG", command=self.open_config, width=10, height=1)
        btn_config.pack(side="right", padx=4)
        
        # 3. Log Area
        frame_log = tk.LabelFrame(self.root, text="Output Log", padx=8, pady=4)
        frame_log.pack(fill="both", expand=True, padx=10, pady=2)
        
        self.txt_log = scrolledtext.ScrolledText(frame_log, state='disabled', height=10, font="TkDefaultFont")
        self.txt_log.pack(fill="both", expand=True)
        # Define tag for error text
        self.txt_log.tag_config("stderr", foreground="red")

    def log(self, message, is_error=False):
        self.log_queue.put((message, is_error))

    def open_help(self):
        import webbrowser
        webbrowser.open("https://codeberg.org/dymaxionkim/AUTO_RENDER")

    def open_config(self):
        ConfigEditorDialog(self.root)

    def process_log_queue(self):
        try:
            while True:
                msg, is_error = self.log_queue.get_nowait()
                self.txt_log.config(state='normal')
                if is_error:
                    self.txt_log.insert(tk.END, msg + "\n", "stderr")
                else:
                    self.txt_log.insert(tk.END, msg + "\n")
                self.txt_log.see(tk.END)
                self.txt_log.config(state='disabled')
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_log_queue)

    def choose_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("SolidWorks Assembly", "*.SLDASM"), ("All Files", "*.*")]
        )
        if file_path:
            self.selected_file_path.set(file_path)
            self.btn_stl.config(state="normal")
            
            # Check if likely ready for blend (if folder exists)
            stl_dir = os.path.splitext(file_path)[0] + "__STL"
            if os.path.isdir(stl_dir):
                self.btn_blend.config(state="normal")
            else:
                self.btn_blend.config(state="disabled")
                
            self.check_blend_file()

    def choose_blend_file(self):
        initial_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = self.selected_file_path.get()
        if file_path and file_path != "No file selected" and os.path.exists(file_path):
            suggested_dir = os.path.splitext(file_path)[0] + "__BLENDER"
            if os.path.isdir(suggested_dir):
                initial_dir = suggested_dir
            else:
                initial_dir = os.path.dirname(file_path)
                
        blend_file = filedialog.askopenfilename(
            initialdir=initial_dir,
            title="Select Blender File",
            filetypes=[("Blender File", "*.blend"), ("All Files", "*.*")]
        )
        if blend_file:
            self.selected_blend_path.set(blend_file)
            self.btn_open.config(state="normal")
            self.btn_render.config(state="normal")
            self.btn_explode.config(state="normal")

    def run_command(self, cmd):
        """Runs a subprocess and streams output to log."""
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                # text=True, # Removing text mode to handle bytes manually
                bufsize=1,
                cwd=os.path.dirname(os.path.abspath(__file__)) 
            )
            
            # Helper to read stream
            def read_stream(stream, is_error):
                import locale
                sys_encoding = locale.getpreferredencoding() or 'cp949'
                for line in iter(stream.readline, b''):
                    try:
                        decoded_line = line.decode('utf-8').strip()
                    except UnicodeDecodeError:
                        try:
                            decoded_line = line.decode(sys_encoding).strip()
                        except Exception:
                            decoded_line = line.decode('utf-8', errors='replace').strip()
                        
                    if decoded_line:
                        self.log(decoded_line, is_error=is_error)
                stream.close()

            # Create threads to read stdout and stderr simultaneously
            t_out = threading.Thread(target=read_stream, args=(process.stdout, False))
            t_err = threading.Thread(target=read_stream, args=(process.stderr, True))
            
            t_out.start()
            t_err.start()
            
            t_out.join()
            t_err.join()
            
            return_code = process.wait()
            
            if return_code == 0:
                self.log(f"Process finished successfully.", is_error=False)
            else:
                self.log(f"Process failed with exit code {return_code}", is_error=True)
            
            return return_code
                
        except Exception as e:
            self.log(f"Error running command: {e}", is_error=True)
            return -1

    def run_make_stl(self):
        file_path = self.selected_file_path.get()
        if not os.path.exists(file_path):
            messagebox.showerror("Error", "Selected file not found.")
            return

        self.btn_stl.config(state="disabled")
        self.btn_blend.config(state="disabled")
        self.log("-" * 40)
        self.log(f"Starting Export to STL: {os.path.basename(file_path)}")

        cmd = [sys.executable, "sw2stl.py", file_path]
        
        def task():
            ret = self.run_command(cmd)
            # Re-enable STL button
            self.root.after(0, lambda: self.btn_stl.config(state="normal"))
            
            # If success, check directory and enable Blend button
            if ret == 0:
                derived_stl_dir = os.path.splitext(file_path)[0] + "__STL"
                if os.path.isdir(derived_stl_dir):
                     self.root.after(0, lambda: self.btn_blend.config(state="normal"))
                     self.log("Ready for Blender conversion.")
                     self.root.after(0, lambda: self.check_blend_file())
                else:
                     self.log(f"Warning: Expected directory not found: {derived_stl_dir}", is_error=True)

        threading.Thread(target=task, daemon=True).start()

    def run_make_blend(self):
        file_path = self.selected_file_path.get()
        # Derive directory
        stl_dir = os.path.splitext(file_path)[0] + "__STL"
        
        if not os.path.isdir(stl_dir):
            messagebox.showerror("Error", f"STL Directory not found:\n{stl_dir}\nPlease run 'Make STL' first.")
            return

        self.btn_blend.config(state="disabled")
        self.log("-" * 40)
        self.log(f"Starting Blender Conversion: {os.path.basename(stl_dir)}")
        
        cmd = [sys.executable, "stl2blender.py", stl_dir]
        
        def task():
            ret = self.run_command(cmd)
            self.root.after(0, lambda: self.btn_blend.config(state="normal"))
            self.root.after(0, lambda: self.check_blend_file())
            if ret == 0:
                self.log(f"Blender conversion successful. Deleting STL directory: {stl_dir}")
                try:
                    shutil.rmtree(stl_dir)
                    self.log("Successfully deleted STL directory.")
                except Exception as e:
                    self.log(f"Failed to delete STL directory: {e}", is_error=True)

        threading.Thread(target=task, daemon=True).start()

    def run_render(self):
        blend_file = self.selected_blend_path.get()
        if not blend_file or blend_file in ("No blend file selected", "No blend file found"):
            messagebox.showerror("Error", "No Blender file selected or found.")
            return

        if not os.path.exists(blend_file):
            messagebox.showerror("Error", f"Blend file not found:\n{blend_file}")
            return
             
        self.btn_render.config(state="disabled")
        self.btn_explode.config(state="disabled")
        self.log("-" * 40)
        self.log(f"Starting Render: {os.path.basename(blend_file)}")
        self.log("Resolution: Keep blend file settings")
        
        # Call blender2png.py as CLI without --res override to keep blend settings
        cmd = [sys.executable, "blender2png.py", blend_file]
        
        def task():
            self.run_command(cmd)
            self.root.after(0, lambda: self.btn_render.config(state="normal"))
            self.root.after(0, lambda: self.btn_explode.config(state="normal"))

        threading.Thread(target=task, daemon=True).start()

    def run_explode(self):
        # 1. Ask user for axis & direction mode
        dialog = AxisSelectionDialog(self.root)
        if not dialog.result:
            self.log("Explode operation cancelled by user.")
            return
        selected_axis, selected_dir_mode = dialog.result

        # 2. Ask user for duration
        duration_dialog = DurationSelectionDialog(self.root)
        selected_duration = duration_dialog.result
        if not selected_duration:
            self.log("Explode operation cancelled by user.")
            return

        blend_file = self.selected_blend_path.get()
        if not blend_file or blend_file in ("No blend file selected", "No blend file found"):
            messagebox.showerror("Error", "No Blender file selected or found.")
            return

        if not os.path.exists(blend_file):
            messagebox.showerror("Error", f"Blend file not found:\n{blend_file}")
            return
             
        self.btn_render.config(state="disabled")
        self.btn_explode.config(state="disabled")
        self.log("-" * 40)
        self.log(f"Starting Explode Render Sequence: {os.path.basename(blend_file)} (Axis: {selected_axis}, Direction: {selected_dir_mode}, Duration: {selected_duration}s)")
        
        # 1. Copy the blend file with _explode suffix
        explode_blend_file = f"{os.path.splitext(blend_file)[0]}_explode.blend"
        try:
            shutil.copy(blend_file, explode_blend_file)
            self.log(f"Copied blend file to: {os.path.basename(explode_blend_file)}")
        except Exception as e:
            self.log(f"Failed to copy blend file: {e}", is_error=True)
            self.btn_render.config(state="normal")
            self.btn_explode.config(state="normal")
            return

        # Get Blender Exe Path and explode resolution percentage
        config = load_config()
        blender_exe = config.get("blender_exe", "blender")
        resolution_percentage_explode = config.get("resolution_percentage_explode", 100)

        # Create temporary python script for Blender
        temp_script_path = os.path.join(os.path.dirname(explode_blend_file), "_temp_explode_render.py")
        temp_script_path = os.path.normpath(temp_script_path)
        
        explode_py_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "explode.py"))
        
        script_content = f"""
import bpy
import os
import sys

# Configure selected axis, direction mode & duration
os.environ["EXPLODE_AXIS"] = "{selected_axis}"
os.environ["EXPLODE_DIR_MODE"] = "{selected_dir_mode}"
os.environ["EXPLODE_DURATION"] = "{selected_duration}"

# Configure Render Settings
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.device = 'GPU'
bpy.context.scene.cycles.samples = 64
bpy.context.scene.cycles.use_denoising = False

# Configure GPU device type
try:
    cycles_pref = bpy.context.preferences.addons['cycles'].preferences
    for dev_type in ('OPTIX', 'CUDA', 'HIP', 'ONEAPI'):
        try:
            cycles_pref.compute_device_type = dev_type
            cycles_pref.get_devices()
            has_gpu = False
            for dev in cycles_pref.devices:
                if dev.type != 'CPU':
                    dev.use = True
                    has_gpu = True
                else:
                    dev.use = False
            if has_gpu:
                print(f"Cycles GPU Compute Device Type configured: {{dev_type}}")
                break
        except Exception:
            pass
except Exception as e:
    print(f"Warning: Could not configure Cycles GPU preferences: {{e}}")

# Resolution settings (800x600, custom scale)
bpy.context.scene.render.resolution_x = 800
bpy.context.scene.render.resolution_y = 600
bpy.context.scene.render.resolution_percentage = {resolution_percentage_explode}

# Frame rate: 30 fps
bpy.context.scene.render.fps = 30

# Output path: same path as blend file, media type: video (FFMPEG, container: MPEG4)
bpy.context.scene.render.filepath = os.path.dirname(bpy.data.filepath) + "/"
bpy.context.scene.render.image_settings.media_type = 'VIDEO'
bpy.context.scene.render.image_settings.file_format = 'FFMPEG'
bpy.context.scene.render.ffmpeg.format = 'MPEG4'

# Copy explode.py code into Scripting window (Text block) and execute it
explode_py_path = {repr(explode_py_path)}
print(f"Loading explode.py script from: {{explode_py_path}}")
try:
    with open(explode_py_path, 'r', encoding='utf-8') as f:
        explode_code = f.read()
    
    # Create text block in blender
    text_block = bpy.data.texts.new(name="explode.py")
    text_block.from_string(explode_code)
    
    # Execute the text block code
    print("Executing explode.py to generate timeline...")
    exec(compile(explode_code, 'explode.py', 'exec'), globals())
    print("explode.py execution complete.")
except Exception as e:
    print(f"Error executing explode.py: {{e}}")
    sys.exit(1)

# Save the blend file
print(f"Saving modified blend file to: {{bpy.data.filepath}}")
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, relative_remap=False)

# Render animation
print("Starting animation render...")
bpy.ops.render.render(animation=True)
print("Animation render complete!")
"""

        try:
            with open(temp_script_path, "w", encoding="utf-8") as f:
                f.write(script_content)
        except Exception as e:
            self.log(f"Error creating temp render script: {e}", is_error=True)
            self.btn_render.config(state="normal")
            self.btn_explode.config(state="normal")
            return

        cmd = [blender_exe, "-b", explode_blend_file, "-P", temp_script_path]
        
        def task():
            ret = self.run_command(cmd)
            
            # Clean up temp script
            if os.path.exists(temp_script_path):
                try:
                    os.remove(temp_script_path)
                except Exception as e:
                    self.log(f"Warning: Failed to delete temp script: {e}", is_error=True)
            
            if ret == 0:
                self.log("=" * 60)
                self.log("EXPLODE ANIMATION RENDER COMPLETED SUCCESSFULLY!")
                self.log(f"Exploded Blender File: {os.path.basename(explode_blend_file)}")
                self.log(f"Output files saved to: {os.path.dirname(explode_blend_file)}")
                self.log("=" * 60)
            else:
                self.log("=" * 60)
                self.log("EXPLODE ANIMATION RENDER FAILED!", is_error=True)
                self.log("=" * 60)

            self.root.after(0, lambda: self.btn_render.config(state="normal"))
            self.root.after(0, lambda: self.btn_explode.config(state="normal"))

        threading.Thread(target=task, daemon=True).start()

    def run_open_blend(self):
        blend_file = self.selected_blend_path.get()
        if not blend_file or blend_file in ("No blend file selected", "No blend file found") or not os.path.exists(blend_file):
            messagebox.showerror("Error", "No Blender file selected or found.")
            return
            
        # Read Blender Path
        config = load_config()
        blender_exe = config.get("blender_exe", "blender")
                
        self.log("-" * 40)
        self.log(f"Launching Blender GUI with: {os.path.basename(blend_file)}")
        
        try:
            # Launch Blender GUI asynchronously without blocking the Tkinter event loop
            import subprocess
            if os.name == 'nt':
                # Detach on Windows using CREATE_NEW_CONSOLE
                subprocess.Popen([blender_exe, blend_file], creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen([blender_exe, blend_file])
            self.log("Blender GUI launched successfully.")
        except Exception as e:
            self.log(f"Error launching Blender: {e}", is_error=True)

    def check_blend_file(self):
        file_path = self.selected_file_path.get()
        if not file_path or file_path == "No file selected": return
        
        base_path_no_ext = os.path.splitext(file_path)[0]
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        blend_dir = base_path_no_ext + "__BLENDER"
        blend_file = os.path.join(blend_dir, f"{base_name}.blend")
        
        if os.path.exists(blend_file):
            self.log(f"Suggested Blend file found: {os.path.basename(blend_file)}")
            self.btn_open.config(state="normal")
            self.btn_render.config(state="normal")
            self.btn_explode.config(state="normal")
            self.selected_blend_path.set(blend_file)
        else:
            self.btn_open.config(state="disabled")
            self.btn_render.config(state="disabled")
            self.btn_explode.config(state="disabled")
            self.selected_blend_path.set("No blend file found")

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoRenderApp(root)
    root.mainloop()
