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
    
    # Define helper to create/retrieve materials with proper properties
    def get_or_create_material(name, diffuse_color, metallic, roughness, specular=0.5, extra_setup_func=None):
        mat = bpy.data.materials.get(name)
        if not mat:
            mat = bpy.data.materials.new(name=name)
        mat.diffuse_color = diffuse_color + (1.0,) if len(diffuse_color) == 3 else diffuse_color
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

    hw_keywords = ["screw", "bolt", "key", "pin", "washer", "nut", "rivet", "나사", "볼트", "핀", "와셔", "너트", "리벳", "키"]
    bearing_keywords = ["bearing", "베어링"]
    
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            name_lower = obj.name.lower()
            assigned_mat = None
            
            # Rule 1: Brushed Nickel (Screws, Bolts, Keys, etc.)
            if any(hw in name_lower for hw in hw_keywords):
                assigned_mat = mat_brushed_nickel
                
            # Rule 2: Stainless Steel (Bearings)
            elif any(brg in name_lower for brg in bearing_keywords):
                assigned_mat = mat_stainless_steel
                
            # Rule 3: STATOR + COIL -> Copper
            elif "stator" in name_lower and "coil" in name_lower:
                assigned_mat = mat_copper
                
            # Rule 4: STATOR + CORE -> Carbon Steel
            elif "stator" in name_lower and "core" in name_lower:
                assigned_mat = mat_carbon_steel
                
            # Rule 5: STATOR + BOBBIN -> Green Plastic
            elif "stator" in name_lower and "bobbin" in name_lower:
                assigned_mat = mat_green_plastic
                
            # Rule 6: ROTOR + MAGNET -> Nickel
            elif "rotor" in name_lower and "magnet" in name_lower:
                assigned_mat = mat_nickel
                
            # Rule 7: Fallback -> Aluminium
            else:
                assigned_mat = mat_aluminium
                
            if assigned_mat:
                # Apply material
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                
                obj.data.materials.clear()
                obj.data.materials.append(assigned_mat)
                if hasattr(obj.data, "polygons"):
                    for poly in obj.data.polygons:
                        poly.material_index = 0
                print(f"Applied procedural {{assigned_mat.name}} to '{{obj.name}}'")

    # 4.6. Identify Outer/Housing Components for Pearl Black Plastic (OUTSIDE the STL import loop)
    print("Identifying outer housing components for Pearl Black Plastic...")
    mesh_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    
    # Filter out hardware and internal machine components from outer housing candidates
    candidate_objs = []
    hw_keywords = ["screw", "bolt", "key", "pin", "washer", "nut", "rivet", "bearing", "나사", "볼트", "핀", "와셔", "너트", "리벳", "키", "베어링"]
    for obj in mesh_objs:
        name_lower = obj.name.lower()
        # Filter out hardware
        if any(hw in name_lower for hw in hw_keywords):
            continue
        # Filter out motor internals
        if "stator" in name_lower and ("coil" in name_lower or "core" in name_lower or "bobbin" in name_lower):
            continue
        if "rotor" in name_lower and "magnet" in name_lower:
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
        
        # Apply Pearl Black Painted Plastic Material
        mat_name = "Mat_Pearl_Black_Plastic"
        mat = bpy.data.materials.get(mat_name)
        if not mat:
            mat = bpy.data.materials.new(name=mat_name)
            
        mat.diffuse_color = (0.1, 0.1, 0.1, 1.0)
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
            # Robust Active Selection and Assignment
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            
            obj.data.materials.clear()
            obj.data.materials.append(mat)
            if hasattr(obj.data, "polygons"):
                for poly in obj.data.polygons:
                    poly.material_index = 0
            print(f"Applied Pearl Black Painted Plastic to '{{obj.name}}'")

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
        
        # Use diagonal length for safer auto-fit (80% fill)
        # Ortho scale corresponds to the horizontal width of the view.
        # To be safe, we use the diagonal of the bounding box.
        diagonal = size_vec.length
        if diagonal == 0: diagonal = 10.0
        
        # 80% fill means object size is 0.8 of view size
        target_scale = diagonal / 0.8
        
        # Create Target Empty at Origin
        bpy.ops.object.empty_add(location=(0, 0, 0))
        target = bpy.context.active_object
        target.name = "Cam_Target"

        # Create 4 Isometric Cameras (Front-Right, Front-Left, Back-Right, Back-Left)
        camera_configs = [
            ("Camera_ISO_FR", (max_dim*2, -max_dim*2, max_dim*2)),
            ("Camera_ISO_FL", (-max_dim*2, -max_dim*2, max_dim*2)),
            ("Camera_ISO_BR", (max_dim*2, max_dim*2, max_dim*2)),
            ("Camera_ISO_BL", (-max_dim*2, max_dim*2, max_dim*2))
        ]
        
        first_cam = None
        for cam_name, cam_loc in camera_configs:
            bpy.ops.object.camera_add(location=cam_loc)
            cam_obj = bpy.context.active_object
            cam_obj.name = cam_name
            cam_obj.data.type = 'ORTHO'
            cam_obj.data.ortho_scale = target_scale
            
            # Add TrackTo Constraint to look at origin
            track_to = cam_obj.constraints.new(type='TRACK_TO')
            track_to.target = target
            track_to.track_axis = 'TRACK_NEGATIVE_Z'
            track_to.up_axis = 'UP_Y'
            
            print(f"Created Isometric Camera '{{cam_name}}' at {{cam_loc}}")
            if not first_cam:
                first_cam = cam_obj
                
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

        # Configure World Background to White Light
        world = bpy.data.worlds.new("World_White")
        bpy.context.scene.world = world
        if hasattr(world, 'use_nodes') and not world.use_nodes:
            try:
                world.use_nodes = True
            except:
                pass
        bg_node = world.node_tree.nodes.get("Background")
        if bg_node:
            bg_node.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
            bg_node.inputs['Strength'].default_value = 1.0
        
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

    else:
        print("No mesh objects found to center.")

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
        except Exception as viewport_err:
            print(f"Warning: Could not configure viewport settings: {{viewport_err}}")

    # Save the file
    bpy.ops.wm.save_as_mainfile(filepath="{blend_file_path_str}")

if __name__ == "__main__":
    run()
"""

    try:
        with open(import_script_path, "w", encoding="utf-8") as script_f:
            script_f.write(import_script_content)
    except Exception as e:
        print(f"Error creating import script: {e}")
        sys.exit(1)

    print(f"Created import script: {import_script_path}")
    
    # 6. Run Blender
    cmd = [blender_exe, "-b", "-P", str(import_script_path)]
    
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
