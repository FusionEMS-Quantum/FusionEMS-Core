#!/bin/bash

# Deployment readiness check for FusionEMS

set -e

echo "=== FusionEMS Deployment Readiness Check ==="
echo ""

# Check for required tools
echo "1. Checking required tools..."
if command -v terraform &> /dev/null; then
    terraform version | head -1
else
    echo "❌ Terraform not found"
    exit 1
fi

if command -v aws &> /dev/null; then
    aws --version | head -1
else
    echo "❌ AWS CLI not found"
    exit 1
fi

if command -v docker &> /dev/null; then
    docker --version
else
    echo "❌ Docker not found"
    exit 1
fi

echo "✅ All tools available"
echo ""

# Check AWS credentials
echo "2. Checking AWS credentials..."
if aws sts get-caller-identity &> /dev/null; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    echo "✅ AWS credentials valid (Account: $ACCOUNT_ID)"
else
    echo "❌ AWS credentials invalid or not configured"
    exit 1
fi

echo ""

# Check if bootstrap has been run
echo "3. Checking AWS resources..."
BUCKET="fusionems-terraform-state-prod"
if aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
    echo "✅ S3 state bucket exists: $BUCKET"
    
    # Check for state file
    if aws s3api list-objects-v2 --bucket "$BUCKET" --prefix "fusionems/prod/" --query "Contents[?Key.contains(@, 'terraform.tfstate')]" --output text 2>/dev/null; then
        echo "✅ Terraform state file exists"
        STATE_EXISTS=true
    else
        echo "⚠️  No Terraform state file found (first deployment)"
        STATE_EXISTS=false
    fi
else
    echo "❌ S3 state bucket not found: $BUCKET"
    echo "   Run bootstrap.sh first"
    exit 1
fi

echo ""

# Check application build
echo "4. Checking application build..."
if [ -f "backend/Dockerfile" ]; then
    echo "✅ Backend Dockerfile exists"
else
    echo "❌ Backend Dockerfile not found"
    exit 1
fi

if [ -f "frontend/package.json" ]; then
    echo "✅ Frontend package.json exists"
else
    echo "❌ Frontend package.json not found"
    exit 1
fi

echo ""

# Check GitHub Actions OIDC
echo "5. Checking GitHub OIDC configuration..."
if aws iam list-open-id-connect-providers --query "OpenIDConnectProviderList[?ends_with(Arn, '/token.actions.githubusercontent.com')].Arn" --output text 2>/dev/null | grep -q "arn:"; then
    echo "✅ GitHub OIDC provider exists"
else
    echo "⚠️  GitHub OIDC provider not found (run bootstrap.sh)"
fi

echo ""

# Summary
echo "=== Summary ==="
echo ""
if [ "$STATE_EXISTS" = true ]; then
    echo "Status: Infrastructure may already be deployed"
    echo "Next: Check current state with 'terraform plan'"
else
    echo "Status: Ready for first deployment"
    echo "Next: Run 'terraform apply'"
fi

echo ""
echo "To proceed with deployment:"
echo "1. cd infra/terraform/environments/prod"
echo "2. terraform init"
echo "3. terraform plan"
echo "4. terraform apply"
echo ""
echo "Or use GitHub Actions workflow:"
echo "1. Go to GitHub Actions"
echo "2. Run 'terraform' workflow with allow_apply=true"