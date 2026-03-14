with open('frontend/services/api.ts', 'r') as f:
    lines = f.readlines()

# Find where to insert - before the very end
# The file ends with many blank lines and maybe some whitespace
# Let's find the last non-empty line
last_non_empty = len(lines) - 1
while last_non_empty >= 0 and lines[last_non_empty].strip() == '':
    last_non_empty -= 1

print(f"Last non-empty line {last_non_empty}: {repr(lines[last_non_empty])}")

# Check if the file ends with any closing braces or just whitespace
# Let's look at the last 20 lines
for i in range(max(0, last_non_empty - 20), last_non_empty + 1):
    print(f"{i}: {repr(lines[i])}")

# Determine where to add new functions - likely before the very end
# We'll add after the last function but before the file ends
# Let's find the last export function
last_export = -1
for i, line in enumerate(lines):
    if 'export async function' in line:
        last_export = i

print(f"Last export function at line {last_export}: {lines[last_export] if last_export >=0 else 'none'}")

# We'll insert after that line
insert_line = last_export + 1 if last_export >= 0 else len(lines) - 1
while insert_line < len(lines) and lines[insert_line].strip() != '':
    insert_line += 1

print(f"Will insert at line {insert_line}")

# Analytics API functions
analytics_functions = '''
// ── Analytics API ─────────────────────────────────────────────────────────────

export async function getAnalyticsExecutiveSummary(agencyId: string): Promise<Record<string, unknown>> {
  const res = await API.get(`/api/v1/analytics/${agencyId}/executive-summary`, { headers: aiHeaders() });
  return res.data;
}

export async function getAnalyticsOperationalMetrics(
  agencyId: string,
  periodStart?: string,
  periodEnd?: string,
): Promise<Record<string, unknown>> {
  const params: Record<string, string> = {};
  if (periodStart) params.period_start = periodStart;
  if (periodEnd) params.period_end = periodEnd;
  const res = await API.get(`/api/v1/analytics/${agencyId}/metrics/operational`, {
    headers: aiHeaders(),
    params,
  });
  return res.data;
}

export async function getAnalyticsFinancialMetrics(
  agencyId: string,
  periodStart?: string,
  periodEnd?: string,
): Promise<Record<string, unknown>> {
  const params: Record<string, string> = {};
  if (periodStart) params.period_start = periodStart;
  if (periodEnd) params.period_end = periodEnd;
  const res = await API.get(`/api/v1/analytics/${agencyId}/metrics/financial`, {
    headers: aiHeaders(),
    params,
  });
  return res.data;
}

export async function getAnalyticsClinicalMetrics(
  agencyId: string,
  periodStart?: string,
  periodEnd?: string,
): Promise<Record<string, unknown>> {
  const params: Record<string, string> = {};
  if (periodStart) params.period_start = periodStart;
  if (periodEnd) params.period_end = periodEnd;
  const res = await API.get(`/api/v1/analytics/${agencyId}/metrics/clinical`, {
    headers: aiHeaders(),
    params,
  });
  return res.data;
}

export async function getAnalyticsReadinessMetrics(
  agencyId: string,
  periodStart?: string,
  periodEnd?: string,
): Promise<Record<string, unknown>> {
  const params: Record<string, string> = {};
  if (periodStart) params.period_start = periodStart;
  if (periodEnd) params.period_end = periodEnd;
  const res = await API.get(`/api/v1/analytics/${agencyId}/metrics/readiness`, {
    headers: aiHeaders(),
    params,
  });
  return res.data;
}

export async function listAnalyticsReports(agencyId: string): Promise<Record<string, unknown>> {
  const res = await API.get(`/api/v1/analytics/${agencyId}/reports`, { headers: aiHeaders() });
  return res.data;
}

export async function generateAnalyticsReport(
  agencyId: string,
  reportDefinitionId: string,
): Promise<Record<string, unknown>> {
  const res = await API.post(
    `/api/v1/analytics/${agencyId}/reports/generate`,
    { report_definition_id: reportDefinitionId },
    { headers: aiHeaders() }
  );
  return res.data;
}

export async function getAnalyticsAlerts(
  agencyId: string,
  severity?: string,
): Promise<Record<string, unknown>> {
  const params: Record<string, string> = {};
  if (severity) params.severity = severity;
  const res = await API.get(`/api/v1/analytics/${agencyId}/alerts`, {
    headers: aiHeaders(),
    params,
  });
  return res.data;
}
'''

print("\nReady to add analytics functions.")
print(f"Inserting {len(analytics_functions.split(chr(10)))} lines.")

# Write the new file
with open('frontend/services/api.ts', 'w') as f:
    f.writelines(lines[:insert_line])
    f.write(analytics_functions)
    f.writelines(lines[insert_line:])

print("File updated.")