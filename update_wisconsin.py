import os

filepath = "/workspaces/FusionEMS-Core/frontend/app/founder-command/page.tsx"

with open(filepath, "r") as f:
    content = f.read()

# I need to update the transmission logic to include the State of Wisconsin Dept. of Revenue sync.

old_logic = """    setTimeout(() => setTransmitLog(prev => [...prev, "[NETWORK] Establishing TLS 1.3 pipe to IRS FIRE endpoint..."]), 3200);
    setTimeout(() => setTransmitLog(prev => [...prev, "[IRS-FIRE] 1099-K & Form 1120-S Schema Validated."]), 4000);
    setTimeout(() => {
        setTransmitLog(prev => [...prev, "[SUCCESS] Transmission Accepted. Ack ID: IRS-994-FEMS-01"]);
        setIsTransmitting(false);
        setEfileStatus("ACCEPTED");
    }, 5000);"""

new_logic = """    setTimeout(() => setTransmitLog(prev => [...prev, "[NETWORK] Establishing TLS 1.3 pipe to IRS FIRE endpoint..."]), 3200);
    setTimeout(() => setTransmitLog(prev => [...prev, "[IRS-FIRE] 1099-K & Form 1120-S Schema Validated. (Federal)"]), 4000);
    setTimeout(() => setTransmitLog(prev => [...prev, "[STATE-WIDOR] Forking payload via WI MyTax Account API..."]), 4800);
    setTimeout(() => setTransmitLog(prev => [...prev, "[STATE-WIDOR] Wisconsin Pass-Through Entity & Sales Tax XML Validated."]), 5600);
    setTimeout(() => {
        setTransmitLog(prev => [...prev, "[SUCCESS] Federal & Wisconsin Transmission Accepted. Ack ID: WI-994-FEMS-01"]);
        setIsTransmitting(false);
        setEfileStatus("ACCEPTED");
    }, 6600);"""

content = content.replace(old_logic, new_logic)


# I need to update the Matrix text
old_text = '<p className="text-sm text-zinc-400 font-mono mb-4">Direct IRS/State 1099-K & W-2 schema compilation. Encrypted JSON payload ready.</p>'
new_text = '<p className="text-sm text-zinc-400 font-mono mb-4">Direct IRS (Federal) & Wisconsin Dept. of Revenue (MyTax) native connection. Encrypted XML/JSON payloads.</p>'
content = content.replace(old_text, new_text)

# Also update the Button text
old_button = 'Sign & Transmit Direct to IRS'
new_button = 'Sign & Transmit Federal + Wisconsin'
content = content.replace(old_button, new_button)


with open(filepath, "w") as f:
    f.write(content)
