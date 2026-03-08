import glob
import re

files = glob.glob('frontend/app/signup/**/*.tsx', recursive=True) + ['frontend/app/signup/page.tsx']

for path in files:
    with open(path, 'r') as f:
        content = f.read()

    # Re-apply clip paths globally to all border containers that lack it
    # We can do this safely where there's  "bg... border border"
    content = re.sub(
        r'(className="[^"]*?(bg-zinc-950|bg-\[\#0A0A0B\])[^"]*?")(>| \{)',
        r'\1 style={{ clipPath: "polygon(0 0, calc(100% - 16px) 0, 100% 16px, 100% 100%, 0 100%)" }}\3',
        content
    )
    
    # Catch any remaining bg-orange buttons
    content = re.sub(
        r'bg-orange text-(black|text-inverse) font-[a-z]+ px-6 py-[0-9\.]+ text-sm uppercase tracking-wider hover:bg-orange-bright transition-colors( chamfer-4)?',
        r'bg-[#FF4D00] hover:bg-[#E64500] text-black font-black uppercase tracking-[0.2em] text-[11px] px-8 py-4 transition-all',
        content
    )

    # Any leftover orange vars
    content = content.replace('var(--q-orange)', '#FF4D00')
    content = content.replace('var(--color-brand-orange)', '#FF4D00')

    with open(path, 'w') as f:
        f.write(content)

