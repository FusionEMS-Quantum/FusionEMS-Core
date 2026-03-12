with open('frontend/services/api.ts', 'r') as f:
    lines = f.readlines()

# Count braces
open_braces = 0
for i, line in enumerate(lines):
    open_braces += line.count('{')
    open_braces -= line.count('}')
    if open_braces < 0:
        print(f"ERROR: Negative brace count at line {i}: {line.strip()}")
        break

print(f"Final brace count: {open_braces}")

# Look for any unclosed functions
in_function = False
function_start = 0
for i, line in enumerate(lines):
    if 'export async function' in line and not in_function:
        in_function = True
        function_start = i
    if in_function and open_braces == 0 and i > function_start:
        # function closed
        in_function = False

if in_function:
    print(f"WARNING: Possibly unclosed function starting at line {function_start}")

# Print last 10 lines
print("\nLast 10 lines:")
for line in lines[-10:]:
    print(repr(line))