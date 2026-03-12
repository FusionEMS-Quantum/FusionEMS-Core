#!/bin/bash

# Check if AWS credentials are available
echo "Checking AWS credentials..."

# Check for environment variables
if [[ -z "$AWS_ACCESS_KEY_ID" ]]; then
    echo "AWS_ACCESS_KEY_ID not set in environment"
else
    echo "AWS_ACCESS_KEY_ID is set"
fi

if [[ -z "$AWS_SECRET_ACCESS_KEY" ]]; then
    echo "AWS_SECRET_ACCESS_KEY not set in environment"
else
    echo "AWS_SECRET_ACCESS_KEY is set"
fi

if [[ -z "$AWS_SESSION_TOKEN" ]]; then
    echo "AWS_SESSION_TOKEN not set (may be using IAM role)"
else
    echo "AWS_SESSION_TOKEN is set"
fi

# Try to get caller identity
if command -v aws &> /dev/null; then
    echo "\nAttempting to get AWS caller identity..."
    aws sts get-caller-identity --output text --query 'Account' 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "AWS credentials are valid"
    else
        echo "AWS credentials are invalid or not configured"
    fi
else
    echo "AWS CLI not installed"
fi

# Check for Terraform
if command -v terraform &> /dev/null; then
    echo "\nTerraform version:"
    terraform version
else
    echo "\nTerraform not installed"
fi

# Check for Docker
if command -v docker &> /dev/null; then
    echo "\nDocker version:"
    docker --version
else
    echo "\nDocker not installed"
fi