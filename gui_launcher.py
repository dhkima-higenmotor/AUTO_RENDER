import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import os
import sys
import threading

def run_blender(file_path, resolution, status_label, root):
    # Blender Executable Path
    blender_exe = r"C:\Users\hmpublic\scoop\apps\Blender\current\blender.exe"
    
    if not os.path.exists(blender_exe):
        messagebox.showerror("Error", f"Blender not found at:\n{blender_exe}")
        status_label.config(text="Status: Blender not found")
        return

    # Command construction
    # blender --background --python main.py -- --res [res] [file]
    cmd = [
        blender_exe,
        "--background",
        "--python", "main.py",
        "--",
        "--res", resolution,
        file_path
    ]
    
    status_label.config(text=f"Status: Rendering {os.path.basename(file_path)}...")
    root.update()

    try:
        # Run blocking or non-blocking?
        # Blocking is safer for simple script to prevent closing
        subprocess.run(cmd, check=True)
        status_label.config(text="Status: Finished successfully!")
        messagebox.showinfo("Success", "Rendering Complete!")
    except subprocess.CalledProcessError as e:
        status_label.config(text="Status: Error during rendering")
        messagebox.showerror("Error", f"Blender process failed:\n{e}")
    except Exception as e:
        status_label.config(text="Status: Unexpected Error")
        messagebox.showerror("Error", f"Unexpected error:\n{e}")

def on_select_and_run(res_var, status_label, root):
    file_path = filedialog.askopenfilename(
        title="Select STL File",
        filetypes=[("STL Files", "*.stl"), ("All Files", "*.*")]
    )
    
    if not file_path:
        return

    file_path = os.path.abspath(file_path)
    resolution = res_var.get()
    
    # Run in thread to keep GUI responsive? 
    # For simplicity in this environment, running in main thread is fine as user expects it to work sequentially.
    # But let's use a thread to not freeze UI if user drags windows.
    t = threading.Thread(target=run_blender, args=(file_path, resolution, status_label, root))
    t.start()

def main():
    root = tk.Tk()
    root.title("Blender STL Renderer")
    root.geometry("400x350")
    
    # Label
    lbl_header = tk.Label(root, text="Render Configuration", font=("Arial", 12, "bold"))
    lbl_header.pack(pady=10)
    
    # Resolution Selection
    lbl_res = tk.Label(root, text="Resolution:")
    lbl_res.pack()
    
    res_var = tk.StringVar(value="mid")
    
    frame_res = tk.Frame(root)
    frame_res.pack(pady=5)
    
    tk.Radiobutton(frame_res, text="Low (800x600)", variable=res_var, value="low").pack(anchor="w")
    tk.Radiobutton(frame_res, text="Mid (1024x768)", variable=res_var, value="mid").pack(anchor="w")
    tk.Radiobutton(frame_res, text="High (2048x1536)", variable=res_var, value="high").pack(anchor="w")
    
    # Separator
    tk.Frame(root, height=2, bd=1, relief="sunken").pack(fill="x", padx=10, pady=10)
    
    # Status
    status_label = tk.Label(root, text="Status: Ready", fg="blue")
    status_label.pack(side="bottom", pady=5)
    
    # Button
    btn_run = tk.Button(root, text="Select File & Render", 
                        command=lambda: on_select_and_run(res_var, status_label, root),
                        bg="#DDDDDD", font=("Arial", 10))
    btn_run.pack(pady=10, ipady=5, ipadx=10)
    
    root.mainloop()

if __name__ == "__main__":
    main()
