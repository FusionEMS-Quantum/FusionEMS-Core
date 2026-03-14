fp = '/workspaces/FusionEMS-Core/.github/workflows/security_compliance_enforcer.yml'
with open(fp) as f:
    text = f.read()

text = text.replace('tflint --chdir=infra/terraform/ --recursive --minimum-failure-severity=warning', 'cd infra/terraform/ && tflint --recursive --minimum-failure-severity=warning')

with open(fp, 'w') as f:
    f.write(text)
