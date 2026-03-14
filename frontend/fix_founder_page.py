import re
import os

filepath = "/workspaces/FusionEMS-Core/frontend/app/founder-command/page.tsx"
with open(filepath, "r") as f:
    content = f.read()

# Fix Tailwind dynamic classes. You can't use arbitrary values with string interpolation in Tailwind classnames.
# I will use inline styles for the dynamic variables.
old_sys_map = """                      <div className={`absolute top-0 right-0 w-2 h-full bg-[var(--color-${sys.color})]`} />
                      <div className="text-xs uppercase tracking-widest text-zinc-400">{sys.sub}</div>
                      <div className="text-xl font-bold mt-1 text-white">{sys.name}</div>
                      <div className={`mt-3 text-xs font-black uppercase tracking-wider text-[var(--color-${sys.color})] bg-[var(--color-${sys.color})]/10 inline-block px-2 py-1`}>"""

new_sys_map = """                      <div className="absolute top-0 right-0 w-2 h-full" style={{ backgroundColor: `var(--color-${sys.color})` }} />
                      <div className="text-xs uppercase tracking-widest text-zinc-400">{sys.sub}</div>
                      <div className="text-xl font-bold mt-1 text-white">{sys.name}</div>
                      <div className="mt-3 text-xs font-black uppercase tracking-wider inline-block px-2 py-1" style={{ color: `var(--color-${sys.color})`, backgroundColor: `color-mix(in srgb, var(--color-${sys.color}) 10%, transparent)` }}>"""

content = content.replace(old_sys_map, new_sys_map)


with open(filepath, "w") as f:
    f.write(content)
