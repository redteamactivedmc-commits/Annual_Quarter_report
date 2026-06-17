#!/usr/bin/env python3
"""
Quick setup script to save Asana token directly to .env file.
Usage: python setup_asana.py <your_asana_token>
"""

import os
import sys

if len(sys.argv) < 2:
    print("Usage: python setup_asana.py <your_asana_token>")
    print("\nExample:")
    print("  python setup_asana.py 2/1234567890abcdef1234567890abcdef")
    sys.exit(1)

token = sys.argv[1].strip()

# Find the .env file location
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, ".env")

# Read existing variables
env_vars = {}
if os.path.exists(env_path):
    print(f"✓ Found existing .env at {env_path}")
    try:
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    env_vars[key.strip()] = val.strip()
        print(f"  Loaded {len(env_vars)} existing variables")
    except Exception as e:
        print(f"✗ Error reading .env: {e}")
        sys.exit(1)
else:
    print(f"✓ Creating new .env at {env_path}")

# Update with new token
env_vars["ASANA_PAT"] = token

# Write back
try:
    with open(env_path, "w") as f:
        for key, val in env_vars.items():
            f.write(f"{key}={val}\n")
    print(f"✓ Wrote {len(env_vars)} variables to .env")
    print(f"\n✓ ASANA_PAT set to: {token[:15]}...")
    print(f"\nNow restart the app and generate a new report.")
except Exception as e:
    print(f"✗ Error writing .env: {e}")
    sys.exit(1)
