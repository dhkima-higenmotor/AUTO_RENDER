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

def create_adaptive_bbox_explosion(axis='Y', factor=5.0, total_seconds=20.0):
    """
    axis: Axis along which the explosion happens ('X', 'Y', or 'Z')
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

    # 2. Sort objects using the adaptive bounding box logic
    # Parts are sorted from the highest/outermost coordinate down to the lowest
    sorted_objects = sorted(
        all_objects, 
        key=lambda o: get_sorting_key(o, axis_idx), 
        reverse=True
    )

    # 3. Calculate the global average center to determine the explosion direction
    total_val = sum(obj.location[axis_idx] for obj in all_objects)
    global_center_val = total_val / num_parts

    # 4. Calculate equal frame distribution based on a fixed 20-second duration
    fps = bpy.context.scene.render.fps  
    total_frames = int(total_seconds * fps)  # 20s * 30fps = 600 frames
    
    # Timeline split: 60% for sequential delays, 40% for individual movement duration
    if num_parts > 1:
        delay_offset = (total_frames * 0.6) / (num_parts - 1)
        duration = total_frames * 0.4
    else:
        delay_offset = 0
        duration = total_frames

    scene = bpy.context.scene
    current_delay = 0.0  

    # 5. Generate keyframes for sorted objects sequentially
    for obj in sorted_objects:
        # Determine explosion direction along the chosen axis relative to the global center
        direction = 1.0 if obj.location[axis_idx] >= global_center_val else -1.0
        if obj.location[axis_idx] == global_center_val:
            direction = 1.0

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
        obj.location[axis_idx] += direction * factor
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
try:
    explode_duration = float(os.environ.get("EXPLODE_DURATION", "20.0"))
except ValueError:
    explode_duration = 20.0
create_adaptive_bbox_explosion(axis=explode_axis, factor=5.0, total_seconds=explode_duration)