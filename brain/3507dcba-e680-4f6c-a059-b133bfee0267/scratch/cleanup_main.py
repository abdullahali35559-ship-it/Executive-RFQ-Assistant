import sys
import os

target_file = r'D:\rfi_vps_version - multi agent\api\main.py'
with open(target_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# We want to keep lines before 318 (1-indexed, so 0-316)
# and lines after 1349 (1-indexed, so 1349-end)

new_lines = lines[:317]
new_lines.append("\n# ============================================\n")
new_lines.append("# ANALYTICS & SUMMARY API\n")
new_lines.append("# ============================================\n")
new_lines.extend(lines[1349:])

with open(target_file, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("File cleaned successfully.")
