import sys
import os
import subprocess
import argparse

def run_step(description, cmd, check_path=None):
    print("=" * 60)
    print(f"STEP: {description}")
    print("-" * 60)
    
    try:
        full_cmd = [sys.executable] + cmd
        print(f"Command: {' '.join(full_cmd)}")
        
        ret = subprocess.call(full_cmd)
        
        if ret != 0:
            print(f"ERROR: Step failed with return code {ret}")
            return False
            
        if check_path and not os.path.exists(check_path):
            print(f"ERROR: Expected output not found: {check_path}")
            return False
            
        print("SUCCESS")
        print("=" * 60 + "\n")
        return True
        
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Auto Render TUI Pipeline")
    parser.add_argument("input_file", help="Path to SolidWorks Assembly (.SLDASM)")
    parser.add_argument("--res", default="800x600", help="Resolution in WxH format (default: 800x600)")
    
    args = parser.parse_args()
    
    input_file = os.path.abspath(args.input_file)
    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    base_dir = os.path.dirname(input_file)
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    
    # Define expected paths
    stl_dir = os.path.join(base_dir, f"{base_name}__STL")
    blend_dir = os.path.join(base_dir, f"{base_name}__BLENDER")
    blend_file = os.path.join(blend_dir, f"{base_name}.blend")

    # Step 1: SolidWorks to STL
    if not run_step("SolidWorks to STL", ["sw2stl.py", input_file], check_path=stl_dir):
        sys.exit(1)
        
    # Step 2: STL to Blender
    if not run_step("STL to Blender Scene", ["stl2blender.py", stl_dir], check_path=blend_file):
        sys.exit(1)
        
    # Step 3: Render
    if not run_step("Render to PNG", ["blender2png.py", blend_file, "--res", args.res]):
        sys.exit(1)
        
    print("\n" + "*" * 60)
    print("ALL STEPS COMPLETED SUCCESSFULLY")
    print(f"Output Directory: {blend_dir}")
    print("*" * 60)

if __name__ == "__main__":
    main()
