import os
import subprocess
import sys

print("=== System Check ===")
print(f"Python: {sys.version}")
print(f"Current dir: {os.getcwd()}")
print(f"Files in current dir: {len(os.listdir('.'))}")

# Check for AWS environment variables
aws_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'AWS_DEFAULT_REGION']
for var in aws_vars:
    value = os.getenv(var)
    if value:
        print(f"{var}: {'*' * 8 if 'SECRET' in var or 'KEY' in var else value}")
    else:
        print(f"{var}: Not set")

# Check for Terraform
print("\n=== Checking for Terraform ===")
try:
    result = subprocess.run(['which', 'terraform'], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Terraform found at: {result.stdout.strip()}")
        # Try to get version
        version_result = subprocess.run(['terraform', 'version'], capture_output=True, text=True)
        print(f"Terraform version: {version_result.stdout.split('\n')[0] if version_result.stdout else 'Unknown'}")
    else:
        print("Terraform not found")
except Exception as e:
    print(f"Error checking for Terraform: {e}")

# Check for Docker
print("\n=== Checking for Docker ===")
try:
    result = subprocess.run(['which', 'docker'], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Docker found at: {result.stdout.strip()}")
        version_result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        print(f"Docker version: {version_result.stdout.strip() if version_result.stdout else 'Unknown'}")
    else:
        print("Docker not found")
except Exception as e:
    print(f"Error checking for Docker: {e}")

# Check for AWS CLI
print("\n=== Checking for AWS CLI ===")
try:
    result = subprocess.run(['which', 'aws'], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"AWS CLI found at: {result.stdout.strip()}")
        # Try to get caller identity
        caller_result = subprocess.run(['aws', 'sts', 'get-caller-identity', '--output', 'text', '--query', 'Account'], 
                                      capture_output=True, text=True, timeout=5)
        if caller_result.returncode == 0:
            print(f"AWS Account ID: {caller_result.stdout.strip()}")
            print("AWS credentials are valid")
        else:
            print(f"AWS credentials invalid or not configured: {caller_result.stderr.strip()}")
    else:
        print("AWS CLI not found")
except Exception as e:
    print(f"Error checking AWS CLI: {e}")

# Check backend build
print("\n=== Checking Backend Build ===")
backend_dir = 'backend'
if os.path.exists(backend_dir):
    print(f"Backend directory exists with {len(os.listdir(backend_dir))} items")
    if os.path.exists(os.path.join(backend_dir, 'requirements.txt')):
        with open(os.path.join(backend_dir, 'requirements.txt'), 'r') as f:
            lines = f.readlines()
            print(f"Backend has {len(lines)} dependencies in requirements.txt")
else:
    print("Backend directory not found")

# Check frontend build
print("\n=== Checking Frontend Build ===")
frontend_dir = 'frontend'
if os.path.exists(frontend_dir):
    print(f"Frontend directory exists with {len(os.listdir(frontend_dir))} items")
    if os.path.exists(os.path.join(frontend_dir, 'package.json')):
        print("Frontend package.json exists")
else:
    print("Frontend directory not found")