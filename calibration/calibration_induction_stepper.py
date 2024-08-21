import sys
import os
from pathlib import Path

def generate_script(rotation_dir, tmp_dir=Path('tmp'), script_name='calibrate_induction_stepper.py'):
    script_content = f"""from calibration import stop_all, calibrate_stepper

stop_all()
calibrate_stepper(rotation_dir={rotation_dir})
"""
    tmp_dir.mkdir(exist_ok=True)
    with open(tmp_dir / script_name, 'w') as script_file:
        script_file.write(script_content)
    print(f"Script generated and stored to {tmp_dir}/{script_name}")