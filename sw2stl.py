import sys
import os
import json
import win32com.client
import pythoncom

def get_material_properties(component, swApp):
    """
    Extracts material properties (Color, Ambient, Diffuse, Specular, Shininess, Transparency, Emission).
    Prioritizes Component-level settings (overrides), then falls back to Model-level (Part) settings.
    """
    mat_props = None
    
    # Debug prefix
    comp_name = component.Name2
    # print(f"DEBUG: Checking component: {comp_name}")
    try:
        # GetSuppression might be exposed as property or method depending on Dispatch
        val = component.GetSuppression
        if callable(val):
            suppression = val()
        else:
            suppression = val
            
        # swComponentSuppressed = 0
        # swComponentLightweight = 1
        # swComponentFullyResolved = 2
        # swComponentResolved = 3
        # swComponentFullyLightweight = 4
        if suppression in (1, 4): # Only resolve if lightweight (1 or 4)
            res = component.SetSuppression2(2) # 2 = Resolve
            
            # Re-check
            val = component.GetSuppression
            if callable(val): new_suppression = val()
            else: new_suppression = val
            
        # Check Path
        val = component.GetPathName
        if callable(val): path = val()
        else: path = val
        
    except Exception as e:
         pass
    
    # 1. Component Level Override (Direct checks)
    try:
        raw_props = component.MaterialPropertyValues
        if raw_props and len(raw_props) >= 9:
            mat_props = raw_props
            # print(f"  > Found Component Override for {comp_name}")
    except:
        pass

    # 2. Configuration Specific Material (The Fix)
    if not mat_props:
        try:
            # Option 1: swThisConfiguration (1)
            # Try passing empty string instead of None for ConfigName
            raw_props = component.GetMaterialPropertyValues2(1, "") # Changed None to ""
            if raw_props and len(raw_props) >= 9 and raw_props[0] >= 0:
                mat_props = raw_props
                # print(f"  > Found Config Specific Material for {comp_name}")
        except Exception as e:
             # print(f"  > Config Material failed: {e}")
             pass

    # 3. Model Level (Part/Assembly material) - Fallback
    if not mat_props:
        model = None
        try:
            val = component.GetModelDoc2
            if callable(val): model = val()
            else: model = val
            
            if model is None:
                # print(f"  > GetModelDoc2 returned None.")
                pass
        except Exception as e:
            # print(f"  > GetModelDoc2 failed: {e}")
            try: model = component.GetModelDoc()
            except Exception as e2: pass # print(f"  > GetModelDoc (Legacy) failed: {e2}")
            
        if model:
            try:
                # IModelDoc2 / PartDoc usually has MaterialPropertyValues
                raw_props = model.MaterialPropertyValues
                if raw_props and len(raw_props) >= 9:
                    mat_props = raw_props
                    # print(f"  > Found Model Material for {comp_name}")
            except:
                try: 
                    raw_props = model.Extension.MaterialPropertyValues
                    if raw_props and len(raw_props) >= 9:
                         mat_props = raw_props
                         # print(f"  > Found Model Ext Material for {comp_name}")
                except: pass
        
        # 4. Fallback: Try obtaining ModelDoc from SW Application by Path
        if not mat_props and not model:
            try:
                path_val = component.GetPathName
                if callable(path_val): c_path = path_val()
                else: c_path = path_val
                
                if c_path:
                    # GetOpenDocumentByName accepts filename/path
                    model_doc = swApp.GetOpenDocumentByName(c_path)
                    if model_doc:
                        # print(f"  > Recovered ModelDoc via app.GetOpenDocumentByName")
                        # Try getting material from this doc
                        try:
                            raw_props = model_doc.MaterialPropertyValues
                            if raw_props and len(raw_props) >= 9:
                                mat_props = raw_props
                        except:
                             try:
                                raw_props = model_doc.Extension.MaterialPropertyValues
                                if raw_props and len(raw_props) >= 9:
                                    mat_props = raw_props
                             except: pass
            except Exception as e:
                # print(f"  > App Fallback failed: {e}")
                pass
        
        if not mat_props and not model:
            # print(f"DEBUG: ModelDoc not found for {comp_name} (Lightweight?)")
            pass

    if mat_props:
        return {
            "color": [mat_props[0], mat_props[1], mat_props[2]], # R, G, B
            "ambient": mat_props[3],
            "diffuse": mat_props[4],
            "specular": mat_props[5],
            "shininess": mat_props[6],
            "transparency": mat_props[7],
            "emission": mat_props[8]
        }
    
    # Default values if retrieval failed
    return {
        "color": [0.8, 0.8, 0.8],
        "ambient": 1.0,
        "diffuse": 1.0,
        "specular": 1.0,
        "shininess": 0.5,
        "transparency": 0.0,
        "emission": 0.0
    }

def traverse_and_save_materials(component, output_dir, assembly_name, swApp):
    """
    Recursively traverses the assembly. 
    For each part (leaf node), generates a JSON file with material properties.
    Filename: "{assembly_name} - {component.Name2}.json"
    """
    # Skip suppressed components
    try:
        val = component.GetSuppression
        if callable(val):
            suppression = val()
        else:
            suppression = val
            
        if suppression == 0: # swComponentSuppressed
            return
    except:
        pass

    # Get Children
    children = component.GetChildren
    if callable(children):
        children = children()
    
    if children:
        # It's an assembly or sub-assembly
        for child in children:
            if child:
                traverse_and_save_materials(child, output_dir, assembly_name, swApp)
    else:
        # It's a leaf part (likely exported as an STL)
        # Construct expected STL filename pattern: AssemblyName - ComponentName-Instance.stl
        # Note: Name2 usually includes Instance Number (e.g. Part-1)
        part_name = component.Name2
        # Sanitize name (replace / with space to match STL export behavior)
        part_name = part_name.replace('/', ' ').replace('\\', ' ')
        
        # Expected Full Filename
        full_json_name = f"{assembly_name} - {part_name}.json"
        target_json_name = full_json_name 
        
        # Check against existing STLs to handle Truncation (___)
        # 1. Expected STL Name
        expected_stl_name = f"{assembly_name} - {part_name}.stl"
        expected_stl_path = os.path.join(output_dir, expected_stl_name)
        
        if not os.path.exists(expected_stl_path):
            # 2. Search for truncated version
            # Pattern: Start...___...End.stl
            # We iterate all STLs and check if they "match" the full name vaguely
            stl_files = os.listdir(output_dir)
            for f in stl_files:
                if f.lower().endswith('.stl') and "___" in f:
                    # Candidates
                    # Check if 'f' can be a truncated version of 'expected_stl_name'
                    # e.g. "LongNamePart1...___...End.stl"
                    # Simple heuristic: Split by ___ and check if parts exist in full name in order
                    # Or simpler: SolidWorks usually truncates the MIDDLE.
                    
                    # Let's try to match prefix and suffix
                    prefix, suffix = f.split("___", 1)
                    suffix_base, _ = os.path.splitext(suffix)
                    prefix_base = prefix
                    
                    # Warning: This is loose matching.
                    # But if the full name STARTS with prefix AND ENDS with suffix (extensionless), match.
                    
                    # Handle extension in expected name
                    base_expected = os.path.splitext(expected_stl_name)[0]
                    
                    if base_expected.startswith(prefix_base) and base_expected.endswith(suffix_base):
                        # FOUND MATCH
                        # Use this filename for JSON
                        target_json_name = os.path.splitext(f)[0] + ".json"
                        break
        
        json_path = os.path.join(output_dir, target_json_name)
        
        # Get Material
        material = get_material_properties(component, swApp)
        
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(material, f, indent=4)
        except Exception as e:
            # If file exists and has content, maybe ignore or log differently?
            if os.path.exists(json_path) and os.path.getsize(json_path) > 0:
                pass 
            else:
                print(f"Failed to save {json_filename}: {e}")

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
            
            def choose_config_dialog(config_names):
                selected = [config_names[0]]
                root = tk.Tk()
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
                
                lbl = tk.Label(root, text="Select SolidWorks Configuration:", font=("Arial", 10, "bold"), pady=10)
                lbl.pack()
                
                frame = tk.Frame(root)
                frame.pack(fill="x", padx=20, pady=5)
                
                scroll = tk.Scrollbar(frame, orient="vertical")
                listb = tk.Listbox(frame, yscrollcommand=scroll.set, font=("Arial", 10), height=6)
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
        
        # 6. Generate Individual Material JSONs
        print("Generating individual material JSONs...")
        try:
             conf_mgr = model.ConfigurationManager
             active_conf = conf_mgr.ActiveConfiguration
             root_comp = active_conf.GetRootComponent3(True)
             
             if root_comp:
                 traverse_and_save_materials(root_comp, output_dir, file_name, swApp)
                 print("Material JSONs generated.")
        except Exception as e:
             print(f"Error generating material JSONs: {e}")
             
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
            
            print(f"Closing document in SolidWorks (QuitDoc): {doc_title}")
            swApp.QuitDoc(doc_title)
            
            # Secondary fallback with exact filename with extension
            if doc_title != file_name_with_ext:
                swApp.QuitDoc(file_name_with_ext)
        except Exception as e:
            print(f"Failed to close document in SolidWorks: {e}")

    print("Done.")

if __name__ == "__main__":
    main()




