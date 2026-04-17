#!/usr/bin/env python3
"""
Debug script to simulate get_all_parent_folders logic
"""
import sys
sys.path.insert(0, '.')

from api.db.db_models import DB, File
from api.db.services.file_service import FileService

def debug_ancestors(file_id):
    print(f"Debugging ancestors for file_id: {file_id}")
    parent_folders = []
    current_id = file_id
    visited = set()

    while current_id:
        print(f"  current_id: {current_id}")
        if current_id in visited:
            print(f"  ⚠️ CYCLE DETECTED! Already visited {current_id}")
            break
        visited.add(current_id)

        e, file = FileService.get_by_id(current_id)
        print(f"    get_by_id result: e={e}, file={'None' if not e else f'id={file.id}, parent_id={file.parent_id}'}")

        if e and file.parent_id != file.id:
            parent_folders.append(file)
            current_id = file.parent_id
            print(f"    parent_id != id, moving to parent: {current_id}")
        else:
            if e:
                parent_folders.append(file)
            print(f"    else branch: break")
            break

        if len(visited) > 20:
            print(f"  ⚠️ TOO MANY ITERATIONS (>20), breaking")
            break

    print(f"  Result parent_folders count: {len(parent_folders)}")
    for pf in parent_folders:
        print(f"    - {pf.id} ({pf.name}) parent={pf.parent_id}")
    return parent_folders

if __name__ == "__main__":
    # Test with problematic file_id
    file_id = "44b0cadc371611f1b1b31e71dcb42474"
    debug_ancestors(file_id)

    # Also test root folder
    print("\n\nTesting root folder:")
    root_id = "aff56f5e323011f18dd21e71dcb42474"
    debug_ancestors(root_id)