import sys
import os
from pathlib import Path

def generate_script(speed_frac, tmp_dir=Path('tmp'), script_name='calibrate_inc_stirrer.py'):   
    script_content = f"""from calibration import stop_all, calibrate_inc_stirrer

stop_all()
calibrate_inc_stirrer(top_speed_frac={speed_frac})
"""
    tmp_dir.mkdir(exist_ok=True)
    with open(tmp_dir / script_name, 'w') as script_file:
        script_file.write(script_content)
    print(f"Script generated and stored to {tmp_dir}/{script_name}")

def write_speed_frac_to_file(speed_frac, exp_name):
    file_path = f'experiments/{exp_name}/inc_stirrer_speed_frac.txt'
    with open(file_path, 'w') as speed_file:
        speed_file.write(str(speed_frac))
    print(f"Speed fraction written to {file_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python calibration_inc_stirrer.py <speed_frac>")
        sys.exit(1)
    
    speed_frac = sys.argv[1]
    try:
        speed_frac = float(speed_frac)
    except ValueError:
        print("The speed_frac parameter must be a valid float.")
        sys.exit(1)
    
    exp_name = os.getenv('EXP_NAME')
    if not exp_name:
        print("The EXP_NAME environment variable is not set.")
        sys.exit(1)
    
    generate_script(speed_frac)
    write_speed_frac_to_file(speed_frac, exp_name)