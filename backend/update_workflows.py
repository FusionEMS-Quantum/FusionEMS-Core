import glob


def patch_file(filepath):
    with open(filepath) as f:
        content = f.read()

    if 'tflint --init' in content and 'GITHUB_TOKEN' not in content:
        # We need to add env: GITHUB_TOKEN to the Init TFLint step
        content = content.replace(
            "run: tflint --init",
            "run: tflint --init\n        env:\n          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}"
        )
    with open(filepath, 'w') as f:
        f.write(content)


for wp in glob.glob('/workspaces/FusionEMS-Core/.github/workflows/*.yml'):
    patch_file(wp)

