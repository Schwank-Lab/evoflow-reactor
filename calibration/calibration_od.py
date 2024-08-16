from pathlib import Path

def generate_script(num_probes, tmp_dir=Path('tmp'), script_name='calibrate_od.py'):
    script_content = f"""from calibration import stop_all, calibrate_od

stop_all()
calibrate_od(num_probes={num_probes})"""
    tmp_dir.mkdir(exist_ok=True)
    with open(tmp_dir / script_name, 'w') as script_file:
        script_file.write(script_content)
    print(f"Script generated and stored to {tmp_dir}/{script_name}")



