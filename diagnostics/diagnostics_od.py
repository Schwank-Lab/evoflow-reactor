import sys
from pathlib import Path

def generate_script(incubator, temp_dir=Path('tmp'), script_name='diagnostics_od.py'):
    assert incubator in {'inc_left', 'inc_right'}
    measure_od = 'measure_od_inc_left' if incubator == 'inc_left' else 'measure_od_inc_right'
    script_content = f"""from diagnostics import stop_all, test_od, {measure_od}

stop_all() 
test_od({measure_od})
"""
    temp_dir.mkdir(exist_ok=True)
    with open(temp_dir / script_name, 'w') as script_file:
        script_file.write(script_content)
    print(f"Script generated and stored to {temp_dir}/{script_name}")



