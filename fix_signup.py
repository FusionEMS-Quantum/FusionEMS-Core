import re

with open('frontend/app/signup/page.tsx', 'r') as f:
    content = f.read()

# Fix classes
content = re.sub(
    r"const inputCls = .*;",
    r'const inputCls = "bg-[#050505] border border-zinc-800 px-4 py-3 text-[12px] font-mono text-zinc-100 placeholder-zinc-700 focus:outline-none focus:border-[#FF4D00] focus:ring-1 focus:ring-[#FF4D00]/20 transition-all tracking-widest w-full uppercase";',
    content
)

content = re.sub(
    r"const selectCls = .*;",
    r'const selectCls = "bg-[#050505] border border-zinc-800 px-4 py-3 text-[12px] font-mono text-zinc-100 focus:outline-none focus:border-[#FF4D00] transition-all tracking-widest appearance-none w-full uppercase";',
    content
)

content = re.sub(
    r"const labelCls = .*;",
    r'const labelCls = "block text-[10px] font-bold mb-2 tracking-[0.2em] text-zinc-500 uppercase";',
    content
)

# Update headings
content = re.sub(
    r'className="text-2xl font-black[^"]*"',
    r'className="text-2xl md:text-3xl font-black uppercase tracking-tighter text-white mb-2"',
    content
)

content = re.sub(
    r'className="text-text-muted mb-8 text-sm"',
    r'className="text-xs font-mono tracking-widest text-zinc-500 uppercase mb-10"',
    content
)

# Update next / prev buttons
content = content.replace(
    'className="flex-1 py-3 text-center text-text-primary text-sm font-bold border border-border-DEFAULT chamfer-4 hover:border-orange transition-colors"',
    'className="flex-1 py-3 bg-zinc-900 border border-zinc-800 hover:border-zinc-500 text-zinc-300 font-bold uppercase tracking-[0.2em] text-[11px] transition-all text-center" style={{ clipPath: \'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)\' }}'
)

content = content.replace(
    'className="flex-1 py-3 text-center bg-orange text-black text-sm font-black border border-orange chamfer-4 hover:bg-orange-bright transition-colors disabled:opacity-50"',
    'className="flex-1 py-3 bg-[#FF4D00] hover:bg-[#E64500] text-black font-black uppercase tracking-[0.2em] text-[11px] border border-[#FF4D00] transition-all disabled:opacity-50 disabled:grayscale text-center" style={{ clipPath: \'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)\' }}'
)

content = content.replace(
    'className="w-full py-3 text-center bg-orange text-black text-sm font-black border border-orange chamfer-4 hover:bg-orange-bright transition-colors disabled:opacity-50"',
    'className="w-full py-4 bg-[#FF4D00] hover:bg-[#E64500] text-black font-black uppercase tracking-[0.2em] text-[11px] border border-[#FF4D00] transition-all disabled:opacity-50 hover:shadow-[0_0_20px_rgba(255,77,0,0.3)] text-center block mt-8" style={{ clipPath: \'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)\' }}'
)

content = content.replace(
    'className="w-full py-3 mt-8 bg-orange text-black font-black text-sm uppercase tracking-widest hover:bg-orange-bright transition-colors disabled:opacity-50 chamfer-4"',
    'className="w-full py-4 mt-8 bg-[#FF4D00] hover:bg-[#E64500] text-black font-black uppercase tracking-[0.2em] text-[11px] border border-[#FF4D00] transition-all disabled:opacity-50 hover:shadow-[0_0_20px_rgba(255,77,0,0.3)] text-center block" style={{ clipPath: \'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)\' }}'
)

# Update plan grid styling
content = re.sub(
    r'className={`border chamfer-4 p-4 cursor-pointer transition-colors \${.*?\}`}',
    r'className={`relative border p-6 cursor-pointer transition-all duration-300 ${plan === p.code ? "bg-[#FF4D00]/10 border-[#FF4D00] shadow-[0_0_20px_rgba(255,77,0,0.15)]" : "bg-zinc-950/50 border-zinc-800 hover:border-zinc-600"}`} style={{ clipPath: "polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)" }}',
    content
)

content = content.replace(
    '<div className="bg-panel-body border border-border-DEFAULT p-4 chamfer-4 mt-4 space-y-4">',
    '<div className="bg-zinc-950 border border-zinc-800 p-6 space-y-4 relative mt-6" style={{ clipPath: \'polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)\' }}>'
)
content = content.replace(
    'className="flex items-start gap-4 p-4 border border-border-DEFAULT chamfer-4 cursor-pointer hover:border-orange transition-colors bg-[rgba(255,255,255,0.02)]"',
    'className="flex items-start gap-4 p-5 border border-zinc-800 cursor-pointer hover:border-[#FF4D00]/50 hover:bg-[#FF4D00]/5 transition-all bg-[#0A0A0B]" style={{ clipPath: "polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)" }}'
)

# Various smaller fixes
content = content.replace('var(--color-brand-orange)', '#FF4D00')
content = content.replace('var(--q-orange)', '#FF4D00')
content = content.replace('border-orange', 'border-[#FF4D00]')


with open('frontend/app/signup/page.tsx', 'w') as f:
    f.write(content)

