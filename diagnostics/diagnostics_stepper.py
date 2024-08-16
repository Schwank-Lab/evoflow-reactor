import sys
from pathlib import Path

def generate_script(rotation_deg, temp_dir=Path('tmp'), script_name='diagnostics_stepper.py'):
    script_content = f"""from diagnostics import stop_all, test_stepper_rotation 

stop_all() 
test_stepper_rotation({rotation_deg})
"""
    temp_dir.mkdir(exist_ok=True)
    with open(temp_dir / script_name, 'w') as script_file:
        script_file.write(script_content)
    print(f"Script generated and stored to {temp_dir}/{script_name}")

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