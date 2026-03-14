#!/bin/bash

# Commit unstaged changes before deployment

set -e

echo "=== Committing Unstaged Changes ==="
echo ""

# Check git status
echo "Checking git status..."
git status --porcelain

echo ""
echo "These are the unstaged changes mentioned in the audit report."
echo "They include API prefix standardization (/v1/... → /api/v1/...)"
echo ""

read -p "Do you want to stage and commit these changes? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Skipping commit. Changes will remain unstaged."
    exit 0
fi

echo ""
echo "Staging changes..."
git add backend/core_app/api/*.py frontend/services/api.ts

echo "Committing..."
git commit -m "chore: standardize API route prefixes and update service bindings"

echo ""
echo "✅ Changes committed"
echo ""
echo "You can now push to trigger CI/CD:"
echo "git push origin main"