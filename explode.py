import bpy
import mathutils
from bpy_extras.object_utils import world_to_camera_view

def get_sorting_key(obj, axis_idx=1):
    """
    Determines the sorting key based on the bounding box position.
    If the max coordinate along the selected axis is negative, it returns the minimum coordinate.
    Otherwise, it returns the maximum coordinate.
    """
    matrix_world = obj.matrix_world
    world_coords = [(matrix_world @ mathutils.Vector(corner))[axis_idx] for corner in obj.bound_box]
    
    max_coord = max(world_coords)
    min_coord = min(world_coords)
    
    # If the entire part is in the negative region, use the minimum coordinate as the sorting baseline
    if max_coord < 0:
        return min_coord
    return max_coord

def get_max_coord(obj, axis_idx=1):
    """
    Returns the maximum bounding box coordinate of the object along the selected axis.
    """
    matrix_world = obj.matrix_world
    world_coords = [(matrix_world @ mathutils.Vector(corner))[axis_idx] for corner in obj.bound_box]
    return max(world_coords)

def get_min_coord(obj, axis_idx=1):
    """
    Returns the minimum bounding box coordinate of the object along the selected axis.
    """
    matrix_world = obj.matrix_world
    world_coords = [(matrix_world @ mathutils.Vector(corner))[axis_idx] for corner in obj.bound_box]
    return min(world_coords)

def o_center(obj, axis_idx):
    """
    Returns the center of the bounding box of the object along the selected axis.
    """
    matrix_world = obj.matrix_world
    world_coords = [(matrix_world @ mathutils.Vector(corner))[axis_idx] for corner in obj.bound_box]
    return (min(world_coords) + max(world_coords)) / 2.0

def is_outside_camera(obj, camera, scene):
    """
    Checks if the bounding box of the object is completely outside the camera's viewport.
    """
    matrix_world = obj.matrix_world
    corners = [matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    
    projected = []
    for corner in corners:
        co_ndc = world_to_camera_view(scene, camera, corner)
        projected.append(co_ndc)
        
    # Check if they are all on one side of the camera view:
    # 1. Behind the camera (z < 0)
    # 2. To the left of the screen (x < 0)
    # 3. To the right of the screen (x > 1)
    # 4. Below the screen (y < 0)
    # 5. Above the screen (y > 1)
    if all(p.z < 0 for p in projected):
        return True
    if all(p.x < 0.0 for p in projected):
        return True
    if all(p.x > 1.0 for p in projected):
        return True
    if all(p.y < 0.0 for p in projected):
        return True
    if all(p.y > 1.0 for p in projected):
        return True
        
    return False

def find_clearance_displacement(obj, axis_idx, direction, camera, scene, assembly_scale):
    """
    Finds the minimum displacement required to push the object completely outside the camera viewport.
    """
    if not camera:
        return assembly_scale * 3.0
        
    d = 0.0
    step = assembly_scale * 0.1
    orig_loc = obj.location.copy()
    
    for _ in range(500):
        obj.location[axis_idx] = orig_loc[axis_idx] + direction * d
        bpy.context.view_layer.update()
        if is_outside_camera(obj, camera, scene):
            # Restore original location
            obj.location = orig_loc
            bpy.context.view_layer.update()
            return d
        d += step
        
    # Fallback to a large displacement if it cannot clear
    obj.location = orig_loc
    bpy.context.view_layer.update()
    return assembly_scale * 5.0

def create_adaptive_bbox_explosion(axis='Y', direction_mode='BOTH', factor=5.0, total_seconds=20.0):
    """
    axis: Axis along which the explosion happens ('X', 'Y', or 'Z')
    direction_mode: Direction of explosion ('POS', 'NEG', or 'BOTH')
    factor: Explosion distance multiplier (retained for signature compatibility)
    total_seconds: Total animation duration in seconds (Default: 20.0s)
    """
    axis_map = {'X': 0, 'Y': 1, 'Z': 2}
    axis_idx = axis_map.get(axis.upper(), 1)  # Default is Y (1)
    
    # 1. Gather all mesh objects in the scene
    all_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    
    num_parts = len(all_objects)
    if num_parts == 0:
        print("No mesh objects found in the scene.")
        return

    # Clear existing animation data to prevent conflicts
    for obj in all_objects:
        if obj.animation_data:
            obj.animation_data_clear()

    # 2. Calculate global scale of the assembly
    min_corner = mathutils.Vector((float('inf'), float('inf'), float('inf')))
    max_corner = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))
    for obj in all_objects:
        matrix_world = obj.matrix_world
        for corner in obj.bound_box:
            world_corner = matrix_world @ mathutils.Vector(corner)
            min_corner.x = min(min_corner.x, world_corner.x)
            min_corner.y = min(min_corner.y, world_corner.y)
            min_corner.z = min(min_corner.z, world_corner.z)
            max_corner.x = max(max_corner.x, world_corner.x)
            max_corner.y = max(max_corner.y, world_corner.y)
            max_corner.z = max(max_corner.z, world_corner.z)
            
    size_vec = max_corner - min_corner
    assembly_scale = max(size_vec.x, size_vec.y, size_vec.z)
    if assembly_scale <= 0.0:
        assembly_scale = 1.0

    # 3. Calculate the global average center to determine the explosion direction
    total_val = sum(o_center(obj, axis_idx) for obj in all_objects)
    global_center_val = total_val / num_parts

    # Get active camera and scene
    camera = bpy.context.scene.camera
    if not camera:
        cameras = [obj for obj in bpy.context.scene.objects if obj.type == 'CAMERA']
        if cameras:
            camera = cameras[0]

    # 4. Pre-calculate displacements, directions, and animation delay order based on direction_mode
    displacements = {}
    directions = {}
    direction_mode = direction_mode.upper()
    
    # Establish a visual spacing gap proportional to the assembly scale to keep parts distinct
    base_gap = max(0.2 * assembly_scale, 0.5)
    
    if direction_mode == 'POS':
        # Sort objects by original center along the axis ascending (left to right)
        objs_sorted_by_pos = sorted(
            all_objects,
            key=lambda o: o_center(o, axis_idx)
        )
        
        # Innermost is the first element (moves least in POS direction). Get its clearance displacement.
        d0 = find_clearance_displacement(objs_sorted_by_pos[0], axis_idx, 1.0, camera, bpy.context.scene, assembly_scale)
        displacements[objs_sorted_by_pos[0]] = d0
        directions[objs_sorted_by_pos[0]] = 1.0
        
        # Distribute subsequent displacements outwards maintaining order and gap
        for i in range(1, len(objs_sorted_by_pos)):
            obj = objs_sorted_by_pos[i]
            prev_obj = objs_sorted_by_pos[i-1]
            
            prev_max = get_max_coord(prev_obj, axis_idx)
            curr_min = get_min_coord(obj, axis_idx)
            
            # Adaptive gap based on bounding box dimensions of adjacent parts
            size_prev = prev_max - get_min_coord(prev_obj, axis_idx)
            size_curr = get_max_coord(obj, axis_idx) - curr_min
            gap = max(base_gap, 0.15 * (size_prev + size_curr))
            
            d_prev = displacements[prev_obj]
            d_curr = max(d_prev, d_prev + (prev_max - curr_min) + gap)
            displacements[obj] = d_curr
            directions[obj] = 1.0
            
        # Delay order: outermost first (highest max coordinate starts first)
        sorted_objects = sorted(
            all_objects,
            key=lambda o: get_max_coord(o, axis_idx),
            reverse=True
        )
        
    elif direction_mode == 'NEG':
        # Sort objects by original center along the axis ascending (left to right)
        objs_sorted_by_pos = sorted(
            all_objects,
            key=lambda o: o_center(o, axis_idx)
        )
        
        n = len(objs_sorted_by_pos)
        # Innermost is the last element (moves least in NEG direction). Get its clearance displacement.
        dn = find_clearance_displacement(objs_sorted_by_pos[-1], axis_idx, -1.0, camera, bpy.context.scene, assembly_scale)
        displacements[objs_sorted_by_pos[-1]] = dn
        directions[objs_sorted_by_pos[-1]] = -1.0
        
        # Distribute subsequent displacements outwards (moving right to left)
        for i in range(n - 2, -1, -1):
            obj = objs_sorted_by_pos[i]
            next_obj = objs_sorted_by_pos[i+1]
            
            curr_max = get_max_coord(obj, axis_idx)
            next_min = get_min_coord(next_obj, axis_idx)
            
            # Adaptive gap based on bounding box dimensions of adjacent parts
            size_curr = curr_max - get_min_coord(obj, axis_idx)
            size_next = get_max_coord(next_obj, axis_idx) - next_min
            gap = max(base_gap, 0.15 * (size_curr + size_next))
            
            d_next = displacements[next_obj]
            d_curr = max(d_next, d_next + (curr_max - next_min) + gap)
            displacements[obj] = d_curr
            directions[obj] = -1.0
            
        # Delay order: outermost first in negative (lowest min coordinate starts first)
        sorted_objects = sorted(
            all_objects,
            key=lambda o: get_min_coord(o, axis_idx),
            reverse=False
        )
        
    else:  # BOTH (bidirectional) mode
        pos_group = [obj for obj in all_objects if o_center(obj, axis_idx) >= global_center_val]
        neg_group = [obj for obj in all_objects if o_center(obj, axis_idx) < global_center_val]
        
        # Calculate positive side displacements (outward from center)
        if pos_group:
            pos_sorted = sorted(pos_group, key=lambda o: o_center(o, axis_idx))
            # Innermost of positive group is pos_sorted[0]
            d0 = find_clearance_displacement(pos_sorted[0], axis_idx, 1.0, camera, bpy.context.scene, assembly_scale)
            displacements[pos_sorted[0]] = d0
            directions[pos_sorted[0]] = 1.0
            
            for i in range(1, len(pos_sorted)):
                obj = pos_sorted[i]
                prev_obj = pos_sorted[i-1]
                prev_max = get_max_coord(prev_obj, axis_idx)
                curr_min = get_min_coord(obj, axis_idx)
                
                # Adaptive gap based on bounding box dimensions of adjacent parts
                size_prev = prev_max - get_min_coord(prev_obj, axis_idx)
                size_curr = get_max_coord(obj, axis_idx) - curr_min
                gap = max(base_gap, 0.15 * (size_prev + size_curr))
                
                d_prev = displacements[prev_obj]
                d_curr = max(d_prev, d_prev + (prev_max - curr_min) + gap)
                displacements[obj] = d_curr
                directions[obj] = 1.0
                
        # Calculate negative side displacements (outward from center)
        if neg_group:
            neg_sorted = sorted(neg_group, key=lambda o: o_center(o, axis_idx))
            # Innermost of negative group is neg_sorted[-1]
            n_neg = len(neg_sorted)
            dn = find_clearance_displacement(neg_sorted[-1], axis_idx, -1.0, camera, bpy.context.scene, assembly_scale)
            displacements[neg_sorted[-1]] = dn
            directions[neg_sorted[-1]] = -1.0
            
            for i in range(n_neg - 2, -1, -1):
                obj = neg_sorted[i]
                next_obj = neg_sorted[i+1]
                curr_max = get_max_coord(obj, axis_idx)
                next_min = get_min_coord(next_obj, axis_idx)
                
                # Adaptive gap based on bounding box dimensions of adjacent parts
                size_curr = curr_max - get_min_coord(obj, axis_idx)
                size_next = get_max_coord(next_obj, axis_idx) - next_min
                gap = max(base_gap, 0.15 * (size_curr + size_next))
                
                d_next = displacements[next_obj]
                d_curr = max(d_next, d_next + (curr_max - next_min) + gap)
                displacements[obj] = d_curr
                directions[obj] = -1.0
                
        # Delay order: furthest from center starts first to prevent collisions
        sorted_objects = sorted(
            all_objects, 
            key=lambda o: abs(o_center(o, axis_idx) - global_center_val), 
            reverse=True
        )

    # 6. Calculate equal frame distribution based on a fixed total duration
    fps = bpy.context.scene.render.fps  
    total_frames = int(total_seconds * fps)
    
    # Timeline split: 60% for sequential delays, 40% for individual movement duration
    if num_parts > 1:
        delay_offset = (total_frames * 0.6) / (num_parts - 1)
        duration = total_frames * 0.4
    else:
        delay_offset = 0
        duration = total_frames

    scene = bpy.context.scene
    current_delay = 0.0  

    # 7. Generate keyframes for sorted objects sequentially
    for obj in sorted_objects:
        # Determine explosion direction along the chosen axis
        direction = directions.get(obj, 1.0)

        # Convert frame values to integers for inserting keyframes
        start_frame = int(1 + current_delay)
        
        # Lock initial assembly position at frame 1
        scene.frame_set(1)
        obj.keyframe_insert(data_path="location", index=axis_idx)
        
        # Keep the object stationary until its specific start frame arrives
        scene.frame_set(start_frame)
        obj.keyframe_insert(data_path="location", index=axis_idx)
        
        # Smoothly move to the exploded position over the calculated duration
        end_frame = int(start_frame + duration)
        scene.frame_set(end_frame)
        
        # Apply displacement along the selected axis
        displacement = displacements.get(obj, 0.0)
        obj.location[axis_idx] += direction * displacement
        obj.keyframe_insert(data_path="location", index=axis_idx)
        
        # Accumulate delay for the next subsequent part
        current_delay += delay_offset
        
    # Reset timeline to frame 1 and update the scene's end frame range
    scene.frame_set(1)
    scene.frame_end = total_frames
    
    print(f"--- Adaptive Bounding Box Explosion Configuration Complete ---")
    print(f"Axis: {axis.upper()} | Total Parts: {num_parts} | Total Time: {total_seconds}s ({total_frames} frames)")
    print(f"Movement Duration: {int(duration)}f | Delay Offset: {delay_offset:.2f}f")

# Execute the script
import os
explode_axis = os.environ.get("EXPLODE_AXIS", "Y")
explode_dir_mode = os.environ.get("EXPLODE_DIR_MODE", "BOTH")
try:
    explode_duration = float(os.environ.get("EXPLODE_DURATION", "20.0"))
except ValueError:
    explode_duration = 20.0
create_adaptive_bbox_explosion(
    axis=explode_axis, 
    direction_mode=explode_dir_mode, 
    factor=5.0, 
    total_seconds=explode_duration
)