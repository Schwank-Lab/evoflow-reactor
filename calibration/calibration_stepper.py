import sys
import os

def generate_script(rotation_dir):
    script_content = f"""from calibration import stop_all, calibrate_stepper

stop_all()
calibrate_stepper(rotation_dir={rotation_dir})
"""
    os.makedirs('tmp', exist_ok=True)
    with open('tmp/calibrate_stepper.py', 'w') as script_file:
        script_file.write(script_content)
    print("Script generated and stored to tmp/calibrate_stepper.py")

def write_speed_frac_to_file(speed_frac, exp_name):
    file_path = f'experiments/{exp_name}/stepper_rotation_direction.txt'
    with open(file_path, 'w') as speed_file:
        speed_file.write(str(speed_frac))
    print(f"Rotatoion direction written to {file_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python calibration_stepper.py <rotation_direction>")
        sys.exit(1)
    
    rotation_dir = sys.argv[1]
    try:
        rotation_dir = float(rotation_dir)
    except ValueError:
        print("The rotation_direction parameter must be a valid float.")
        sys.exit(1)
    
    exp_name = os.getenv('EXP_NAME')
    if not exp_name:
        print("The EXP_NAME environment variable is not set.")
        sys.exit(1)
    
    generate_script(rotation_dir)
    write_speed_frac_to_file(rotation_dir, exp_name)