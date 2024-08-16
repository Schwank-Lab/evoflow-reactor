import sys
import os
from pathlib import Path

def generate_script(temp, tmp_dir=Path('tmp'), script_name='calibrate_temp.py'):
    script_content = f"""from calibration import stop_all, calibrate_temp

stop_all()
calibrate_temp({temp})
"""
    tmp_dir.mkdir(exist_ok=True)
    with open(tmp_dir / script_name, 'w') as script_file:
        script_file.write(script_content)
    print(f"Script generated and stored to {tmp_dir}/{script_name}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python calibration)temp.py <temp>")
        sys.exit(1)
    
    temp = sys.argv[1]
    try:
        temp = float(temp)
    except ValueError:
        print("The temp parameter must be a valid float.")
        sys.exit(1)
    
    exp_name = os.getenv('EXP_NAME')
    if not exp_name:
        print("The EXP_NAME environment variable is not set.")
        sys.exit(1)
    
    generate_script(temp)