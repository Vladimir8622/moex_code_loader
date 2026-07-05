import subprocess
import sys

def run_script(script_name):
    print(f"Running {script_name}...")
    result = subprocess.run([sys.executable, script_name])
    if result.returncode != 0:
        print(f"Error running {script_name}, return code {result.returncode}")
        return False
    print(f"{script_name} completed successfully")
    return True

if __name__ == '__main__':
    # Часть скриптов может не запуситься из-за настроек конфига
    scripts = [
        'moex_futures_data_loader.py',
        'load_summary.py', 
        'moex_futures_merge.py',
        'tests/test_data_loader.py',
        'tests/test_merge_algorithm.py',
        'tests/test_utilities.py'
    ]
    
    for script in scripts:
        if not run_script(script):
            print(f"Failed to run {script}. Stopping.")
            break
    else:
        print("All scripts completed successfully")
