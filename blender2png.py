import argparse
import subprocess
import os
import sys

def safe_print(s, stream=sys.stdout):
    try:
        print(s, file=stream)
    except UnicodeEncodeError:
        # Fallback for systems with limited console encoding (e.g. cp949)
        encoding = stream.encoding or 'utf-8'
        print(s.encode(encoding, errors='replace').decode(encoding), file=stream)

def run_render(blend_file, resolution):
    blend_file = os.path.normpath(os.path.abspath(blend_file))
    if not os.path.exists(blend_file):
        print(f"Error: File not found: {blend_file}")
        return

    width, height = None, None
    if resolution:
        try:
            width, height = map(int, resolution.lower().split('x'))
        except ValueError:
            print("Error: Resolution must be in format WxH (e.g., 800x600)")
            return

    import json
    
    # Defaults
    blender_exe = "blender"
    render_samples = 512
    viewport_samples = 64
    use_denoising = True
    
    # Read config.json or config.json.template
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    template_path = os.path.join(script_dir, "config.json.template")
    
    selected_path = None
    if os.path.exists(config_path):
        selected_path = config_path
    elif os.path.exists(template_path):
        selected_path = template_path
        
    if selected_path:
        try:
            with open(selected_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                blender_exe = config_data.get("blender_exe", "blender")
                render_samples = config_data.get("render_samples", 512)
                viewport_samples = config_data.get("viewport_samples", 64)
                use_denoising = config_data.get("use_denoising", True)
        except Exception as e:
            print(f"Warning: Failed to load config from {selected_path}: {e}")
    
    print("-" * 40)
    print(f"Starting Render: {os.path.basename(blend_file)}")
    if width and height:
        print(f"Resolution Override: {width} x {height}")
    else:
        print("Resolution: Keep blend file settings")

    # Create a temporary python script for Blender
    temp_script_path = os.path.join(os.path.dirname(blend_file), "_temp_render_script.py")
    temp_script_path = os.path.normpath(temp_script_path)
    
    res_setup_str = ""
    if width is not None and height is not None:
        res_setup_str = f"""
# Set Resolution
bpy.context.scene.render.resolution_x = {width}
bpy.context.scene.render.resolution_y = {height}
bpy.context.scene.render.resolution_percentage = 200
"""

    script_content = f"""
import bpy
import os
import sys

{res_setup_str}

# Set Transparent Background (RGBA)
bpy.context.scene.render.film_transparent = True
bpy.context.scene.render.image_settings.file_format = 'PNG'
bpy.context.scene.render.image_settings.color_mode = 'RGBA'

# Configure World Background to White Light
world = bpy.context.scene.world
if not world:
    world = bpy.data.worlds.new("World_White")
    bpy.context.scene.world = world
if bpy.app.version < (5, 0, 0):
    if hasattr(world, 'use_nodes') and not world.use_nodes:
        try:
            world.use_nodes = True
        except:
            pass
bg_node = world.node_tree.nodes.get("Background")
if bg_node:
    bg_node.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
    bg_node.inputs['Strength'].default_value = 1.0

# Ensure Cycles engine and GPU device are set for rendering
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.device = 'GPU'

# Set Sampling (Viewport: {viewport_samples}, Render: {render_samples}, Denoise: {use_denoising})
bpy.context.scene.cycles.preview_samples = {viewport_samples}
bpy.context.scene.cycles.samples = {render_samples}
bpy.context.scene.cycles.use_denoising = {use_denoising}

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

base_path = bpy.data.filepath
base_dir = os.path.dirname(base_path)
base_name = os.path.splitext(os.path.basename(base_path))[0]

# Find all cameras
cameras = [obj for obj in bpy.context.scene.objects if obj.type == 'CAMERA']
print(f"Found {{len(cameras)}} cameras.")

if not cameras:
    print("No cameras found, rendering active view...")
    if bpy.context.scene.camera:
         print(f"Active Camera: {{bpy.context.scene.camera.name}}")
    # Default render
    bpy.ops.render.render(write_still=True)
else:
    for cam in cameras:
        bpy.context.scene.camera = cam
        out_name = f"{{base_name}}_{{cam.name}}.png"
        bpy.context.scene.render.filepath = os.path.join(base_dir, out_name)
        print(f"Rendering Camera: {{cam.name}}")
        try:
            bpy.ops.render.render(write_still=True)
        except Exception as e:
            print(f"Error rendering {{cam.name}}: {{e}}")
"""
    
    with open(temp_script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    print(f"Created temp render script: {temp_script_path}")
    
    cmd = [blender_exe, "-b", blend_file, "-P", temp_script_path]
    print(f"Running command: {cmd}")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(blend_file)
        )
        
        import locale
        sys_encoding = locale.getpreferredencoding() or 'cp949'

        # Stream output
        while True:
            output = process.stdout.readline()
            if output == b'' and process.poll() is not None:
                break
            if output:
                try:
                    decoded = output.decode('utf-8').strip()
                except UnicodeDecodeError:
                    try:
                        decoded = output.decode(sys_encoding).strip()
                    except Exception:
                        decoded = output.decode('utf-8', errors='replace').strip()
                safe_print(decoded)

        # Check stderr remnants
        err_out = process.stderr.read()
        if err_out:
             try:
                decoded_err = err_out.decode('utf-8').strip()
             except UnicodeDecodeError:
                try:
                    decoded_err = err_out.decode(sys_encoding).strip()
                except Exception:
                    decoded_err = err_out.decode('utf-8', errors='replace').strip()
             safe_print(decoded_err, stream=sys.stderr)

        if process.returncode == 0:
            print("Render Success!")
        else:
            print(f"Render Failed (Code {process.returncode})")

    except Exception as e:
        print(f"Execution Error: {e}")
    finally:
        if os.path.exists(temp_script_path):
            try:
                os.remove(temp_script_path)
                print(f"Cleaned up temp script: {temp_script_path}")
            except Exception as e:
                print(f"Warning: Failed to delete temp script: {e}")

def main():
    parser = argparse.ArgumentParser(description="Render Blender file to PNG")
    parser.add_argument("blend_file", help="Path to .blend file")
    parser.add_argument("--res", default=None, help="Resolution in WxH format (e.g., 800x600). If omitted, keeps blend file resolution.")
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    run_render(args.blend_file, args.res)

if __name__ == "__main__":
    main()
