
fp = '/workspaces/FusionEMS-Core/.github/workflows/security_compliance_enforcer.yml'
with open(fp) as f:
    text = f.read()

text = text.replace('tflint --init\n          cd infra/terraform/ && tflint --recursive --minimum-failure-severity=warning', 'cd infra/terraform/ && tflint --init && tflint --recursive --minimum-failure-severity=warning')

with open(fp, 'w') as f:
    f.write(text)

fp2 = '/workspaces/FusionEMS-Core/.github/workflows/terraform.yml'
with open(fp2) as f:
    text2 = f.read()

text2 = text2.replace('tflint --init\n        env:\n          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}\n\n      - name: Run TFLint\n        run: cd ${{ env.TF_ROOT_DIR }} && tflint --recursive --minimum-failure-severity=error',
'cd ${{ env.TF_ROOT_DIR }} && tflint --init\n        env:\n          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}\n\n      - name: Run TFLint\n        run: cd ${{ env.TF_ROOT_DIR }} && tflint --recursive --minimum-failure-severity=error')

with open(fp2, 'w') as f:
    f.write(text2)

