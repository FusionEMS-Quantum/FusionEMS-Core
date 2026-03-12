with open('frontend/services/api.ts', 'r') as f:
    content = f.read()

# Find position of the last function
target = "export async function listPatientPortalIdentityMerges(): Promise<PatientPortalIdentityMergeRequestApi[]> {"
idx = content.find(target)
if idx == -1:
    print("Function not found")
    exit(1)

print(f"Found at position {idx}")
print("Text from idx to end length:", len(content) - idx)
print("First 500 chars after idx:")
print(repr(content[idx:idx+500]))
print("\nLast 500 chars of file:")
print(repr(content[-500:]))

# Count newlines after idx
newline_count = content[idx:].count('\n')
print(f"\nNumber of lines after function start: {newline_count}")

# Let's get the exact function text by looking for the closing brace
# Find the next '}' at the same indentation level
lines = content[idx:].split('\n')
func_lines = []
brace_count = 0
for i, line in enumerate(lines):
    func_lines.append(line)
    brace_count += line.count('{')
    brace_count -= line.count('}')
    if brace_count == 0 and i > 0:
        break

print(f"Function spans {len(func_lines)} lines:")
for i, line in enumerate(func_lines):
    print(f"{i}: {line}")

# Now get everything after the function
func_end_idx = idx + len('\n'.join(func_lines))
remaining = content[func_end_idx:]
print(f"\nRemaining characters after function: {len(remaining)}")
print("First 200 chars of remaining:")
print(repr(remaining[:200]))
print("\nAll remaining lines:")
remaining_lines = remaining.split('\n')
for i, line in enumerate(remaining_lines[:50]):
    print(f"{i}: {repr(line)}")