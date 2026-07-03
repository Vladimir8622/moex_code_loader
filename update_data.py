import subprocess
import sys

def run_script(script_name):
    print(f"Running {script_name}...")
    result = subprocess.run([sys.executable, script_name], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running {script_name}:")
        print(result.stderr)
        return False
    print(f"{script_name} completed successfully")
    return True

if __name__ == '__main__':
    scripts = [
        'moex_futures_data_loader.py',
        'load_summary.py', 
        'moex_futures_merge.py'
    ]
    
    for script in scripts:
        if not run_script(script):
            print(f"Failed to run {script}. Stopping.")
            break
    else:
        print("All scripts completed successfully")
