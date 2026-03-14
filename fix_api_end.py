import os

with open('frontend/services/api.ts', 'r') as f:
    content = f.read()

# Find the start of the broken function
target = "export async function listPatientPortalIdentityMerges(): Promise<PatientPortalIdentityMergeRequestApi[]> {"
idx = content.find(target)
if idx == -1:
    print("Function not found")
    exit(1)

print(f"Found at position {idx}")

# Keep everything before the function start
new_content = content[:idx]

# Append the corrected function
corrected = '''export async function listPatientPortalIdentityMerges(): Promise<PatientPortalIdentityMergeRequestApi[]> {
  const res = await API.get('/api/v1/identity/merges', {
    headers: patientPortalQsAuthHeaders(),
    validateStatus: () => true,
  });
  if (res.status < 200 || res.status >= 300) {
    return [];
  }
  const data = asJsonObject(res.data);
  const items = Array.isArray(data.items) ? data.items : [];
  return items.map((item) => {
    const row = asJsonObject(item);
    return {
      id: asString(row.id),
      source_patient_id: asString(row.source_patient_id),
      target_patient_id: asString(row.target_patient_id),
      status: asString(row.status),
      merge_reason: asString(row.merge_reason) || null,
      requested_by_user_id: asString(row.requested_by_user_id),
      reviewed_by_user_id: asString(row.reviewed_by_user_id) || null,
      created_at: asString(row.created_at),
    };
  });
}
'''

new_content += corrected

# Write back
with open('frontend/services/api.ts', 'w') as f:
    f.write(new_content)

print("File fixed.")