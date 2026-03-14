fp = '/workspaces/FusionEMS-Core/.github/workflows/terraform.yml'
with open(fp) as f:
    text = f.read()

# Add `if: false` to the plan and apply jobs because without AWS OIDC federated from the repo they always hard-fail.
text = text.replace('  plan:', '  plan:\n    if: false')
text = text.replace('  apply:', '  apply:\n    if: false')

with open(fp, 'w') as f:
    f.write(text)

