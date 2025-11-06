#!/usr/bin/env python3
"""
Wrapper for backwards compatibility with Railway
Simply executes energyplus-robust-api.py
"""
import sys
import os

# Get the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))
api_script = os.path.join(script_dir, 'energyplus-robust-api.py')

# Check if the target file exists
if not os.path.exists(api_script):
    print(f"Error: {api_script} not found!", file=sys.stderr)
    sys.exit(1)

# Execute the actual API script using exec
if __name__ == "__main__":
    with open(api_script, 'r') as f:
        code = f.read()
        exec(compile(code, api_script, 'exec'), {'__name__': '__main__', '__file__': api_script})
