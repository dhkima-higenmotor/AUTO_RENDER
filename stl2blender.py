import sys
import os
import subprocess
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python stl2blender.py <path_to_stl_directory>")
        sys.exit(1)

    input_path = Path(sys.argv[1]).resolve()
    
    if not input_path.exists():
        print(f"Error: The path '{input_path}' does not exist.")
        sys.exit(1)

    # 1. Determine new directory name
    dir_name = input_path.name
    if "__STL" in dir_name:
        new_dir_name = dir_name.replace("__STL", "__BLENDER")
    else:
        print(f"Warning: Directory name '{dir_name}' does not contain '__STL'. Appending '__BLENDER' instead.")
        new_dir_name = dir_name + "__BLENDER"

    # 2. Create the new directory
    parent_dir = input_path.parent
    new_dir_path = parent_dir / new_dir_name
    
    try:
        new_dir_path.mkdir(exist_ok=True)
        print(f"Created directory: {new_dir_path}")
    except Exception as e:
        print(f"Error creating directory: {e}")
        sys.exit(1)

    # 3. Read Blender configuration
    script_dir = Path(__file__).parent.resolve()
    blender_exe_config = script_dir / "blender_exe.txt"
    
    if not blender_exe_config.exists():
        print(f"Error: Configuration file '{blender_exe_config}' not found.")
        sys.exit(1)
        
    try:
        with open(blender_exe_config, "r") as config_f:
            blender_exe = config_f.read().strip()
    except Exception as e:
         print(f"Error reading configuration file: {e}")
         sys.exit(1)

    if not os.path.exists(blender_exe):
        print(f"Error: Blender executable not found at '{blender_exe}'")
        sys.exit(1)

    # 4. Determine blend file path
    if "__BLENDER" in new_dir_name:
        base_name = new_dir_name.replace("__BLENDER", "")
    else:
        base_name = new_dir_name
        
    blend_file_name = f"{base_name}.blend"
    blend_file_path = new_dir_path / blend_file_name
    
    print(f"Creating Blender file: {blend_file_path}")

    # 5. Prepare Blender script
    # Escape backslashes for usage in Python string within the script
    blend_file_path_str = str(blend_file_path).replace("\\", "\\\\")
    input_path_str = str(input_path).replace("\\", "\\\\")
    
    import_script_path = new_dir_path / "import_stls.py"
    
    import_script_content = f"""
import bpy
import os
import mathutils

def run():
    # Helper to set socket value robustly across Blender versions and locales
    def set_socket(node, name, value):
        if not node: return False
        
        target_socket = None
        if name in node.inputs:
            target_socket = node.inputs[name]
        else:
            target = name.lower().replace(" ", "").replace("_", "")
            for s in node.inputs:
                s_name = s.name.lower().replace(" ", "").replace("_", "")
                s_id = s.identifier.lower().replace(" ", "").replace("_", "")
                if s_name == target or s_id == target:
                    target_socket = s
                    break
                    
        if target_socket is None:
            print(f"DEBUG: Socket '{{name}}' not found in node '{{node.name}}'")
            return False
            
        try:
            # Check if target is array-like and value is iterable
            if hasattr(target_socket.default_value, "__len__") and not isinstance(value, (str, bytes)) and hasattr(value, "__iter__"):
                val_list = [float(v) for v in value]
                if len(target_socket.default_value) == 4 and len(val_list) == 3:
                    val_list.append(1.0)
                
                for idx, val in enumerate(val_list):
                    if idx < len(target_socket.default_value):
                        target_socket.default_value[idx] = val
                print(f"DEBUG: Element-wise set socket '{{name}}' in '{{node.name}}' to {{val_list}}")
            else:
                target_socket.default_value = value
                print(f"DEBUG: Directly set socket '{{name}}' in '{{node.name}}' to {{value}}")
            return True
        except Exception as e:
            print(f"DEBUG: Error setting socket '{{name}}' in node '{{node.name}}' to {{value}}: {{e}}")
            try:
                target_socket.default_value = value
                return True
            except Exception as e2:
                print(f"DEBUG: Fallback direct set failed: {{e2}}")
                return False

    # Clear existing objects
    bpy.ops.wm.read_homefile(use_empty=True)
    
    input_dir = "{input_path_str}"
    
    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{{input_dir}}' not found inside Blender.")
        return

    # Get STL files and sort them alphabetically
    stl_files = sorted([f for f in os.listdir(input_dir) if f.lower().endswith('.stl')])
    
    print(f"Found {{len(stl_files)}} STL files to import.")
    
    for f in stl_files:
        filepath = os.path.join(input_dir, f)
        print(f"Importing: {{f}}")
        
        # Record objects before import to accurately detect new mesh
        pre_import_objs = set(bpy.data.objects.keys())
        
        try:
             # Use the new C++ importer (Blender 4.0+)
             bpy.ops.wm.stl_import(
                filepath=filepath,
                global_scale=1.0,
                forward_axis='Z',
                up_axis='Y'
             )
        except AttributeError:
             print(f"Error: Could not find stl_import operator for {{f}}")
             continue
        except TypeError as e:
             print(f"Error importing {{f}}: {{e}}")
             continue

        # Detect imported object(s)
        post_import_objs = set(bpy.data.objects.keys())
        imported_objs = [bpy.data.objects[name] for name in (post_import_objs - pre_import_objs)]
        if not imported_objs:
             imported_objs = bpy.context.selected_objects
             if not imported_objs and bpy.context.active_object:
                  imported_objs = [bpy.context.active_object]



    # 4.5. Special Material Override & Default Material Assignment (OUTSIDE the STL import loop)
    print("Applying smart material assignment based on component names...")
    
    # Define helper to create/retrieve materials with proper properties (fallback)
    def get_or_create_material(name, diffuse_color, metallic, roughness, specular=0.5, extra_setup_func=None):
        mat = bpy.data.materials.get(name)
        if not mat:
            mat = bpy.data.materials.new(name=name)
        mat.diffuse_color = diffuse_color + (1.0,) if len(diffuse_color) == 3 else diffuse_color
        if bpy.app.version < (5, 0, 0):
            if hasattr(mat, 'use_nodes') and not mat.use_nodes:
                try:
                    mat.use_nodes = True
                except:
                    pass
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        
        out_node = nodes.new("ShaderNodeOutputMaterial")
        out_node.location = (400, 0)
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)
        links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])
        
        if bsdf:
            set_socket(bsdf, 'Base Color', diffuse_color)
            set_socket(bsdf, 'Metallic', metallic)
            set_socket(bsdf, 'Roughness', roughness)
            if not set_socket(bsdf, 'Specular IOR Level', specular):
                set_socket(bsdf, 'Specular', specular)
            if extra_setup_func:
                extra_setup_func(bsdf)
        return mat

    def setup_brushed_nickel(bsdf):
        set_socket(bsdf, 'Anisotropic', 0.6)
        set_socket(bsdf, 'Anisotropic Rotation', 0.2)
        
    mat_brushed_nickel = get_or_create_material("Mat_Brushed_Nickel", (0.62, 0.60, 0.57), 1.0, 0.35, extra_setup_func=setup_brushed_nickel)
    mat_stainless_steel = get_or_create_material("Mat_Stainless_Steel", (0.7, 0.7, 0.7), 1.0, 0.22)
    mat_copper = get_or_create_material("Mat_Copper", (0.95, 0.64, 0.54), 1.0, 0.2)
    mat_carbon_steel = get_or_create_material("Mat_Carbon_Steel", (0.54, 0.55, 0.55), 1.0, 0.3)
    mat_green_plastic = get_or_create_material("Mat_Green_Plastic", (0.1, 0.6, 0.2), 0.0, 0.4)
    mat_nickel = get_or_create_material("Mat_Nickel", (0.66, 0.60, 0.54), 1.0, 0.25)
    mat_aluminium = get_or_create_material("Mat_Aluminium", (0.91, 0.92, 0.92), 1.0, 0.3)
    mat_brass = get_or_create_material("Mat_Brass", (0.88, 0.72, 0.38), 1.0, 0.2)

    def load_blenderkit_material_cached(asset_ids):
        import os
        from pathlib import Path
        import bpy
        
        global_dir = Path(os.path.expanduser("~")) / "blenderkit_data"
        try:
            for addon_name in bpy.context.preferences.addons.keys():
                if "blenderkit" in addon_name:
                    prefs = bpy.context.preferences.addons[addon_name].preferences
                    if hasattr(prefs, "global_dir") and prefs.global_dir:
                        global_dir = Path(prefs.global_dir)
                        break
        except Exception:
            pass
            
        materials_dir = global_dir / "materials"
        if not materials_dir.exists():
            return None
            
        mat = None
        # Turn off relative paths temporarily to prevent cross-drive warnings on Windows (e.g. C: to D:)
        filepath_prefs = bpy.context.preferences.filepaths
        orig_relative = filepath_prefs.use_relative_paths
        filepath_prefs.use_relative_paths = False
        try:
            for asset_id in asset_ids:
                for root, dirs, files in os.walk(materials_dir):
                    if asset_id in root or any(asset_id in d for d in dirs):
                        for f in files:
                            if f.endswith(".blend"):
                                blend_path = Path(root) / f
                                mat_name = None
                                try:
                                    with bpy.data.libraries.load(str(blend_path), relative=False) as (data_from, data_to):
                                        if data_from.materials:
                                            mat_name = data_from.materials[0]
                                            existing = bpy.data.materials.get(mat_name)
                                            if existing:
                                                mat = existing
                                            else:
                                                data_to.materials = [mat_name]
                                except Exception as load_err:
                                    print(f"Error loading from cache: {{load_err}}")
                                if mat is None and mat_name is not None:
                                    mat = bpy.data.materials.get(mat_name)
                                if mat:
                                    break
                    if mat:
                        break
                if mat:
                    break
        finally:
            filepath_prefs.use_relative_paths = orig_relative
        return mat

    def apply_blenderkit_material(obj, asset_ids, fallback_material):
        import os
        from pathlib import Path
        import urllib.request
        import json
        import bpy
        
        # 1. Try to load from cache first
        mat = load_blenderkit_material_cached(asset_ids)
        if mat:
            obj.data.materials.clear()
            obj.data.materials.append(mat)
            if hasattr(obj.data, "polygons"):
                for poly in obj.data.polygons:
                    poly.material_index = 0
            print(f"Applied BlenderKit material '{{mat.name}}' from cache to '{{obj.name}}'")
            return

        # If running in background mode, we cannot download new assets from BlenderKit (daemon isn't running).
        if bpy.app.background:
            print(f"BlenderKit material with ID(s) {{asset_ids}} not found in cache. Running in background/headless mode, skipping download.")
            if fallback_material:
                obj.data.materials.clear()
                obj.data.materials.append(fallback_material)
                if hasattr(obj.data, "polygons"):
                    for poly in obj.data.polygons:
                        poly.material_index = 0
                print(f"Applied procedural fallback material '{{fallback_material.name}}' to '{{obj.name}}'")
            return

        print(f"BlenderKit material with ID(s) {{asset_ids}} not found in cache. Triggering download...")
        
        # 2. Trigger background download
        ext_name = None
        import addon_utils
        for mod in addon_utils.modules():
            if "blenderkit" in mod.__name__:
                ext_name = mod.__name__
                break
                
        if ext_name:
            try:
                default_state, loaded_state = addon_utils.check(ext_name)
                if not loaded_state:
                    addon_utils.enable(ext_name)
                
                # Fetch details, clean avatar fields, inject and trigger
                asset_id = asset_ids[0]
                url = f"https://www.blenderkit.com/api/v1/assets/{{asset_id}}/"
                req = urllib.request.Request(url, headers={{'User-Agent': 'Mozilla/5.0'}})
                with urllib.request.urlopen(req) as response:
                    asset_data = json.loads(response.read().decode())
                
                if "author" in asset_data:
                    author = asset_data["author"]
                    for k in list(author.keys()):
                        if k.startswith("avatar") and k != "avatar128":
                            author.pop(k, None)
                
                # Resolve the search module dynamically
                import sys
                search_module = None
                for name, module in sys.modules.items():
                    if "blenderkit" in name and name.endswith(".search"):
                        search_module = module
                        break
                        
                if search_module:
                    try:
                        parsed_asset_data = search_module.parse_result(asset_data)
                    except Exception:
                        parsed_asset_data = asset_data
                        if "assetBaseId" not in parsed_asset_data:
                            parsed_asset_data["assetBaseId"] = asset_id
                        if "assetType" not in parsed_asset_data:
                            parsed_asset_data["assetType"] = "material"
                    
                    history_step = search_module.get_active_history_step()
                    history_step["search_results"] = [parsed_asset_data]
                    
                    # Run download operator
                    bpy.ops.scene.blenderkit_download(
                        asset_index=0,
                        target_object=obj.name
                    )
                    print(f"Triggered background download for '{{asset_id}}' on '{{obj.name}}'")
            except Exception as download_err:
                print(f"Failed to trigger download for '{{asset_ids}}': {{download_err}}")
        else:
            print("BlenderKit addon is not installed or enabled.")

        # 3. Apply fallback
        if fallback_material:
            obj.data.materials.clear()
            obj.data.materials.append(fallback_material)
            if hasattr(obj.data, "polygons"):
                for poly in obj.data.polygons:
                    poly.material_index = 0
            print(f"Applied procedural fallback material '{{fallback_material.name}}' to '{{obj.name}}'")

    def apply_blenderkit_hdri(asset_ids):
        import os
        from pathlib import Path
        import bpy
        import urllib.request
        import json

        # 1. Search local cache first
        global_dir = Path(os.path.expanduser("~")) / "blenderkit_data"
        try:
            for addon_name in bpy.context.preferences.addons.keys():
                if "blenderkit" in addon_name:
                    prefs = bpy.context.preferences.addons[addon_name].preferences
                    if hasattr(prefs, "global_dir") and prefs.global_dir:
                        global_dir = Path(prefs.global_dir)
                        break
        except Exception:
            pass
            
        hdrs_dir = global_dir / "hdrs"
        image_path = None
        if hdrs_dir.exists():
            for asset_id in asset_ids:
                for root, dirs, files in os.walk(hdrs_dir):
                    if asset_id in root or any(asset_id in d for d in dirs):
                        for f in files:
                            if f.lower().endswith((".exr", ".hdr")):
                                image_path = Path(root) / f
                                break
                    if image_path:
                        break
                if image_path:
                    break
                    
        # 2. If found, load and apply environment texture
        if image_path:
            try:
                img = bpy.data.images.load(str(image_path))
                world = bpy.context.scene.world
                if not world:
                    world = bpy.data.worlds.new("World")
                    bpy.context.scene.world = world
                if bpy.app.version < (5, 0, 0):
                    world.use_nodes = True
                nodes = world.node_tree.nodes
                links = world.node_tree.links
                nodes.clear()
                
                out_node = nodes.new("ShaderNodeOutputWorld")
                out_node.location = (400, 0)
                bg_node = nodes.new("ShaderNodeBackground")
                bg_node.location = (200, 0)
                bg_node.inputs['Strength'].default_value = 1.0
                tex_node = nodes.new("ShaderNodeTexEnvironment")
                tex_node.location = (0, 0)
                tex_node.image = img
                
                links.new(tex_node.outputs['Color'], bg_node.inputs['Color'])
                links.new(bg_node.outputs['Background'], out_node.inputs['Surface'])
                print(f"Applied BlenderKit HDRI background '{{image_path.name}}' from cache.")
                return True
            except Exception as load_err:
                print(f"Error loading cached HDRI: {{load_err}}")

        # 3. If not found in cache, trigger background download
        if bpy.app.background:
            print(f"Office HDRI ID(s) {{asset_ids}} not found in cache. Running in background/headless mode, skipping download.")
        else:
            print(f"Office HDRI ID(s) {{asset_ids}} not found in cache. Triggering download...")
            ext_name = None
            import addon_utils
            for mod in addon_utils.modules():
                if "blenderkit" in mod.__name__:
                    ext_name = mod.__name__
                    break
                    
            if ext_name:
                try:
                    default_state, loaded_state = addon_utils.check(ext_name)
                    if not loaded_state:
                        addon_utils.enable(ext_name)
                    
                    # Fetch details, clean avatar fields, inject and trigger
                    asset_id = asset_ids[0]
                    url = f"https://www.blenderkit.com/api/v1/assets/{{asset_id}}/"
                    req = urllib.request.Request(url, headers={{'User-Agent': 'Mozilla/5.0'}})
                    with urllib.request.urlopen(req) as response:
                        asset_data = json.loads(response.read().decode())
                    
                    if "author" in asset_data:
                        author = asset_data["author"]
                        for k in list(author.keys()):
                            if k.startswith("avatar") and k != "avatar128":
                                author.pop(k, None)
                    
                    import sys
                    search_module = None
                    for name, module in sys.modules.items():
                        if "blenderkit" in name and name.endswith(".search"):
                            search_module = module
                            break
                            
                    if search_module:
                        try:
                            parsed_asset_data = search_module.parse_result(asset_data)
                        except Exception:
                            parsed_asset_data = asset_data
                            if "assetBaseId" not in parsed_asset_data:
                                parsed_asset_data["assetBaseId"] = asset_id
                            if "assetType" not in parsed_asset_data:
                                parsed_asset_data["assetType"] = "hdr"
                        
                        history_step = search_module.get_active_history_step()
                        history_step["search_results"] = [parsed_asset_data]
                        
                        bpy.ops.scene.blenderkit_download(
                            asset_index=0
                        )
                        print(f"Triggered background HDRI download for '{{asset_id}}'")
                except Exception as download_err:
                    print(f"Failed to trigger download: {{download_err}}")
            else:
                print("BlenderKit addon is not installed or enabled.")
            
        # Fallback to white background if download not ready
        world = bpy.context.scene.world
        if not world:
            world = bpy.data.worlds.new("World_White")
            bpy.context.scene.world = world
        if bpy.app.version < (5, 0, 0):
            world.use_nodes = True
        nodes = world.node_tree.nodes
        links = world.node_tree.links
        nodes.clear()
        out_node = nodes.new("ShaderNodeOutputWorld")
        out_node.location = (400, 0)
        bg_node = nodes.new("ShaderNodeBackground")
        bg_node.location = (200, 0)
        bg_node.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
        bg_node.inputs['Strength'].default_value = 1.0
        links.new(bg_node.outputs['Background'], out_node.inputs['Surface'])
        print("Applied fallback solid white background.")
        return False

    hw_keywords = ["screw", "bolt", "key", "pin", "washer", "nut", "rivet", "나사", "볼트", "핀", "와셔", "너트", "리벳", "키"]
    bearing_keywords = ["bearing", "베어링", "6803zz", "6905zz", "6807zz", "6808zz", "6809zz", "6903zz", "nsk", "rau"]
    
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            name_lower = obj.name.lower()
            assigned_mat = None
            asset_ids = []
            
            # Rule 0a: AP-, BP-, PCB, CONNECTOR -> Green Plastic
            if any(kw in name_lower for kw in ["ap-", "bp-", "pcb", "connector"]):
                assigned_mat = mat_green_plastic
                asset_ids = ["387e8822-6486-473d-92ff-3a91f426dd64"]

            # Rule 0b: HEX_POST -> Brass
            elif "hex_post" in name_lower:
                assigned_mat = mat_brass
                asset_ids = ["f0c815ea-41ce-448e-ade1-8bcf1beebd3e", "e7be890c-f95e-43eb-9686-6a1e09e25aa4"]

            # Rule 1: Brushed Nickel (Screws, Bolts, Keys, etc.)
            elif any(hw in name_lower for hw in hw_keywords):
                assigned_mat = mat_brushed_nickel
                asset_ids = ["b058fc10-bd2a-4cb5-8e05-f330fad99101"]
                
            # Rule 2: Stainless Steel (Bearings)
            elif any(brg in name_lower for brg in bearing_keywords):
                assigned_mat = mat_stainless_steel
                asset_ids = ["79540f1a-c977-436f-b949-d9a2aa4c44a1"]
                
            # Rule 3: STATOR + COIL -> Copper
            elif "stator" in name_lower and "coil" in name_lower:
                assigned_mat = mat_copper
                asset_ids = ["b19cef5d-04f7-4569-b53f-8c3475b2526d", "cba239ae-5280-48f1-a1ba-61e36d98d406"]
                
            # Rule 4: STATOR + CORE -> Carbon Steel
            elif "stator" in name_lower and "core" in name_lower:
                assigned_mat = mat_carbon_steel
                asset_ids = ["58281db0-4437-4069-b925-5a8ab1c32197"]
                
            # Rule 5: STATOR + BOBBIN -> Green Plastic
            elif "stator" in name_lower and "bobbin" in name_lower:
                assigned_mat = mat_green_plastic
                asset_ids = ["387e8822-6486-473d-92ff-3a91f426dd64"]
                
            # Rule 6: ROTOR + MAGNET -> Nickel (which is Brushed Nickel per request #2)
            elif "rotor" in name_lower and "magnet" in name_lower:
                assigned_mat = mat_brushed_nickel
                asset_ids = ["b058fc10-bd2a-4cb5-8e05-f330fad99101"]
                
            # Rule 7: Fallback -> Aluminium
            else:
                assigned_mat = mat_aluminium
                asset_ids = ["8e58e654-b722-49b7-aa44-e24210d5eede"]
                
            if assigned_mat:
                apply_blenderkit_material(obj, asset_ids, assigned_mat)

    # 4.6. Identify Outer/Housing Components for Pearl Black Plastic (OUTSIDE the STL import loop)
    print("Identifying outer housing components for Pearl Black Plastic...")
    mesh_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    
    # Filter out hardware and internal machine components from outer housing candidates
    candidate_objs = []
    hw_keywords = ["screw", "bolt", "key", "pin", "washer", "nut", "rivet", "bearing", "나사", "볼트", "핀", "와셔", "너트", "리벳", "키", "베어링"]
    for obj in mesh_objs:
        name_lower = obj.name.lower()
        # Filter out hardware
        if any(hw in name_lower for hw in hw_keywords) or any(brg in name_lower for brg in bearing_keywords):
            continue
        # Filter out motor internals
        if "stator" in name_lower and ("coil" in name_lower or "core" in name_lower or "bobbin" in name_lower):
            continue
        if "rotor" in name_lower and "magnet" in name_lower:
            continue
        # Filter out PCBs, connectors, plates, and hex posts
        if any(kw in name_lower for kw in ["ap-", "bp-", "pcb", "connector", "hex_post"]):
            continue
        candidate_objs.append(obj)
            
    if candidate_objs:
        # Calculate overall scene bounding box from candidates
        import mathutils
        global_min = mathutils.Vector((float('inf'), float('inf'), float('inf')))
        global_max = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))
        
        obj_bounds = {{}}
        for obj in candidate_objs:
            o_min = mathutils.Vector((float('inf'), float('inf'), float('inf')))
            o_max = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))
            for corner in obj.bound_box:
                world_corner = obj.matrix_world @ mathutils.Vector(corner)
                o_min.x = min(o_min.x, world_corner.x)
                o_min.y = min(o_min.y, world_corner.y)
                o_min.z = min(o_min.z, world_corner.z)
                o_max.x = max(o_max.x, world_corner.x)
                o_max.y = max(o_max.y, world_corner.y)
                o_max.z = max(o_max.z, world_corner.z)
            
            obj_bounds[obj] = (o_min, o_max)
            
            global_min.x = min(global_min.x, o_min.x)
            global_min.y = min(global_min.y, o_min.y)
            global_min.z = min(global_min.z, o_min.z)
            global_max.x = max(global_max.x, o_max.x)
            global_max.y = max(global_max.y, o_max.y)
            global_max.z = max(global_max.z, o_max.z)
            
        # Scene Size
        scene_size = global_max - global_min
        max_scene_dim = max(scene_size.x, scene_size.y, scene_size.z)
        if max_scene_dim == 0: max_scene_dim = 1.0
        
        # Score each object based on size and edge proximity
        scores = []
        for obj in candidate_objs:
            o_min, o_max = obj_bounds[obj]
            o_size = o_max - o_min
            diag = o_size.length
            
            # Check if it touches outer boundary (Threshold: 5% of max scene dim)
            threshold = max_scene_dim * 0.05
            touches_edge = False
            if (abs(o_min.x - global_min.x) < threshold or abs(o_max.x - global_max.x) < threshold or
                abs(o_min.y - global_min.y) < threshold or abs(o_max.y - global_max.y) < threshold or
                abs(o_min.z - global_min.z) < threshold or abs(o_max.z - global_max.z) < threshold):
                touches_edge = True
            
            score = diag
            if touches_edge:
                score *= 5.0
                
            # Extra weight for naming
            name_lower = obj.name.lower()
            for keyword in ['housing', 'case', 'cover', 'body', 'frame', 'shell', 'panel', 'enclosure', '하우징', '케이스', '커버', '외관', '몸체', '프레임', '패널', '셀']:
                if keyword in name_lower:
                    score *= 2.0
                    break
                    
            scores.append((score, obj))
            
        scores.sort(key=lambda x: x[0], reverse=True)
        
        # Select outer objects based on naming keyword OR top geometric scores
        outer_objs = []
        
        # 1. Force include any object with housing keywords in its name
        keywords = ['housing', 'case', 'cover', 'body', 'frame', 'shell', 'panel', 'enclosure', '하우징', '케이스', '커버', '외관', '몸체', '프레임', '패널', '셀']
        for score, obj in scores:
            name_lower = obj.name.lower()
            if any(kw in name_lower for kw in keywords):
                if obj not in outer_objs:
                    outer_objs.append(obj)
                    
        # 2. Select top scoring objects based on geometry (up to 33% of candidate objects, max 12)
        geom_limit = max(2, min(12, len(candidate_objs) // 3))
        for score, obj in scores[:geom_limit]:
            if obj not in outer_objs:
                outer_objs.append(obj)
                
        # Fallback: Ensure at least one object is selected
        if not outer_objs and scores:
            outer_objs.append(scores[0][1])
            
        print(f"Selected {{len(outer_objs)}} outer objects: {{[o.name for o in outer_objs]}}")
        
        # Apply Pearl Black Painted Plastic Material (procedural fallback)
        mat_name = "Mat_Pearl_Black_Plastic"
        mat = bpy.data.materials.get(mat_name)
        if not mat:
            mat = bpy.data.materials.new(name=mat_name)
            
        mat.diffuse_color = (0.1, 0.1, 0.1, 1.0)
        if bpy.app.version < (5, 0, 0):
            if hasattr(mat, 'use_nodes') and not mat.use_nodes:
                try:
                    mat.use_nodes = True
                except:
                    pass
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        
        out_node = nodes.new("ShaderNodeOutputMaterial")
        out_node.location = (400, 0)
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)
        links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])
        
        if bsdf:
            print("DEBUG: Mat_Pearl_Black_Plastic bsdf inputs: " + ", ".join([f"{{s.name}} ({{s.identifier}})" for s in bsdf.inputs]))
            set_socket(bsdf, 'Base Color', (0.1, 0.1, 0.1))
            set_socket(bsdf, 'Roughness', 0.9)
            set_socket(bsdf, 'Metallic', 0.7)
            if not set_socket(bsdf, 'Coat Weight', 0.0):
                set_socket(bsdf, 'Clearcoat', 0.0)
                    
        # Apply to selected outer objects
        for obj in outer_objs:
            apply_blenderkit_material(obj, ["386d3d08-9144-4145-881e-4b2d25c8202e"], mat)

    # Center all objects
    # Select all mesh objects
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    
    if mesh_objects:
        min_corner = mathutils.Vector((float('inf'), float('inf'), float('inf')))
        max_corner = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))
        
        for obj in mesh_objects:
            # We need to consider the world matrix if objects were moved (unlikely here but safe)
            # stl import places objects at (0,0,0) usually, but vertices are offset.
            for corner in obj.bound_box:
                world_corner = obj.matrix_world @ mathutils.Vector(corner)
                min_corner.x = min(min_corner.x, world_corner.x)
                min_corner.y = min(min_corner.y, world_corner.y)
                min_corner.z = min(min_corner.z, world_corner.z)
                max_corner.x = max(max_corner.x, world_corner.x)
                max_corner.y = max(max_corner.y, world_corner.y)
                max_corner.z = max(max_corner.z, world_corner.z)
        
        center = (min_corner + max_corner) / 2.0
        print(f"Calculated center: {{center}}")
        
        # Move all objects
        for obj in bpy.context.scene.objects:
             # Simply subtracting the center vector from location works 
             # because we want to shift the whole scene so 'center' goes to (0,0,0)
             obj.location -= center
             
        print("Centered all objects to origin.")
        

        
        # 5. Camera Setup
        print("Setting up Camera...")
        
        # Calculate max dimension for ortho scale
        size_vec = max_corner - min_corner
        max_dim = max(size_vec.x, size_vec.y, size_vec.z)
        if max_dim == 0: max_dim = 10.0 # Fallback
        
        # Create Target Empty at Origin
        bpy.ops.object.empty_add(location=(0, 0, 0))
        target = bpy.context.active_object
        target.name = "Cam_Target"

        # Create 4 Isometric Cameras (Front-Right, Front-Left, Back-Right, Back-Left)
        # Position them at a safe distance (max_dim * 3) to prevent clipping
        camera_configs = [
            ("Camera_ISO_FR", (max_dim*3.0, -max_dim*3.0, max_dim*3.0)),
            ("Camera_ISO_FL", (-max_dim*3.0, -max_dim*3.0, max_dim*3.0)),
            ("Camera_ISO_BR", (max_dim*3.0, max_dim*3.0, max_dim*3.0)),
            ("Camera_ISO_BL", (-max_dim*3.0, max_dim*3.0, max_dim*3.0))
        ]
        
        # Calculate mathematically exact target scale based on 3D bounding box projection
        corners = [
            mathutils.Vector((min_corner.x, min_corner.y, min_corner.z)),
            mathutils.Vector((min_corner.x, min_corner.y, max_corner.z)),
            mathutils.Vector((min_corner.x, max_corner.y, min_corner.z)),
            mathutils.Vector((min_corner.x, max_corner.y, max_corner.z)),
            mathutils.Vector((max_corner.x, min_corner.y, min_corner.z)),
            mathutils.Vector((max_corner.x, min_corner.y, max_corner.z)),
            mathutils.Vector((max_corner.x, max_corner.y, min_corner.z)),
            mathutils.Vector((max_corner.x, max_corner.y, max_corner.z)),
        ]
        
        aspect_ratio = 800.0 / 600.0
        max_required_scale = 0.0
        cameras = []
        first_cam = None
        
        for cam_name, cam_loc in camera_configs:
            bpy.ops.object.camera_add(location=cam_loc)
            cam_obj = bpy.context.active_object
            cam_obj.name = cam_name
            cam_obj.data.type = 'ORTHO'
            
            # Add TrackTo Constraint to look at origin
            track_to = cam_obj.constraints.new(type='TRACK_TO')
            track_to.target = target
            track_to.track_axis = 'TRACK_NEGATIVE_Z'
            track_to.up_axis = 'UP_Y'
            
            cameras.append(cam_obj)
            if not first_cam:
                first_cam = cam_obj
                
        # Update scene to solve constraints and calculate camera world matrices
        bpy.context.view_layer.update()
        
        for cam_obj in cameras:
            inv_matrix = cam_obj.matrix_world.inverted()
            local_corners = [inv_matrix @ c for c in corners]
            
            min_x = min(c.x for c in local_corners)
            max_x = max(c.x for c in local_corners)
            min_y = min(c.y for c in local_corners)
            max_y = max(c.y for c in local_corners)
            
            width = max_x - min_x
            height = max_y - min_y
            
            # Since aspect ratio is 800/600 = 1.3333 (> 1), we use the wide screen formula
            required_scale = max(width, height * aspect_ratio)
            if required_scale > max_required_scale:
                max_required_scale = required_scale
                
        # Apply the final target scale with 5% safety margin (95% fill)
        target_scale = max_required_scale / 0.95
        
        for cam_obj in cameras:
            cam_obj.data.ortho_scale = target_scale
            print(f"Set target scale for {{cam_obj.name}} to {{target_scale}}")
            
        # Set the first camera as active
        bpy.context.scene.camera = first_cam

        # 7. Lighting Setup
        print("Setting up Lighting...")
        
        def create_light(name, type, location, energy, size):
            bpy.ops.object.light_add(type=type, location=location)
            light = bpy.context.active_object
            light.name = name
            light.data.energy = energy
            if type == 'AREA':
                light.data.shape = 'SQUARE'
                light.data.size = size
            
            # Track to origin
            track = light.constraints.new(type='TRACK_TO')
            track.target = target
            track.track_axis = 'TRACK_NEGATIVE_Z'
            track.up_axis = 'UP_Y'
            
        # Heuristic power scaling based on scene size
        # Power scales with area (distance squared)
        base_power = 50 * (max_dim**2)
        
        # Key Light (Front Right)
        create_light("Light_Key", 'AREA', (max_dim, -max_dim, max_dim*1.5), base_power, max_dim/2)
        
        # Fill Light (Front Left) - softer, less power
        create_light("Light_Fill", 'AREA', (-max_dim, -max_dim, max_dim*1.5), base_power * 0.5, max_dim)
        
        # Rim/Back Light (Rear) - for edge definition
        create_light("Light_Rim", 'AREA', (0, max_dim, max_dim*1.5), base_power * 0.8, max_dim/2)

        # 8. Render Settings
        print("Configuring Render Settings...")
        bpy.context.scene.render.resolution_x = 800
        bpy.context.scene.render.resolution_y = 600
        bpy.context.scene.render.resolution_percentage = 200

        # Set Render Engine to Cycles and device to GPU
        bpy.context.scene.render.engine = 'CYCLES'
        bpy.context.scene.cycles.device = 'GPU'

        # Configure World Background to BlenderKit HDRI
        office_hdri_ids = [
            "32e4b557-839b-4aeb-bfc6-4dfd79ec3604",
            "dc09a5ed-823e-4616-bc80-f34fc0cf66f2",
            "8d783162-dbac-4610-b8dd-41b032623ecd"
        ]
        apply_blenderkit_hdri(office_hdri_ids)
        
        # Enable Film Transparency for transparent background (RGBA)
        bpy.context.scene.render.film_transparent = True
        bpy.context.scene.render.image_settings.file_format = 'PNG'
        bpy.context.scene.render.image_settings.color_mode = 'RGBA'
        
        # Set Sampling (Viewport: 64, Render: 512, Denoise: On)
        bpy.context.scene.cycles.preview_samples = 64
        bpy.context.scene.cycles.samples = 512
        bpy.context.scene.cycles.use_denoising = True
        
        # Configure GPU device type in Blender user preferences
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

        # Configure Viewport Settings (Rendered Shading, Camera View, Orthographic)
        print("Configuring Viewport Settings (Rendered Shading, Camera View)...")
        try:
            if first_cam:
                bpy.context.scene.camera = first_cam
                
            for screen in bpy.data.screens:
                for area in screen.areas:
                    if area.type == 'VIEW_3D':
                        for space in area.spaces:
                            if space.type == 'VIEW_3D':
                                space.shading.type = 'RENDERED'
                                space.region_3d.view_perspective = 'CAMERA'
                                
            # Create autoplay script to force Rendered shading when opened in Blender GUI
            autoplay_script = bpy.data.texts.new(name="autoplay.py")
            autoplay_script.from_string('''import bpy
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'RENDERED'
                    space.region_3d.view_perspective = 'CAMERA'
''')
            autoplay_script.use_module = True
            print("Created autoplay.py to force Rendered viewport shading on load.")
        except Exception as viewport_err:
            print(f"Warning: Could not configure viewport settings: {{viewport_err}}")

    else:
        print("No mesh objects found to center.")

    # Apply "Shade Auto Smooth" to each mesh object in Object Mode
    print("Applying Shade Auto Smooth to all mesh objects...")
    try:
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
            
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                # Deselect all, then select the object and make it active
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                
                # Check if the object has a "green plastic" material
                is_green_plastic = False
                if obj.data.materials:
                    for mat in obj.data.materials:
                        if mat and "green" in mat.name.lower() and "plastic" in mat.name.lower():
                            is_green_plastic = True
                            break
                
                if is_green_plastic:
                    try:
                        bpy.ops.object.shade_flat()
                        print("Applied Shade Flat to", obj.name, "(green plastic)")
                    except Exception as flat_err:
                        print("Could not apply shade flat to", obj.name, ":", flat_err)
                else:
                    try:
                        # Blender 4.1+ (where shade_smooth_by_angle is available)
                        bpy.ops.object.shade_smooth_by_angle(angle=0.523599)
                    except AttributeError:
                        try:
                            # Blender 4.0 (where shade_auto_smooth is available)
                            bpy.ops.object.shade_auto_smooth()
                        except AttributeError:
                            try:
                                # Legacy approach for Blender 3.x and earlier
                                bpy.ops.object.shade_smooth()
                                obj.data.use_auto_smooth = True
                                obj.data.auto_smooth_angle = 0.523599 # 30 degrees in radians
                            except Exception as legacy_err:
                                print("Could not apply auto smooth to", obj.name, ":", legacy_err)
                        except Exception as err_4_0:
                            print("Could not apply auto smooth to", obj.name, ":", err_4_0)
                    except Exception as err:
                        print("Could not apply auto smooth to", obj.name, ":", err)
    except Exception as outer_err:
        print("Error during Auto Smooth application:", outer_err)

    # Save the file
    bpy.ops.wm.save_as_mainfile(filepath="{blend_file_path_str}", relative_remap=False)

if __name__ == "__main__":
    if bpy.app.background:
        run()
    else:
        # Defer execution to ensure the window manager and context are fully initialized in GUI mode
        bpy.app.timers.register(run, first_interval=0.5)
"""

    try:
        with open(import_script_path, "w", encoding="utf-8") as script_f:
            script_f.write(import_script_content)
    except Exception as e:
        print(f"Error creating import script: {e}")
        sys.exit(1)

    print(f"Created import script: {import_script_path}")
    
    # 6. Run Blender (GUI mode to allow BlenderKit daemon to run and download assets)
    cmd = [blender_exe, "-P", str(import_script_path)]
    
    try:
        print("Running Blender to import STLs...")
        subprocess.run(cmd, check=True)
        print("Blender import finished successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error running Blender: {e}")
        sys.exit(1)
    finally:
        if import_script_path.exists():
            import_script_path.unlink()

if __name__ == "__main__":
    main()
