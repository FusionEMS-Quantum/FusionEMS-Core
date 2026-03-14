import re

with open('frontend/services/api.ts', 'r') as f:
    content = f.read()

# Find all function definitions
matches = re.findall(r'export async function (\w+)', content)
print("Functions containing analytics:")
for m in matches:
    if 'analytics' in m.lower():
        print(f"  {m}")

print("\nAll functions count:", len(matches))
print("\nChecking for analytics endpoints...")
if 'getExecutiveSummary' in content:
    print("Found getExecutiveSummary")
if 'analytics' in content.lower():
    print("Found 'analytics' in content")
    
# Also check the backend analytics router for endpoints
with open('backend/core_app/api/analytics_router.py', 'r') as f:
    backend = f.read()
    
import re
backend_matches = re.findall(r'@router\.(get|post|put|delete|patch)[^\n]*\nasync def (\w+)', backend)
print("\nBackend analytics endpoints:")
for method, func in backend_matches:
    print(f"  {method.upper()} {func}")