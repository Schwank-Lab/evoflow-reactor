import sys
import os
from pathlib import Path

def generate_script(num_steps, tmp_dir=Path('tmp'), script_name='calibrate_bact_stepper.py'):
    script_content = f"""from calibration import stop_all, calibrate_pump_incubator_to_lagoon

stop_all()
calibrate_pump_incubator_to_lagoon(num_steps={num_steps})
"""
    tmp_dir.mkdir(exist_ok=True)
    with open(tmp_dir / script_name, 'w') as script_file:
        script_file.write(script_content)
    print(f"Script generated and stored to {tmp_dir}/{script_name}")