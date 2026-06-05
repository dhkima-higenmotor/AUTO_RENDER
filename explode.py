import bpy
import mathutils

def get_sorting_key_y(obj):
    """
    Determines the sorting key based on the bounding box position.
    If the max Y is negative, it returns the minimum Y (outermost left).
    Otherwise, it returns the maximum Y (outermost right).
    """
    matrix_world = obj.matrix_world
    world_y_coords = [(matrix_world @ mathutils.Vector(corner)).y for corner in obj.bound_box]
    
    max_y = max(world_y_coords)
    min_y = min(world_y_coords)
    
    # If the entire part is in the negative Y region, use the minimum Y as the sorting baseline
    if max_y < 0:
        return min_y
    return max_y

def create_adaptive_bbox_y_explosion(factor=5.0, total_seconds=20.0):
    """
    factor: Explosion distance multiplier
    total_seconds: Total animation duration in seconds (Default: 20.0s)
    """
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
    # Parts are sorted from the highest/outermost Y coordinate down to the lowest
    sorted_objects = sorted(
        all_objects, 
        key=get_sorting_key_y, 
        reverse=True
    )

    # 3. Calculate the global average Y center to determine the explosion direction
    total_y = sum(obj.location.y for obj in all_objects)
    global_center_y = total_y / num_parts

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
        # Determine explosion direction along the Y-axis relative to the global center
        direction_y = 1.0 if obj.location.y >= global_center_y else -1.0
        if obj.location.y == global_center_y:
            direction_y = 1.0

        # Convert frame values to integers for inserting keyframes
        start_frame = int(1 + current_delay)
        
        # Lock initial assembly position at frame 1
        scene.frame_set(1)
        obj.keyframe_insert(data_path="location", index=1)
        
        # Keep the object stationary until its specific start frame arrives
        scene.frame_set(start_frame)
        obj.keyframe_insert(data_path="location", index=1)
        
        # Smoothly move to the exploded position over the calculated duration
        end_frame = int(start_frame + duration)
        scene.frame_set(end_frame)
        
        # Apply displacement along the Y-axis
        obj.location.y += direction_y * factor
        obj.keyframe_insert(data_path="location", index=1)
        
        # Accumulate delay for the next subsequent part
        current_delay += delay_offset
        
    # Reset timeline to frame 1 and update the scene's end frame range
    scene.frame_set(1)
    scene.frame_end = total_frames
    
    print(f"--- Adaptive Bounding Box Explosion Configuration Complete ---")
    print(f"Total Parts: {num_parts} | Total Time: {total_seconds}s ({total_frames} frames)")
    print(f"Movement Duration: {int(duration)}f | Delay Offset: {delay_offset:.2f}f")

# Execute the script
create_adaptive_bbox_y_explosion(factor=5.0, total_seconds=20.0)