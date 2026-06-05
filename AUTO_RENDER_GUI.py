import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
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

class AutoRenderApp:
    def __init__(self, root):
        self.root = root
        self.root.option_add("*Font", "TkDefaultFont")
        self.root.title("Auto Render GUI")
        self.root.geometry("800x560")
        
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
        frame_file = tk.LabelFrame(self.root, text="Target File", padx=10, pady=10)
        frame_file.pack(fill="x", padx=10, pady=5)
        
        lbl_file = tk.Label(frame_file, textvariable=self.selected_file_path, fg="blue", wraplength=550)
        lbl_file.pack(side="left", fill="x", expand=True)
        
        btn_browse = tk.Button(frame_file, text="Choose SLDASM", command=self.choose_file)
        btn_browse.pack(side="right")

        # 1.5. Blend File Selection Frame
        frame_blend = tk.LabelFrame(self.root, text="blend File", padx=10, pady=10)
        frame_blend.pack(fill="x", padx=10, pady=5)
        
        lbl_blend = tk.Label(frame_blend, textvariable=self.selected_blend_path, fg="blue", wraplength=550)
        lbl_blend.pack(side="left", fill="x", expand=True)
        
        btn_browse_blend = tk.Button(frame_blend, text="Choose BLEND", command=self.choose_blend_file)
        btn_browse_blend.pack(side="right")
        
        # 2. Action Buttons Frame
        frame_actions = tk.Frame(self.root, padx=10, pady=10)
        frame_actions.pack(fill="x", padx=10)
        
        self.btn_stl = tk.Button(frame_actions, text="Make STL", command=self.run_make_stl, width=15, height=2, state="disabled")
        self.btn_stl.pack(side="left", padx=5)
        
        self.btn_blend = tk.Button(frame_actions, text="Make BLEND", command=self.run_make_blend, width=15, height=2, state="disabled")
        self.btn_blend.pack(side="left", padx=5)
        
        self.btn_open = tk.Button(frame_actions, text="Open BLEND", command=self.run_open_blend, width=15, height=2, state="disabled")
        self.btn_open.pack(side="left", padx=5)
        
        # Render UI
        self.btn_render = tk.Button(frame_actions, text="RENDER", command=self.run_render, width=12, height=2, state="disabled", bg="#dddddd")
        self.btn_render.pack(side="left", padx=5)
        
        btn_exit = tk.Button(frame_actions, text="EXIT", command=self.root.quit, width=10, height=2, fg="red")
        btn_exit.pack(side="right", padx=5)
        
        # 3. Log Area
        frame_log = tk.LabelFrame(self.root, text="Output Log", padx=10, pady=10)
        frame_log.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.txt_log = scrolledtext.ScrolledText(frame_log, state='disabled', height=10, font="TkDefaultFont")
        self.txt_log.pack(fill="both", expand=True)
        # Define tag for error text
        self.txt_log.tag_config("stderr", foreground="red")

    def log(self, message, is_error=False):
        self.log_queue.put((message, is_error))

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
        self.log("-" * 40)
        self.log(f"Starting Render: {os.path.basename(blend_file)}")
        self.log("Resolution: Keep blend file settings")
        
        # Call blender2png.py as CLI without --res override to keep blend settings
        cmd = [sys.executable, "blender2png.py", blend_file]
        
        def task():
            self.run_command(cmd)
            self.root.after(0, lambda: self.btn_render.config(state="normal"))

        threading.Thread(target=task, daemon=True).start()

    def run_open_blend(self):
        blend_file = self.selected_blend_path.get()
        if not blend_file or blend_file in ("No blend file selected", "No blend file found") or not os.path.exists(blend_file):
            messagebox.showerror("Error", "No Blender file selected or found.")
            return
            
        # Read Blender Path
        blender_exe = "blender"
        if os.path.exists("blender_exe.txt"):
            with open("blender_exe.txt", "r") as f:
                content = f.read().strip()
                if content: blender_exe = content
                
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
            self.selected_blend_path.set(blend_file)
        else:
            self.btn_open.config(state="disabled")
            self.btn_render.config(state="disabled")
            self.selected_blend_path.set("No blend file found")

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoRenderApp(root)
    root.mainloop()
