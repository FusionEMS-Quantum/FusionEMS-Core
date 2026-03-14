with open("/workspaces/FusionEMS-Core/frontend/app/founder-command/page.tsx") as f:
    lines = f.readlines()

in_tax = False
depth = 0
for i, line in enumerate(lines):
    if '{activeTab === "tax"' in line:
        in_tax = True
    if in_tax:
        opens = line.count("<div")
        closes = line.count("</div")
        depth += (opens - closes)
        if "</motion.div>" in line:
            print(f"At motion.div (line {i+1}), depth is {depth}")
            in_tax = False
