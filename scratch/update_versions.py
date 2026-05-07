import os
import re

ui_dir = r'd:\rfi_vps_version\ui'
files = [f for f in os.listdir(ui_dir) if f.endswith('.html')]

for filename in files:
    path = os.path.join(ui_dir, filename)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace v=1.x with v=1.6
    new_content = re.sub(r'(js/.*?\.js)(\?v=1\.\d+)?', r'\1?v=1.6', content)
    
    # Also handle script tags without v=
    # This is trickier to do without double-replacing, but re.sub handles it
    
    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filename}")
