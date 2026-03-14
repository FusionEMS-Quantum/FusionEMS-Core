import os

with open('frontend/services/api.ts', 'r') as f:
    content = f.read()
    
print(f"File size: {len(content)}")
print("Last 2000 chars:")
print(content[-2000:])
print("\nChecking for unclosed braces...")
lines = content.split('\n')
for i, line in enumerate(lines[-20:]):
    print(f"{len(lines)-20+i}: {line}")