with open("/workspaces/FusionEMS-Core/frontend/app/founder-command/page.tsx") as f:
    lines = f.readlines()

in_tax = False
depth = 0
for i, line in enumerate(lines):
    if '{activeTab === "tax"' in line:
        in_tax = True
        print(f"Start at {i+1}")
    if in_tax:
        opens = line.count("<div")
        closes = line.count("</div")
        depth += (opens - closes)
        if depth < 0 or (depth == 0 and opens == 0 and closes == 0 and "</motion.div>" in line):
            print(f"End at {i+1}, depth before motion/div {depth}")
            if "</motion.div>" in line: in_tax = False

