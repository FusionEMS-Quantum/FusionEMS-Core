import os
import re

def fix_file(path):
    if not os.path.exists(path): return
    with open(path, 'r') as f:
        content = f.read()

    # Classes and patterns to replace 
    content = re.sub(r'var\(--color-brand-orange\)', '#FF4D00', content)
    content = re.sub(r'var\(--q-orange\)', '#FF4D00', content)
    content = re.sub(r'var\(--color-bg-panel\)', '#0A0A0B', content)
    content = re.sub(r'var\(--color-border\)', '#27272A', content) # zinc-800
    content = content.replace('chamfer-4', '')

    # Headings
    content = re.sub(r'text-xl font-bold uppercase tracking-wider text-text-primary', 'text-2xl font-black tracking-[0.1em] text-white uppercase', content)

    # Buttons
    content = re.sub(r'bg-orange text-black font-bold px-6 py-2.5 text-sm uppercase tracking-wider hover:bg-orange-bright transition-colors chamfer-4 disabled:opacity-50 disabled:cursor-not-allowed', 'bg-[#FF4D00] hover:bg-[#E64500] text-black font-black uppercase tracking-[0.2em] text-[11px] px-8 py-3 transition-all disabled:opacity-50 disabled:grayscale', content)
    
    # Text styles
    content = re.sub(r'text-sm transition-colors disabled:opacity-40', 'text-[11px] font-bold tracking-[0.2em] text-zinc-500 hover:text-white uppercase transition-colors disabled:opacity-40', content)


    # Borders
    content = re.sub(r'border p-8 flex flex-col items-center justify-center gap-4', 'bg-[#050505] border border-zinc-800 p-12 flex flex-col items-center justify-center gap-6', content)
    content = re.sub(r'border p-8', 'bg-zinc-950 border border-zinc-800 p-8', content)
    content = re.sub(r'border p-6 md:p-8', 'bg-zinc-950 border border-zinc-800 p-6 md:p-8', content)

    # Inner boxes
    content = re.sub(r'border p-4 overflow-y-auto', 'bg-[#050505] border border-zinc-900 p-5 overflow-y-auto', content)
    
    # Inputs
    content = re.sub(r'bg-\[rgba\(255,255,255,0\.05\)\] border border-border-DEFAULT px-3 py-2 text-sm text-text-primary placeholder-\[rgba\(255,255,255,0\.\d+\)\] focus:outline-none focus:border-orange w-full', 'bg-[#050505] border border-zinc-800 px-4 py-3 text-[12px] font-mono text-zinc-100 placeholder-zinc-700 w-full focus:border-[#FF4D00] transition-colors focus:outline-none uppercase', content)

    with open(path, 'w') as f:
        f.write(content)

fix_file('frontend/app/signup/legal/page.tsx')
fix_file('frontend/app/signup/checkout/page.tsx')
fix_file('frontend/app/signup/success/page.tsx')
