#!/usr/bin/env python3
"""Simple packaging script for django-observability skill."""
import zipfile
import os
from pathlib import Path

def package_skill():
    skill_dir = Path("django-observability")
    output_file = "django-observability.skill"

    if not skill_dir.exists():
        print(f"Error: {skill_dir} does not exist")
        return

    # Create zip file
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(skill_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, skill_dir)
                zf.write(file_path, arcname)
                print(f"Added: {arcname}")

    print(f"\nPackaged: {output_file}")
    print(f"Size: {os.path.getsize(output_file)} bytes")

if __name__ == "__main__":
    package_skill()
