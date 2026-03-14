with open('frontend/services/api.ts', 'r') as f:
    lines = f.readlines()

# Find all export async function lines
func_lines = []
for i, line in enumerate(lines):
    if 'export async function' in line:
        func_lines.append(i)

print(f"Total functions: {len(func_lines)}")

# Check each function for proper closing
for i, idx in enumerate(func_lines):
    start = idx
    end = func_lines[i+1] if i+1 < len(func_lines) else len(lines)
    snippet = lines[start:end]
    # Count braces
    open_braces = 0
    for j, line in enumerate(snippet):
        open_braces += line.count('{')
        open_braces -= line.count('}')
        if open_braces == 0 and j > 0:
            # Function closed
            break
    else:
        # Loop didn't break, function may not be closed
        print(f"Possible unclosed function at line {start}: {lines[start].strip()}")
        # Show first few lines
        for k in range(min(5, len(snippet))):
            print(f"  {start+k}: {snippet[k].rstrip()}")

print("\nDone.")