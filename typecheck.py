#!/usr/bin/env python3
import subprocess
import sys
import os

os.chdir('frontend')
cmd = ['npx', 'tsc', '--noEmit']
print(f"Running: {' '.join(cmd)}")
proc = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

for line in proc.stdout:
    print(line, end='')

proc.wait()
sys.exit(proc.returncode)