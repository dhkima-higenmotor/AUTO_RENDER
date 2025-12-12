import bpy
import math
import os
import mathutils
from collections import defaultdict
import bmesh

def create_light(name, type, location, target, energy, size=1.0):
    light_data = bpy.data.lights.new(name=name, type=type)
    light_data.energy = energy
    if type == 'AREA':
        light_data.shape = 'RECTANGLE'
        light_data.size = size
        light_data.size_y = size

    light_obj = bpy.data.objects.new(name=name, object_data=light_data)
    bpy.context.collection.objects.link(light_obj)
    light_obj.location = location
    direction = target - light_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    light_obj.rotation_euler = rot_quat.to_euler()
    return light_obj

def setup_lighting(scene, center, size_magnitude):
    print("Setting up lighting...")
    dist = size_magnitude * 3.0 # Move lights further out
    height = size_magnitude * 2.0
    
    # Smaller lights = Sharper highlights, less "white wash" on black metal
    light_size = size_magnitude * 0.2 
    
    # Reduced intensity for Cycles (Too bright previously)
    # Energy is in Watts. For small objects, low values are needed.
    # Key: 50W, Fill: 25W, Rim: 75W (Approx 1/4 of previous)
    
    key_loc = center + mathutils.Vector((-dist * 0.7, -dist * 0.7, height))
    create_light("Key_Light", 'AREA', key_loc, center, energy=50.0, size=light_size)
    
    fill_loc = center + mathutils.Vector((dist * 0.7, -dist * 0.5, height * 0.5))
    create_light("Fill_Light", 'AREA', fill_loc, center, energy=25.0, size=light_size)
    
    rim_loc = center + mathutils.Vector((0, dist, height * 0.8))
    create_light("Rim_Light", 'AREA', rim_loc, center, energy=75.0, size=light_size)
    
    # Set World Background to Dark to prevent ambient washout
    if scene.world and scene.world.use_nodes:
        bg_node = scene.world.node_tree.nodes.get("Background")
        if bg_node:
            bg_node.inputs["Color"].default_value = (0.01, 0.01, 0.01, 1) # Very dark grey
            bg_node.inputs["Strength"].default_value = 1.0
    
    print("Lighting setup complete.")

def get_combined_bound_box(objects):
    min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
    max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')
    has_obj = False
    for obj in objects:
        has_obj = True
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ mathutils.Vector(corner)
            min_x = min(min_x, world_corner.x)
            min_y = min(min_y, world_corner.y)
            min_z = min(min_z, world_corner.z)
            max_x = max(max_x, world_corner.x)
            max_y = max(max_y, world_corner.y)
            max_z = max(max_z, world_corner.z)
            
    if not has_obj: return None, None
    center = mathutils.Vector(((min_x + max_x) / 2, (min_y + max_y) / 2, (min_z + max_z) / 2))
    size = mathutils.Vector((max_x - min_x, max_y - min_y, max_z - min_z))
    return center, size

def setup_camera_view(scene, camera, target_objects):
    print("Setting up camera...")
    scene.camera = camera
    center, size_vec = get_combined_bound_box(target_objects)
    if center is None: return

    direction = mathutils.Vector((1, -1, 1)).normalized()
    distance = 10.0 
    camera.location = center + direction * distance
    
    direction_to_center = center - camera.location
    rot_quat = direction_to_center.to_track_quat('-Z', 'Y')
    camera.rotation_euler = rot_quat.to_euler()
    
    bpy.context.view_layer.update()
    
    min_x_cam, min_y_cam = float('inf'), float('inf')
    max_x_cam, max_y_cam = float('-inf'), float('-inf')
    w_to_c = camera.matrix_world.inverted()
    
    for obj in target_objects:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ mathutils.Vector(corner)
            cam_corner = w_to_c @ world_corner
            
            min_x_cam = min(min_x_cam, cam_corner.x)
            min_y_cam = min(min_y_cam, cam_corner.y)
            max_x_cam = max(max_x_cam, cam_corner.x)
            max_y_cam = max(max_y_cam, cam_corner.y)
            
    req_width = max_x_cam - min_x_cam
    req_height = max_y_cam - min_y_cam
    render = scene.render
    aspect_ratio = render.resolution_x / render.resolution_y
    margin = 1.1 
    final_scale = max(req_width, req_height * aspect_ratio) * margin
    camera.data.ortho_scale = final_scale
    print(f"Calculated Ortho Scale: {final_scale}")

def setup_camera(scene, name, direction_vec, target_objects):
    print(f"Setting up camera: {name}...")
    cam_data = bpy.data.cameras.new(name=name)
    cam_obj = bpy.data.objects.new(name=name, object_data=cam_data)
    scene.collection.objects.link(cam_obj)
    
    cam_data.type = 'ORTHO'
    cam_data.lens = 50
    
    center, size_vec = get_combined_bound_box(target_objects)
    if center is None: return

    direction = direction_vec.normalized()
    distance = 10.0 
    cam_obj.location = center + direction * distance
    
    direction_to_center = center - cam_obj.location
    rot_quat = direction_to_center.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()
    
    bpy.context.view_layer.update()
    
    min_x_cam, min_y_cam = float('inf'), float('inf')
    max_x_cam, max_y_cam = float('-inf'), float('-inf')
    w_to_c = cam_obj.matrix_world.inverted()
    
    for obj in target_objects:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ mathutils.Vector(corner)
            cam_corner = w_to_c @ world_corner
            min_x_cam = min(min_x_cam, cam_corner.x)
            min_y_cam = min(min_y_cam, cam_corner.y)
            max_x_cam = max(max_x_cam, cam_corner.x)
            max_y_cam = max(max_y_cam, cam_corner.y)
            
    req_width = max_x_cam - min_x_cam
    req_height = max_y_cam - min_y_cam
    render = scene.render
    aspect_ratio = render.resolution_x / render.resolution_y
    margin = 1.1 
    final_scale = max(req_width, req_height * aspect_ratio) * margin
    cam_data.ortho_scale = final_scale
    print(f"  {name} Scale: {final_scale:.3f}")
    return cam_obj

def get_mesh_volume(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    try:
        vol = bm.calc_volume()
    except:
        vol = 0.0
    bm.free()
    return vol

def join_similar_parts(objects):
    groups = defaultdict(list)
    print("Analyzing parts for grouping...")
    for obj in objects:
        if obj.type != 'MESH': continue
        mesh = obj.data
        v_count = len(mesh.vertices)
        p_count = len(mesh.polygons)
        vol = get_mesh_volume(mesh)
        key = (v_count, p_count, f"{vol:.6f}")
        groups[key].append(obj)
        
    print(f"Found {len(groups)} unique shapes out of {len(objects)} parts.")
    
    joined_objects = []
    bpy.ops.object.select_all(action='DESELECT')
    sorted_groups = sorted(groups.items(), key=lambda item: len(item[1]), reverse=True)
    
    group_counter = 1
    for key, group_objs in sorted_groups:
        if not group_objs: continue
        
        valid_objs = [o for o in group_objs if o.name in bpy.data.objects]
        if not valid_objs: continue
        
        for obj in valid_objs:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = valid_objs[0]
        
        if len(valid_objs) > 1:
            try:
                bpy.ops.object.join()
            except: pass
        
        final_obj = bpy.context.view_layer.objects.active
        
        if len(valid_objs) > 1:
            final_obj.name = f"Joined_Part_{group_counter}_x{len(valid_objs)}"
        else:
            final_obj.name = f"Part_{group_counter}"
            
        joined_objects.append(final_obj)
        bpy.ops.object.select_all(action='DESELECT')
        group_counter += 1
        
    return joined_objects

def create_nodes(material, color, metallic, roughness, anisotropic=0.0):
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (300, 0)
    
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    # Anisotropic helps black metal catch light in Cycles
    bsdf.inputs["Anisotropic"].default_value = anisotropic
    if anisotropic > 0:
        bsdf.inputs["Anisotropic Rotation"].default_value = 0.0
    
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

def apply_materials(objects):
    print("Creating materials...")
    
    # Nickel: Slightly cleaner
    mat_nickel = bpy.data.materials.new(name="Nickel_Plated")
    create_nodes(mat_nickel, (0.7, 0.7, 0.65, 1), 1.0, 0.2)
    
    # Black Anodized: Tuned for Contrast
    # Lower roughness (0.4) -> Sharper reflections, deeper black body behavior
    mat_black = bpy.data.materials.new(name="Black_Anodized")
    create_nodes(mat_black, (0.01, 0.01, 0.01, 1), 1.0, 0.4, anisotropic=0.0)
    
    print("Applying materials...")
    count_nickel = 0
    count_black = 0
    
    for obj in objects:
        if obj.type != 'MESH': continue
        if not obj.data.materials: obj.data.materials.append(None)
        
        if obj.name.startswith("Joined_Part"):
            obj.data.materials[0] = mat_nickel
            count_nickel += 1
        else:
            obj.data.materials[0] = mat_black
            count_black += 1
            
    print(f"Material Application: Nickel={count_nickel}, Black={count_black}")

def main():
    print("Starting Blender processing...")
    
    # Ensure Cycles Engine
    bpy.context.scene.render.engine = 'CYCLES'
    
    # Try using GPU just in case
    try:
        cycles_prefs = bpy.context.preferences.addons['cycles'].preferences
        cycles_prefs.compute_device_type = 'CUDA' # or 'OPTIX'
        
        # In script, setting scene.cycles.device is what matters mostly
        bpy.context.scene.cycles.device = 'GPU'
    except:
        bpy.context.scene.cycles.device = 'CPU'

    try:
        import addon_utils
        addon_utils.enable("io_mesh_stl")
    except: pass

    # Clean
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_by_type(type='MESH')
    bpy.ops.object.delete()
    bpy.ops.object.select_by_type(type='CAMERA')
    bpy.ops.object.delete()
    bpy.ops.object.select_by_type(type='LIGHT')
    bpy.ops.object.delete()
    
    for m in bpy.data.materials: bpy.data.materials.remove(m)

    import sys
    import argparse
    
    # Parse arguments after "--"
    argv = []
    if "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1:]
    
    parser = argparse.ArgumentParser(description="Blender Automation Script")
    parser.add_argument("stl_file", nargs="?", default="AA200_ASSY.STL", help="Path to STL file")
    parser.add_argument("--res", choices=["low", "mid", "high"], default="mid", help="Render Resolution")
    
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        # Blender might intercept help, but let's be safe
        return
        
    stl_file = args.stl_file
    resolution = args.res
    
    print(f"Target STL File: {stl_file}")
    print(f"Resolution Mode: {resolution}")
    
    if not os.path.exists(stl_file):
        print(f"Error: File not found: {stl_file}")
        # Only return if we really can't find it. 
        # Sometimes absolute paths need care.
        return

    # Set Resolution Variables
    res_map = {
        "low": (800, 600),
        "mid": (1024, 768),
        "high": (2048, 1536)
    }
    width, height = res_map[resolution]
        
    try:
        if hasattr(bpy.ops.wm, 'stl_import'):
            bpy.ops.wm.stl_import(filepath=stl_file)
        elif hasattr(bpy.ops.import_mesh, 'stl'):
            bpy.ops.import_mesh.stl(filepath=stl_file)
    except: return

    imported_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    if not imported_objects: return

    # 1. Transform
    bpy.context.view_layer.objects.active = imported_objects[0]
    for obj in imported_objects:
        obj.select_set(True)
        obj.scale = (0.001, 0.001, 0.001)
        obj.rotation_euler[0] = math.radians(-90)
    try:
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    except: pass

    # 2. Separate
    print("Separating loose parts...")
    bpy.ops.object.select_all(action='DESELECT')
    for obj in imported_objects:
        obj.select_set(True)
    try:
        bpy.context.view_layer.objects.active = imported_objects[0]
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type='LOOSE')
        bpy.ops.object.mode_set(mode='OBJECT')
    except:
        bpy.ops.object.mode_set(mode='OBJECT')

    # 3. Join & Name
    loose_parts = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    final_objects = join_similar_parts(loose_parts)

    # 4. Center
    center, size = get_combined_bound_box(final_objects)
    if center:
        for obj in final_objects:
            obj.location -= center
    bpy.context.view_layer.update()
    
    # 5. Origin
    bpy.ops.object.select_all(action='DESELECT')
    for obj in final_objects:
        obj.select_set(True)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')

    # Assign Materials
    apply_materials(final_objects)

    # Smoothing
    print("Applying Smooth Shading...")
    for obj in final_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = final_objects[0]
    
    # Use Shade Smooth by Angle (Standard for CAD/Hard Surface in modern Blender)
    if hasattr(bpy.ops.object, 'shade_smooth_by_angle'):
        try:
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30))
        except Exception as e:
            print(f"Smooth by angle failed: {e}")
            # Fallback
            bpy.ops.object.shade_smooth()
    else:
        # Fallback for older versions (though user has 5.0)
        bpy.ops.object.shade_smooth()
        # Enable Auto Smooth property if it exists (Mesh data level)
        for obj in final_objects:
            if hasattr(obj.data, 'use_auto_smooth'):
                obj.data.use_auto_smooth = True

    # Lighting
    center_final, size_final = get_combined_bound_box(final_objects)
    if size_final:
        max_dim = max(size_final.x, size_final.y, size_final.z)
        if max_dim < 0.01: max_dim = 0.1 
        setup_lighting(bpy.context.scene, center_final, max_dim)
    
    # Camera 1: Original (Front-Right-Top)
    # Vec (1, -1, 1)
    cam1 = setup_camera(bpy.context.scene, "Camera_Front", mathutils.Vector((1, -1, 1)), final_objects)
    
    # Camera 2: Opposite Side (Back-Left-Top)
    # Vec (-1, 1, 1)
    cam2 = setup_camera(bpy.context.scene, "Camera_Back", mathutils.Vector((-1, 1, 1)), final_objects)
    
    # Set active camera to Camera_Front
    bpy.context.scene.camera = cam1
    bpy.context.scene.render.resolution_x = width
    bpy.context.scene.render.resolution_y = height
    
    # Rendering
    print("Starting Batch Rendering...")
    
    # Target Directory: Same as STL file
    output_dir = os.path.dirname(os.path.abspath(stl_file))
    stl_basename = os.path.splitext(os.path.basename(stl_file))[0]
    print(f"Output Directory: {output_dir}")
    print(f"File Prefix: {stl_basename}")
    
    render_cameras = [cam1, cam2]
    
    for cam in render_cameras:
        bpy.context.scene.camera = cam
        
        # 1. Normal Render (Opaque Background)
        bpy.context.scene.render.film_transparent = False
        output_filename = f"{stl_basename}_{cam.name}.png"
        output_path = os.path.join(output_dir, output_filename)
        
        bpy.context.scene.render.filepath = output_path
        print(f"  Rendering {cam.name} (Opaque)...")
        try:
            bpy.ops.render.render(write_still=True)
            print(f"  Saved to: {output_path}")
        except Exception as e:
            print(f"  Render failed for {cam.name}: {e}")
            
        # 2. Transparent Render
        bpy.context.scene.render.film_transparent = True
        output_filename_trans = f"{stl_basename}_{cam.name}_transparent.png"
        output_path_trans = os.path.join(output_dir, output_filename_trans)
        
        bpy.context.scene.render.filepath = output_path_trans
        print(f"  Rendering {cam.name} (Transparent)...")
        try:
            bpy.ops.render.render(write_still=True)
            print(f"  Saved to: {output_path_trans}")
        except Exception as e:
            print(f"  Transparent render failed for {cam.name}: {e}")

    print("Done.")

if __name__ == "__main__":
    main()
