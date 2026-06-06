import sys
import os
import json
import win32com.client
import pythoncom



def main():
    if len(sys.argv) < 2:
        print("Usage: python sw2json.py <path_to_sldasm>")
        sys.exit(1)

    # Normalize path (handle Windows backslashes)
    raw_path = sys.argv[1]
    raw_path = raw_path.strip('"').strip("'")
    file_path = os.path.abspath(raw_path)
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    file_dir = os.path.dirname(file_path)
    file_name_with_ext = os.path.basename(file_path)
    file_name, _ = os.path.splitext(file_name_with_ext)

    # 1. Connect to SolidWorks
    # Use EnsureDispatch to force Early Binding.
    print("Connecting to SolidWorks...")
    try:
        swApp = win32com.client.gencache.EnsureDispatch("SldWorks.Application")
        swApp.Visible = True
    except Exception:
        # Fallback to simple dispatch if makepy fails (silently)
        try:
            swApp = win32com.client.Dispatch("SldWorks.Application")
            swApp.Visible = True
        except Exception as e2:
            print(f"Could not connect to SolidWorks: {e2}")
            sys.exit(1)

    # 2. Open the file
    print(f"Opening {file_path}...")
    
    # Check configurations before opening
    selected_config = ""
    try:
        configs = swApp.GetConfigurationNames(file_path)
        if configs and len(configs) > 1:
            print(f"Multiple configurations found: {configs}")
            import tkinter as tk
            import tkinter.font as tkfont
            
            def choose_config_dialog(config_names):
                # Make the process DPI aware to render sharp system fonts on Windows
                try:
                    import ctypes
                    ctypes.windll.shcore.SetProcessDpiAwareness(1)
                except Exception:
                    pass
                    
                selected = [config_names[0]]
                root = tk.Tk()
                root.option_add("*Font", "TkDefaultFont")
                root.title("Select Configuration")
                root.geometry("350x250")
                root.attributes("-topmost", True)
                
                # Center on screen
                root.update_idletasks()
                width = root.winfo_width()
                height = root.winfo_height()
                x = (root.winfo_screenwidth() // 2) - (width // 2)
                y = (root.winfo_screenheight() // 2) - (height // 2)
                root.geometry(f'{width}x{height}+{x}+{y}')
                
                sys_font = tkfont.nametofont("TkDefaultFont")
                bold_sys_font = tkfont.Font(root=root, family=sys_font.cget("family"), size=sys_font.cget("size"), weight="bold")
                
                lbl = tk.Label(root, text="Select SolidWorks Configuration:", font=bold_sys_font, pady=10)
                lbl.pack()
                
                frame = tk.Frame(root)
                frame.pack(fill="x", padx=20, pady=5)
                
                scroll = tk.Scrollbar(frame, orient="vertical")
                listb = tk.Listbox(frame, yscrollcommand=scroll.set, font="TkDefaultFont", height=6)
                scroll.config(command=listb.yview)
                scroll.pack(side="right", fill="y")
                listb.pack(side="left", fill="both", expand=True)
                
                for c in config_names:
                    listb.insert(tk.END, c)
                listb.select_set(0)
                
                def on_ok():
                    sel = listb.curselection()
                    if sel:
                        selected[0] = config_names[sel[0]]
                    root.destroy()
                    
                btn = tk.Button(root, text="OK", command=on_ok, width=10, height=2, bg="#dddddd")
                btn.pack(pady=10)
                
                root.protocol("WM_DELETE_WINDOW", on_ok)
                root.mainloop()
                return selected[0]
                
            selected_config = choose_config_dialog(list(configs))
            print(f"Opening with configuration: {selected_config}")
    except Exception as e:
        print(f"Error querying configurations: {e}")

    # OpenDoc6(FileName, Type, Options, Configuration, &Errors, &Warnings)
    # Type: 2 for Assembly (swDocASSEMBLY)
    # Options: 1 (swOpenDocOptions_Silent)
    # Try to open the file
    model = None
    try:
        # Try correct OpenDoc6 call for Dynamic Dispatch (requires explicit ByRef VARIANTs)
        try:
             # First attempt: Pythonic (works for Early Binding usually)
             result = swApp.OpenDoc6(file_path, 2, 1, selected_config)
             if isinstance(result, tuple):
                 model = result[0]
             else:
                 model = result
        except Exception:
             # Second attempt: Dynamic Dispatch with explicit VARIANTs
             # Silently try the fallback
             arg_err = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
             arg_warn = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
             model = swApp.OpenDoc6(file_path, 2, 1, selected_config, arg_err, arg_warn)
             
    except Exception:
        # Final fallback to legacy OpenDoc
        try:
            model = swApp.OpenDoc(file_path, 2)
        except Exception:
             model = None
    
    if not model:
        print("Failed to open document.")
        sys.exit(1)
        
    # Activate the document just in case
    # ActivateDoc3(Name, Rebuild, Options, &Errors)
    try:
        # Try Pythonic way (omitting ByRef output)
        swApp.ActivateDoc3(file_name_with_ext, False, 0)
    except:
        try:
             # Try with VARIANT for ByRef
             arg_err = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
             swApp.ActivateDoc3(file_name_with_ext, False, 0, arg_err)
        except Exception as e:
            print(f"Warning: ActivateDoc3 failed ({e}), but proceeding since OpenDoc succeeded.")

    # Explicitly switch configuration if a specific one was selected (in case file was already open)
    if selected_config:
        try:
            print(f"Activating configuration: {selected_config}")
            val = model.ShowConfiguration2
            if callable(val):
                val(selected_config)
            else:
                model.ShowConfiguration2 = selected_config
            
            # Rebuild after switching configuration
            rebuild_val = model.EditRebuild3
            if callable(rebuild_val):
                rebuild_val()
        except Exception as e:
            print(f"Warning: Failed to show configuration '{selected_config}': {e}")

    # 2.5. Identify and delete suppressed components from the memory model
    model_type = model.GetType() if callable(model.GetType) else model.GetType
    if model_type == 2:  # swDocASSEMBLY = 2
        try:
            print("Identifying and deleting suppressed components from memory...")
            conf_mgr = model.ConfigurationManager
            active_conf = conf_mgr.ActiveConfiguration
            root_comp = active_conf.GetRootComponent3(True)
            
            if root_comp:
                suppressed_comps = []
                def collect_suppressed(comp):
                    try:
                        supp_val = comp.GetSuppression() if callable(comp.GetSuppression) else comp.GetSuppression
                        if supp_val == 0:  # swComponentSuppressed = 0
                            suppressed_comps.append(comp)
                            return
                    except Exception:
                        pass
                    
                    try:
                        children = comp.GetChildren() if callable(comp.GetChildren) else comp.GetChildren
                        if children:
                            for child in children:
                                if child:
                                    collect_suppressed(child)
                    except Exception:
                        pass
                
                collect_suppressed(root_comp)
                
                if suppressed_comps:
                    print(f"Found {len(suppressed_comps)} suppressed component(s). Deleting from memory...")
                    model.ClearSelection2(True)
                    sel_data = None
                    try:
                        sel_mgr = model.SelectionManager
                        sel_data = sel_mgr.CreateSelectData() if callable(sel_mgr.CreateSelectData) else sel_mgr.CreateSelectData
                    except Exception as e:
                        print(f"Warning: Failed to create SelectData object: {e}")

                    for comp in suppressed_comps:
                        try:
                            if sel_data is not None:
                                comp.Select4(True, sel_data, False)
                            else:
                                comp.Select4(True, None, False)
                        except Exception as e:
                            print(f"Warning: Failed to select suppressed component: {e}")
                    
                    # Delete selected components
                    # Option 3 (swDelete_Absorbed + swDelete_Children) ensures dependent child components are deleted
                    deleted = model.Extension.DeleteSelection2(3)
                    if deleted:
                        print("Suppressed components deleted from memory successfully.")
                    else:
                        print("DeleteSelection2 returned False. Trying EditDelete...")
                        model.EditDelete()
                else:
                    print("No suppressed components found in the active configuration.")
        except Exception as e:
            print(f"Error handling suppressed components: {e}")

    # 3. Create Output Directory
    # Directory: [original_dir]/[filename]__STL/
    output_dir = os.path.join(file_dir, f"{file_name}__STL")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # 4. Configure STL Export Options (Meters, Separate Files)
    print("Configuring STL export options...")
    # Constants
    swExportStlUnits = 163 # 4 = Meters
    swSTLComponentsIntoOneFile = 32 # False = separate files
    
    # Unit: 4 (Meters)
    swApp.SetUserPreferenceIntegerValue(swExportStlUnits, 4)
    # Save all components into one file? NO.
    swApp.SetUserPreferenceToggle(swSTLComponentsIntoOneFile, False)
    
    # 5. Export Assembly to STL
    stl_output_path = os.path.join(output_dir, f"{file_name}.stl")
    print(f"Exporting Assembly to STL: {stl_output_path}")
    
    # Save
    saved = False
    
    # 1. Try Pythonic Extension.SaveAs
    # Returns Boolean
    try:
        saved = model.Extension.SaveAs(stl_output_path, 0, 0, None, None, None)
    except Exception as e:
        # print(f"Method 1 error: {e}")
        pass

    # 2. Try legacy ModelDoc2.SaveAs3 if Method 1 failed
    # Returns 0 for success, non-zero for error
    if not saved:
        try:
            res = model.SaveAs3(stl_output_path, 0, 0)
            if res == 0:
                saved = True
        except Exception as e:
            # print(f"Method 2 error: {e}")
            pass

    # 3. Extension.SaveAs with explicitly VARIANTS for ByRefs if all else failed
    if not saved:
        try:
            arg_err = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
            arg_warn = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
            saved = model.Extension.SaveAs(stl_output_path, 0, 0, None, arg_err, arg_warn)
        except Exception as e:
             print(f"SaveAs failed with exception: {e}")

    if saved:
        print("Export successful.")
    else:
        print("Export returned False (Failure). Check write permissions or filename.")

    # Close document in SolidWorks
    if model:
        try:
            val = model.GetTitle
            if callable(val):
                doc_title = val()
            else:
                doc_title = val
            
            # Strip any modification asterisk and trailing whitespaces
            if doc_title and "*" in doc_title:
                doc_title = doc_title.split("*")[0].strip()
            
            print(f"Closing document in SolidWorks (CloseDoc): {doc_title}")
            swApp.CloseDoc(doc_title)
            
            # Secondary fallback with exact filename with extension
            if doc_title != file_name_with_ext:
                swApp.CloseDoc(file_name_with_ext)
        except Exception as e:
            print(f"Failed to close document in SolidWorks: {e}")

    print("Done.")

if __name__ == "__main__":
    main()




