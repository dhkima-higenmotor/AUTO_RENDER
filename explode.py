import bpy
import mathutils

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

def create_adaptive_bbox_explosion(axis='Y', direction_mode='BOTH', factor=5.0, total_seconds=20.0):
    """
    axis: Axis along which the explosion happens ('X', 'Y', or 'Z')
    direction_mode: Direction of explosion ('POS', 'NEG', or 'BOTH')
    factor: Explosion distance multiplier
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
    total_val = sum(obj.location[axis_idx] for obj in all_objects)
    global_center_val = total_val / num_parts

    # 4. Pre-calculate displacements, directions, and animation delay order based on direction_mode
    # Even the innermost components must move completely off-screen (min_disp = 3.0 * assembly_scale).
    min_disp = assembly_scale * 3.0
    max_disp = max(assembly_scale * factor, min_disp + assembly_scale)
    displacements = {}
    directions = {}
    direction_mode = direction_mode.upper()
    
    if direction_mode == 'POS':
        # Unidirectional Positive: All components move positive, sorted lowest to highest coord
        all_sorted = sorted(all_objects, key=lambda o: get_sorting_key(o, axis_idx), reverse=False)
        for idx, obj in enumerate(all_sorted):
            if num_parts <= 1:
                displacements[obj] = max_disp
            else:
                group_factor = idx / (num_parts - 1)
                displacements[obj] = min_disp + group_factor * (max_disp - min_disp)
            directions[obj] = 1.0
            
        # Delay order: outermost first in positive direction (highest coordinate starts first)
        sorted_objects = sorted(
            all_objects,
            key=lambda o: get_sorting_key(o, axis_idx),
            reverse=True
        )
        
    elif direction_mode == 'NEG':
        # Unidirectional Negative: All components move negative, sorted highest to lowest coord
        all_sorted = sorted(all_objects, key=lambda o: get_sorting_key(o, axis_idx), reverse=True)
        for idx, obj in enumerate(all_sorted):
            if num_parts <= 1:
                displacements[obj] = max_disp
            else:
                group_factor = idx / (num_parts - 1)
                displacements[obj] = min_disp + group_factor * (max_disp - min_disp)
            directions[obj] = -1.0
            
        # Delay order: outermost first in negative direction (lowest coordinate starts first)
        sorted_objects = sorted(
            all_objects,
            key=lambda o: get_sorting_key(o, axis_idx),
            reverse=False
        )
        
    else:  # BOTH (bidirectional) mode
        # Bidirectional: positive components move positive, negative move negative relative to center
        pos_group = [obj for obj in all_objects if (1.0 if obj.location[axis_idx] >= global_center_val else -1.0) == 1.0]
        pos_sorted = sorted(pos_group, key=lambda o: get_sorting_key(o, axis_idx), reverse=False)
        num_pos = len(pos_sorted)
        for idx, obj in enumerate(pos_sorted):
            if num_pos <= 1:
                displacements[obj] = max_disp
            else:
                group_factor = idx / (num_pos - 1)
                displacements[obj] = min_disp + group_factor * (max_disp - min_disp)
            directions[obj] = 1.0
            
        neg_group = [obj for obj in all_objects if (1.0 if obj.location[axis_idx] >= global_center_val else -1.0) == -1.0]
        neg_sorted = sorted(neg_group, key=lambda o: get_sorting_key(o, axis_idx), reverse=True)
        num_neg = len(neg_sorted)
        for idx, obj in enumerate(neg_sorted):
            if num_neg <= 1:
                displacements[obj] = max_disp
            else:
                group_factor = idx / (num_neg - 1)
                displacements[obj] = min_disp + group_factor * (max_disp - min_disp)
            directions[obj] = -1.0
            
        # Delay order: furthest from center (on both sides) starts first to prevent collisions
        sorted_objects = sorted(
            all_objects, 
            key=lambda o: abs(get_sorting_key(o, axis_idx) - global_center_val), 
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
        displacement = displacements.get(obj, max_disp)
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