import re

with open("frontend/tailwind.config.js", "r") as f:
    text = f.read()

# Replace border radius to aggressively strip roundness
text = re.sub(
    r'borderRadius:\s*\{[^}]+\}',
    """borderRadius: {
        none: "0",
        sm: "0",
        DEFAULT: "0",
        md: "0",
        lg: "0",
        xl: "0",
        "2xl": "0",
        "3xl": "0",
        full: "9999px"
      }""",
    text
)

with open("frontend/tailwind.config.js", "w") as f:
    f.write(text)

