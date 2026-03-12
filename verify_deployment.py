import os
import sys
import json
import subprocess

def check_aws_cli():
    """Check if AWS CLI is available and credentials are valid"""
    try:
        result = subprocess.run(['aws', 'sts', 'get-caller-identity'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            print(f"✅ AWS CLI available")
            print(f"   Account: {data.get('Account')}")
            print(f"   User: {data.get('Arn')}")
            return True
        else:
            print(f"❌ AWS CLI error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ AWS CLI not installed")
        return False
    except Exception as e:
        print(f"❌ AWS CLI check failed: {e}")
        return False

def check_terraform():
    """Check if Terraform is available"""
    try:
        result = subprocess.run(['terraform', 'version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ Terraform available: {version_line}")
            return True
        else:
            print(f"❌ Terraform error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ Terraform not installed")
        return False
    except Exception as e:
        print(f"❌ Terraform check failed: {e}")
        return False

def check_docker():
    """Check if Docker is available"""
    try:
        result = subprocess.run(['docker', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ Docker available: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Docker error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ Docker not installed")
        return False
    except Exception as e:
        print(f"❌ Docker check failed: {e}")
        return False

def check_aws_resources():
    """Check if AWS resources exist"""
    try:
        # Check S3 state bucket
        bucket_name = "fusionems-terraform-state-prod"
        result = subprocess.run(['aws', 's3api', 'head-bucket', '--bucket', bucket_name],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ S3 state bucket exists: {bucket_name}")
            
            # Check if state file exists
            result = subprocess.run(['aws', 's3api', 'list-objects-v2', '--bucket', bucket_name, '--prefix', 'fusionems/prod/'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                data = json.loads(result.stdout) if result.stdout else {}
                if data.get('Contents'):
                    print(f"✅ Terraform state file exists")
                    for obj in data['Contents']:
                        print(f"   - {obj['Key']} ({obj['Size']} bytes)")
                else:
                    print(f"⚠️  No state files found in bucket")
            else:
                print(f"⚠️  Could not list bucket contents")
        else:
            print(f"❌ S3 state bucket does not exist: {bucket_name}")
            print(f"   Error: {result.stderr}")
            
    except Exception as e:
        print(f"❌ AWS resource check failed: {e}")
        return False

def check_backend_build():
    """Check if backend can be built"""
    backend_dir = 'backend'
    if not os.path.exists(backend_dir):
        print(f"❌ Backend directory not found")
        return False
    
    print(f"✅ Backend directory exists")
    
    # Check requirements
    req_file = os.path.join(backend_dir, 'requirements.txt')
    if os.path.exists(req_file):
        with open(req_file, 'r') as f:
            lines = [l.strip() for l in f.readlines() if l.strip() and not l.startswith('#')]
            print(f"   {len(lines)} dependencies in requirements.txt")
    else:
        print(f"⚠️  requirements.txt not found")
        
    # Check Dockerfile
    dockerfile = os.path.join(backend_dir, 'Dockerfile')
    if os.path.exists(dockerfile):
        print(f"✅ Dockerfile exists")
    else:
        print(f"❌ Dockerfile not found")
        return False
        
    return True

def check_frontend_build():
    """Check if frontend can be built"""
    frontend_dir = 'frontend'
    if not os.path.exists(frontend_dir):
        print(f"❌ Frontend directory not found")
        return False
    
    print(f"✅ Frontend directory exists")
    
    # Check package.json
    package_file = os.path.join(frontend_dir, 'package.json')
    if os.path.exists(package_file):
        with open(package_file, 'r') as f:
            data = json.load(f)
            print(f"   Package: {data.get('name', 'Unknown')} v{data.get('version', 'Unknown')}")
    else:
        print(f"❌ package.json not found")
        return False
        
    # Check Dockerfile
    dockerfile = os.path.join(frontend_dir, 'Dockerfile')
    if os.path.exists(dockerfile):
        print(f"✅ Dockerfile exists")
    else:
        print(f"⚠️  Dockerfile not found (may use multi-stage build)")
        
    return True

def main():
    print("=== FusionEMS Deployment Verification ===\n")
    
    checks = {
        "AWS CLI": check_aws_cli(),
        "Terraform": check_terraform(),
        "Docker": check_docker(),
        "AWS Resources": check_aws_resources(),
        "Backend Build": check_backend_build(),
        "Frontend Build": check_frontend_build(),
    }
    
    print("\n=== Summary ===")
    passed = sum(1 for check in checks.values() if check)
    total = len(checks)
    
    for name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print(f"\n{passed}/{total} checks passed")
    
    if passed == total:
        print("\n✅ All checks passed. Ready for deployment.")
        return 0
    else:
        print("\n❌ Some checks failed. Please fix before deployment.")
        return 1

if __name__ == "__main__":
    sys.exit(main())