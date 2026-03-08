import os, re, glob
from concurrent.futures import ThreadPoolExecutor

print("INITIALIZING SOVEREIGN SYSTEMS DIRECTIVE...")

files = glob.glob('frontend/app/**/*.tsx', recursive=True) + \
        glob.glob('frontend/app/**/*.ts', recursive=True) + \
        glob.glob('frontend/components/**/*.tsx', recursive=True)

# Tactical Token Dictionary
replacements = [
    (r'\btext-text-primary\b', 'text-zinc-100'),
    (r'\btext-text-secondary\b', 'text-zinc-400'),
    (r'\btext-text-muted\b', 'text-zinc-500'),
    (r'\btext-text-inverse\b', 'text-black'),
    (r'\bbg-bg-void\b', 'bg-black'),
    (r'\bbg-bg-base\b', 'bg-[#050505]'),
    (r'\bbg-bg-panel\b', 'bg-[#0A0A0B]'),
    (r'\border-border-DEFAULT\b', 'border-zinc-800'),
    (r'\border-border-subtle\b', 'border-zinc-900'),
    (r'\border-border-strong\b', 'border-zinc-700'),
    (r'\bbg-orange\b', 'bg-[#FF4D00]'),
    (r'\btext-orange\b', 'text-[#FF4D00]'),
    (r'\border-orange\b', 'border-[#FF4D00]'),
    (r'\bbg-orange-bright\b', 'bg-[#E64500]'),
    (r'\bbg-white\b', 'bg-zinc-950'),
    (r'\bbg-gray-900\b', 'bg-zinc-900'),
    (r'\bbg-gray-800\b', 'bg-zinc-900'),
    (r'\bbg-gray-100\b', 'bg-[#0A0A0B]'),
    (r'\bbg-gray-50\b', 'bg-[#050505]'),
    (r'\btext-gray-900\b', 'text-zinc-100'),
    (r'\btext-gray-800\b', 'text-zinc-300'),
    (r'\btext-gray-500\b', 'text-zinc-500'),
    (r'\btext-gray-400\b', 'text-zinc-500'),
    (r'\border-gray-200\b', 'border-zinc-800'),
    (r'\border-gray-300\b', 'border-zinc-800'),
    (r'\border-gray-800\b', 'border-zinc-800'),
    
    # The great decimation of rounded shapes
    (r'\brounded-(sm|md|lg|xl|2xl|3xl|full)\b', ''),
    (r'\brounded\b', ''),
    
    # Super-shadows
    (r'\bshadow-(sm|md|lg|xl|2xl)\b', 'shadow-[0_0_15px_rgba(0,0,0,0.6)]'),
]

mod_count = 0
for path in files:
    with open(path, 'r') as f:
        old = f.read()
        
    new = old
    for regex, target in replacements:
        new = re.sub(regex, target, new)
        
    new = new.replace('var(--color-bg-void)', '#000000')
    new = new.replace('var(--color-bg-base)', '#050505')
    new = new.replace('var(--color-bg-panel)', '#0A0A0B')
    new = new.replace('var(--q-orange)', '#FF4D00')
    new = new.replace('var(--color-brand-orange)', '#FF4D00')
    
    if old != new:
        with open(path, 'w') as f:
            f.write(new)
        mod_count += 1
        
print(f"TACTICAL RE-WRITE COMPLETE. MODIFIED {mod_count} MODULES.")
