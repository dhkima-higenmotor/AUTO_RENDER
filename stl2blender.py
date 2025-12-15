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

def run():
    # Clear existing objects
    bpy.ops.wm.read_homefile(use_empty=True)
    
    input_dir = "{input_path_str}"
    
    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{{input_dir}}' not found inside Blender.")
        return

    # Get STL files and sort them alphabetically
    stl_files = sorted([f for f in os.listdir(input_dir) if f.lower().endswith('.stl')])
    
    print(f"Found {{len(stl_files)}} STL files to import.")
    
    import json

    for f in stl_files:
        filepath = os.path.join(input_dir, f)
        print(f"Importing: {{f}}")
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

        # Material Application
        # 1. Look for corresponding JSON
        json_filename = os.path.splitext(f)[0] + ".json"
        json_path = os.path.join(input_dir, json_filename)
        
        if os.path.exists(json_path):
            # print(f"  DEBUG: Found JSON: {{json_filename}}")
            try:
                with open(json_path, 'r', encoding='utf-8') as jf:
                    mat_data = json.load(jf)
                # print(f"  DEBUG: Loaded Data: {{mat_data}}")
                
                # 2. Extract properties
                color = mat_data.get("color", [0.8, 0.8, 0.8])
                specular = mat_data.get("specular", 0.5)
                shininess = mat_data.get("shininess", 0.5)
                transparency = mat_data.get("transparency", 0.0)
                emission = mat_data.get("emission", 0.0)
                
                # 3. Create Material
                mat_name = f"Mat_{{os.path.splitext(f)[0]}}"
                mat = bpy.data.materials.new(name=mat_name)
                mat.use_nodes = True
                
                # Set Viewport Display Color (Important for Solid View)
                if len(color) == 3:
                     mat.diffuse_color = color + [1.0]
                elif len(color) == 4:
                     mat.diffuse_color = color
                
                # Get Principled BSDF
                bsdf = mat.node_tree.nodes.get("Principled BSDF")
                if not bsdf:
                    # Fallback: Find by type
                    for node in mat.node_tree.nodes:
                        if node.type == 'BSDF_PRINCIPLED':
                            bsdf = node
                            break
                            
                if bsdf:
                    # 1. Base Color
                    # Ensure color is a list of 3 floats
                    if len(color) == 3:
                        bsdf.inputs['Base Color'].default_value = color + [1.0] # Add Alpha=1.0 for Base Color
                    
                    # 2. Roughness
                    # Shininess (0.0-1.0) -> Roughness (1.0-0.0)
                    bsdf.inputs['Roughness'].default_value = 1.0 - shininess
                    
                    # 3. Specular
                    # Map to 'Specular IOR Level' (Blender 4.0+) or 'Specular' (Legacy)
                    if 'Specular IOR Level' in bsdf.inputs:
                        bsdf.inputs['Specular IOR Level'].default_value = specular
                    elif 'Specular' in bsdf.inputs:
                        bsdf.inputs['Specular'].default_value = specular
                        
                    # 4. Metric / Metallic
                    # Not present in SW JSON usually, default to 0.0 (Dielectric) unless implied?
                    # We leave it as default (0.0) for now.

                    # 5. Emission
                    if emission > 0:
                        # Use same color for emission, intensity from emission value
                        bsdf.inputs['Emission Color'].default_value = color + [1.0]
                        bsdf.inputs['Emission Strength'].default_value = emission
                    
                    # 6. Transparency / Transmission
                    if transparency > 0:
                        # Transmission Weight (Blender 4.0+)
                        if 'Transmission Weight' in bsdf.inputs:
                            bsdf.inputs['Transmission Weight'].default_value = transparency
                        elif 'Transmission' in bsdf.inputs:
                            bsdf.inputs['Transmission'].default_value = transparency
                        
                        # Alpha (for Eevee/Transparent BSDF mixing if needed, but Principled handles transmission)
                        # Reducing Alpha often makes it vanish in Eevee unless Blend Mode is set.
                        bsdf.inputs['Alpha'].default_value = 1.0 - transparency
                        
                        # Enable transparency for Eevee/Viewport
                        mat.blend_method = 'HASHED' # Or 'BLEND'
                        mat.shadow_method = 'HASHED'

                # 4. Assign Material to imported object(s)
                for obj in bpy.context.selected_objects:
                    if obj.type == 'MESH':
                        obj.data.materials.clear()
                        obj.data.materials.append(mat)
                        
                print(f"Applied material from {{json_filename}}")

            except Exception as e:
                print(f"Failed to apply material from {{json_filename}}: {{e}}")
        else:
            # print(f"  DEBUG: JSON NOT found: {{json_path}}")
            print(f"No material JSON found for {{f}}")

    # Center all objects
    # Calculate the bounding box of all objects
    import mathutils
    
    # Select all mesh objects
    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    
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
        
        # Apply Auto Smooth (Smooth by Angle) to all meshes
        print("Applying Auto Smooth...")
        bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH':
                obj.select_set(True)
        # shade_smooth_by_angle is available in newer Blender versions (4.1+)
        if hasattr(bpy.ops.object, 'shade_smooth_by_angle'):
             bpy.ops.object.shade_smooth_by_angle()
        else:
             # Fallback for older versions if needed (though user is on 5.0)
             bpy.ops.object.shade_smooth()
             for obj in bpy.context.selected_objects:
                 obj.data.use_auto_smooth = True
        
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
        
        # Create Camera
        bpy.ops.object.camera_add(location=(max_dim*2, -max_dim*2, max_dim*2))
        cam_obj = bpy.context.active_object
        cam_obj.name = "Camera_ISO"
        cam_obj.data.type = 'ORTHO'
        cam_obj.data.ortho_scale = target_scale
        
        # Set as active camera
        bpy.context.scene.camera = cam_obj
        
        # Create Target Empty at Origin
        bpy.ops.object.empty_add(location=(0, 0, 0))
        target = bpy.context.active_object
        target.name = "Cam_Target"
        
        # Add TrackTo Constraint
        track_to = cam_obj.constraints.new(type='TRACK_TO')
        track_to.target = target
        track_to.track_axis = 'TRACK_NEGATIVE_Z'
        track_to.up_axis = 'UP_Y'
        
        print(f"Created Isometric Camera with scale {{cam_obj.data.ortho_scale}}")

        # Create Opposite Camera
        bpy.ops.object.camera_add(location=(-max_dim*2, max_dim*2, max_dim*2))
        cam_opp = bpy.context.active_object
        cam_opp.name = "Camera_ISO_Opposite"
        cam_opp.data.type = 'ORTHO'
        cam_opp.data.ortho_scale = target_scale
        
        # Add TrackTo Constraint
        track_to_opp = cam_opp.constraints.new(type='TRACK_TO')
        track_to_opp.target = target
        track_to_opp.track_axis = 'TRACK_NEGATIVE_Z'
        track_to_opp.up_axis = 'UP_Y'
        
        print(f"Created Opposite Isometric Camera")

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
        bpy.context.scene.render.resolution_percentage = 100

    else:
        print("No mesh objects found to center.")

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
