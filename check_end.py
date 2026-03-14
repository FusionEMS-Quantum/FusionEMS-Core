with open('frontend/services/api.ts', 'r') as f:
    content = f.read()

print(f"Total length: {len(content)}")
print("Last 1000 chars:")
print(repr(content[-1000:]))
print("\nChecking braces...")
open_braces = content.count('{')
close_braces = content.count('}')
print(f"Open braces: {open_braces}, Close braces: {close_braces}, Diff: {open_braces - close_braces}")

# Find last function
lines = content.split('\n')
for i in range(len(lines)-1, max(len(lines)-50, 0), -1):
    if 'export async function' in lines[i]:
        print(f"Last function at line {i}: {lines[i]}")
        for j in range(i, min(i+10, len(lines))):
            print(f"{j}: {lines[j]}")
        break