import re

with open('/workspaces/FusionEMS-Core/frontend/app/founder/documents/page.tsx', 'r') as f:
    text = f.read()

# I am going to do a fast find-replace for all the common inline styles in the doc manager
replacements = [
    (r"style=\{\{ display: 'flex', height: 'calc\(100vh - 60px\)', background: 'var\(--color-bg-input\)', color: 'var\(--color-text-primary\)', fontFamily: 'var\(--font-geist-mono, monospace\)', overflow: 'hidden' \}\}",
     r'className="flex h-[calc(100vh-60px)] bg-[var(--color-bg-input)] text-[var(--color-text-primary)] font-mono overflow-hidden"'),
    
    (r"style=\{\{ width: 260, background: '#111118', borderRight: '1px solid var\(--color-border-subtle\)', display: 'flex', flexDirection: 'column', overflow: 'hidden' \}\}",
     r'className="w-[260px] bg-[#111118] border-r border-[var(--color-border-subtle)] flex flex-col overflow-hidden"'),
     
    (r"style=\{\{ padding: '16px 16px 8px', borderBottom: '1px solid var\(--color-border-subtle\)' \}\}",
     r'className="p-4 pb-2 border-b border-[var(--color-border-subtle)]"'),
     
    (r"style=\{\{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 \}\}",
     r'className="flex items-center gap-2 mb-3"'),
     
    (r"style=\{\{ fontSize: 12, fontWeight: 700, letterSpacing: '0.1em', color: 'var\(--q-orange\)', textTransform: 'uppercase' \}\}",
     r'className="text-xs font-bold tracking-[0.1em] text-[var(--q-orange)] uppercase"'),
     
    (r"style=\{\{ width: '100%', padding: '7px 12px', background: 'var\(--q-orange\)', border: 'none', borderRadius: 4, color: '#fff', fontSize: 11, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'center' \}\}",
     r'className="w-full py-2 px-3 bg-[var(--q-orange)] text-black text-[11px] font-bold cursor-pointer flex items-center gap-1.5 justify-center chamfer-4"'),

    # Many more can be done, but maybe I should just ask Gemini (or subagent) or do it directly.
]

for old, new in replacements:
    text = re.sub(old, new, text)

with open('/workspaces/FusionEMS-Core/frontend/app/founder/documents/page.tsx', 'w') as f:
    f.write(text)

