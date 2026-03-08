with open("frontend/styles/tokens.css", "r") as f:
    text = f.read()

# Replace core colors to the new deeper, high-contrast palette
text = text.replace("--color-bg-base: #111111;", "--color-bg-base: #050505;")
text = text.replace("--color-bg-panel: #161616;", "--color-bg-panel: #0A0A0B;")
text = text.replace("--color-bg-void: #0a0a0a;", "--color-bg-void: #020202;")

text = text.replace("--color-brand-orange: #ff6b1a;", "--color-brand-orange: #FF4D00;")
text = text.replace("--color-brand-orange-hover: #e55a10;", "--color-brand-orange-hover: #E64500;")
text = text.replace("--color-brand-orange-dim: rgba(255, 107, 26, 0.15);", "--color-brand-orange-dim: rgba(255, 77, 0, 0.15);")
text = text.replace("--color-brand-orange-ghost: rgba(255, 107, 26, 0.05);", "--color-brand-orange-ghost: rgba(255, 77, 0, 0.05);")

text = text.replace("--q-orange: #ff6b1a;", "--q-orange: #FF4D00;")

text = text.replace("--color-border: rgba(255, 255, 255, 0.12);", "--color-border: #27272A;")
text = text.replace("--color-border-strong: rgba(255, 255, 255, 0.2);", "--color-border-strong: #3F3F46;")

# Typography should be sharper
text = text.replace("--font-sans: 'Inter', system-ui, sans-serif;", "--font-sans: 'Geist', 'Inter', system-ui, sans-serif;")
text = text.replace("--font-mono: 'JetBrains Mono', monospace;", "--font-mono: 'JetBrains Mono', 'Geist Mono', monospace;")

text = text.replace("--text-h1: 2rem;", "--text-h1: 2.25rem;")
text = text.replace("--text-h2: 1.5rem;", "--text-h2: 1.75rem;")
text = text.replace("--text-h3: 1.25rem;", "--text-h3: 1.5rem;")

# Chamfer paths
text = text.replace("--chamfer-2: polygon(0 0, calc(100% - 2px) 0, 100% 2px, 100% 100%, 0 100%);", "--chamfer-2: polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%);")
text = text.replace("--chamfer-4: polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%);", "--chamfer-4: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%);")
text = text.replace("--chamfer-6: polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%);", "--chamfer-6: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%);")

with open("frontend/styles/tokens.css", "w") as f:
    f.write(text)

