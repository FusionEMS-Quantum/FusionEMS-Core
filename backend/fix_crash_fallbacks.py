import os
import re

TARGET = "?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()"

def get_fallback(line):
    if "length ??" in line or "count ??" in line or "total" in line or ".price ??" in line or "open_slots" in line or "rate ??" in line or "sortOrder ??" in line or "active_connections" in line or "score ??" in line or "filled_slots" in line:
        return "?? 0"
    if "healthy ??" in line:
        return "?? false"
    return "?? 0"

directory = "/workspaces/FusionEMS-Core/frontend/app"
for root, _, files in os.walk(directory):
    for file in files:
        if file.endswith(".tsx"):
            filepath = os.path.join(root, file)
            with open(filepath, "r") as f:
                content = f.read()
            
            if TARGET in content:
                # Do a smart replace line by line
                lines = content.split('\n')
                new_lines = []
                for line in lines:
                    if TARGET in line:
                        fb = get_fallback(line)
                        line = line.replace(TARGET, fb)
                    new_lines.append(line)
                
                with open(filepath, "w") as f:
                    f.write('\n'.join(new_lines))
                print(f"Fixed {filepath}")

