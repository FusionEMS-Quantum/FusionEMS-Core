import os

with open('frontend/services/api.ts', 'r') as f:
    content = f.read()

print(f"Length: {len(content)}")
print("Last 200 chars:")
print(repr(content[-200:]))
print("\nChecking braces...")
open_braces = content.count('{')
close_braces = content.count('}')
print(f"Open braces: {open_braces}, Close braces: {close_braces}, Diff: {open_braces - close_braces}")

# Find last incomplete function
lines = content.split('\n')
for i, line in enumerate(lines[-10:]):
    print(f"{len(lines)-10+i}: {line}")

# Find the line with the incomplete function
for i in range(len(lines)-1, max(len(lines)-30, 0), -1):
    if 'listPatientPortalIdentityMerges' in lines[i]:
        print(f"\nFound function at line {i}:")
        for j in range(max(i-2,0), min(i+10, len(lines))):
            print(f"{j}: {lines[j]}")
        break