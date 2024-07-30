

import sys
import os

def generate_script(rotation_deg):
    script_content = f"""from diagnostics import stop_all, test_stepper_rotation 

stop_all() 
test_stepper_rotation({rotation_deg})
"""
    os.makedirs('tmp', exist_ok=True)
    with open('tmp/diagnostics_stepper.py', 'w') as script_file:
        script_file.write(script_content)
    print("Script generated and stored to tmp/diagnostics_stepper.py")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python diagnostics_stepper.py <rotation_degrees>")
        sys.exit(1)
    
    rotation_deg = sys.argv[1]
    try:
        rotation_deg = float(rotation_deg)
    except ValueError:
        print("The rotation_degrees parameter must be a valid float.")
        sys.exit(1)
    
    generate_script(rotation_deg)