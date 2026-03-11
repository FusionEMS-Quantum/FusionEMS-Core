import subprocess
import os

print("Running Validation Gates via Subprocess Bridge...")
env = os.environ.copy()
env["AWS_PROFILE"] = "fusion"

cmd = ["bash", "-c", "source /workspaces/FusionEMS-Core/.venv/bin/activate && /workspaces/FusionEMS-Core/.venv/bin/python /workspaces/FusionEMS-Core/scripts/multi_agent_execution.py --mode validate --aws-profile fusion"]

proc = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    env=env,
    cwd="/workspaces/FusionEMS-Core"
)

for line in proc.stdout:
    print(line, end="")

proc.wait()
print(f"\\nEXIT CODE: {proc.returncode}")
