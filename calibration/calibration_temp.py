import sys
import os

def generate_script(temp):
    script_content = f"""from calibration import stop_all, calibrate_temp

stop_all()
calibrate_temp({temp})
"""
    os.makedirs('tmp', exist_ok=True)
    with open('tmp/calibrate_temp.py', 'w') as script_file:
        script_file.write(script_content)
    print("Script generated and stored to tmp/calibrate_temp.py")

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