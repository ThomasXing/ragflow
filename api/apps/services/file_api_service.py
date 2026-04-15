#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import logging
import os
import pathlib

from api.common.check_team_permission import check_file_team_permission
from api.common.check_file_permission import (
    check_file_permission,
    check_file_operation_permission,
    check_parent_folder_permission,
)
from api.db import FileType, FilePermissionLevel
from api.db.services import duplicate_name
from api.db.services.document_service import DocumentService
from api.db.services.file2document_service import File2DocumentService
from api.db.services.file_service import FileService
from api.db.services.team_permission_service import TeamPermissionService
from api.db.services.file_permission_service import FilePermissionService
from api.utils.file_utils import filename_type
from common import settings
from common.constants import FileSource
from common.misc_utils import get_uuid, thread_pool_exec


async def upload_file(tenant_id: str, pf_id: str, file_objs: list, user_id: str = None):
    """
    Upload files to a folder.

    :param tenant_id: tenant ID
    :param pf_id: parent folder ID
    :param file_objs: list of file objects from request
    :param user_id: user ID (for permission check, defaults to tenant_id)
    :return: (success, result_list) or (success, error_message)
    """
    if user_id is None:
        user_id = tenant_id

    if not pf_id:
        root_folder = FileService.get_root_folder(tenant_id)
        pf_id = root_folder["id"]

    e, pf_folder = FileService.get_by_id(pf_id)
    if not e:
        return False, "Can't find this folder!"

    # Resolve the folder owner's tenant_id for resource attribution.
    # In team sharing scenarios, the current user (user_id) may differ from
    # the folder owner (pf_folder.tenant_id). The file's tenant_id MUST
    # inherit the folder owner's so that FileService.get_by_pf_id (which
    # filters by tenant_id) can find it for both the owner and team members.
    folder_tenant_id = pf_folder.tenant_id if pf_folder else tenant_id

    # Check permission: need EDIT permission on the target folder itself.
    # NOTE: we call check_file_permission(pf_id) directly rather than
    # check_parent_folder_permission(pf_id). The latter looks up pf_folder.parent_id
    # and checks *that* ancestor, but team shares are set on pf_id itself —
    # checking the wrong folder level would always deny team members.
    has_perm, msg = check_file_permission(pf_id, user_id, FilePermissionLevel.EDIT)
    if not has_perm:
        return False, msg or "You don't have permission to upload files to this folder."

    file_res = []
    for file_obj in file_objs:
        MAX_FILE_NUM_PER_USER = int(os.environ.get('MAX_FILE_NUM_PER_USER', 0))
        # Use folder owner's tenant_id for quota check, not the uploader's
        if 0 < MAX_FILE_NUM_PER_USER <= await thread_pool_exec(DocumentService.get_doc_count, folder_tenant_id):
            return False, "Exceed the maximum file number of a free user!"

        if not file_obj.filename:
            file_obj_names = [pf_folder.name, file_obj.filename]
        else:
            full_path = '/' + file_obj.filename
            file_obj_names = full_path.split('/')
        file_len = len(file_obj_names)

        file_id_list = await thread_pool_exec(FileService.get_id_list_by_id, pf_id, file_obj_names, 1, [pf_id])
        len_id_list = len(file_id_list)

        if file_len != len_id_list:
            e, file = await thread_pool_exec(FileService.get_by_id, file_id_list[len_id_list - 1])
            if not e:
                return False, "Folder not found!"
            last_folder = await thread_pool_exec(
                FileService.create_folder, file, file_id_list[len_id_list - 1], file_obj_names, len_id_list, tenant_id=folder_tenant_id
            )
        else:
            e, file = await thread_pool_exec(FileService.get_by_id, file_id_list[len_id_list - 2])
            if not e:
                return False, "Folder not found!"
            last_folder = await thread_pool_exec(
                FileService.create_folder, file, file_id_list[len_id_list - 2], file_obj_names, len_id_list, tenant_id=folder_tenant_id
            )

        filetype = filename_type(file_obj_names[file_len - 1])
        location = file_obj_names[file_len - 1]
        while await thread_pool_exec(settings.STORAGE_IMPL.obj_exist, last_folder.id, location):
            location += "_"
        blob = await thread_pool_exec(file_obj.read)
        filename = await thread_pool_exec(
            duplicate_name, FileService.query, name=file_obj_names[file_len - 1], parent_id=last_folder.id
        )
        await thread_pool_exec(settings.STORAGE_IMPL.put, last_folder.id, location, blob)
        file_data = {
            "id": get_uuid(),
            "parent_id": last_folder.id,
            "tenant_id": folder_tenant_id,
            "created_by": user_id,
            "type": filetype,
            "name": filename,
            "location": location,
            "size": len(blob),
        }
        inserted = await thread_pool_exec(FileService.insert, file_data)
        file_res.append(inserted.to_json())

    return True, file_res


async def create_folder(tenant_id: str, name: str, pf_id: str = None, file_type: str = None, user_id: str = None):
    """
    Create a new folder or virtual file.

    :param tenant_id: tenant ID
    :param name: folder name
    :param pf_id: parent folder ID
    :param file_type: file type (folder or virtual)
    :param user_id: user ID (for permission check, defaults to tenant_id)
    :return: (success, result) or (success, error_message)
    """
    if user_id is None:
        user_id = tenant_id

    if not pf_id:
        root_folder = FileService.get_root_folder(tenant_id)
        pf_id = root_folder["id"]

    if not FileService.is_parent_folder_exist(pf_id):
        return False, "Parent Folder Doesn't Exist!"

    # Resolve the parent folder owner's tenant_id for resource attribution.
    # In team sharing scenarios, the current user may be creating a folder
    # in a shared folder owned by another tenant.
    e, pf_folder = FileService.get_by_id(pf_id)
    folder_tenant_id = pf_folder.tenant_id if e and pf_folder else tenant_id

    # Check permission: need EDIT permission on the target folder itself.
    # NOTE: we call check_file_permission(pf_id) directly rather than
    # check_parent_folder_permission(pf_id). The latter looks up pf_folder.parent_id
    # and checks *that* ancestor, but team shares are set on pf_id itself —
    # checking the wrong folder level would always deny team members.
    has_perm, msg = check_file_permission(pf_id, user_id, FilePermissionLevel.EDIT)
    if not has_perm:
        return False, msg or "You don't have permission to create folder in this location."

    if FileService.query(name=name, parent_id=pf_id):
        return False, "Duplicated folder name in the same folder."

    if file_type == FileType.FOLDER.value:
        ft = FileType.FOLDER.value
    else:
        ft = FileType.VIRTUAL.value

    file = FileService.insert({
        "id": get_uuid(),
        "parent_id": pf_id,
        "tenant_id": folder_tenant_id,
        "created_by": user_id,
        "name": name,
        "location": "",
        "size": 0,
        "type": ft,
    })
    return True, file.to_json()


def list_files(tenant_id: str, args: dict, user_id: str = None):
    """
    List files under a folder.

    :param tenant_id: tenant ID (current user's ID from auth)
    :param args: query arguments (parent_id, keywords, page, page_size, orderby, desc)
    :param user_id: user ID (for permission check, defaults to tenant_id)
    :return: (success, result) or (success, error_message)
    """
    from api.db.services.user_service import TenantService

    if user_id is None:
        user_id = tenant_id

    pf_id = args.get("parent_id")
    keywords = args.get("keywords", "")
    page_number = int(args.get("page", 1))
    items_per_page = int(args.get("page_size", 15))
    orderby = args.get("orderby", "create_time")
    desc = args.get("desc", True)

    is_root = not pf_id

    if not pf_id:
        root_folder = FileService.get_root_folder(tenant_id)
        pf_id = root_folder["id"]
        FileService.init_knowledgebase_docs(pf_id, tenant_id)

    e, file = FileService.get_by_id(pf_id)
    if not e:
        return False, "Folder not found!"

    # Check permission: need VIEW permission (uses user_id for cross-tenant share check)
    has_perm, msg = check_file_permission(pf_id, user_id, FilePermissionLevel.VIEW)
    if not has_perm:
        return False, msg or "You don't have permission to view this folder."

    # Use the folder's actual tenant_id for content query (not the current user's tenant_id)
    # This is critical for cross-tenant team sharing: file.tenant_id is the owner's tenant
    folder_tenant_id = file.tenant_id if file else tenant_id
    files, total = FileService.get_by_pf_id(folder_tenant_id, pf_id, page_number, items_per_page, orderby, desc, keywords)

    # When listing the root directory, inject team-shared folders from other tenants
    # that the current user belongs to.
    #
    # In RAGFlow's model, tenant_id from add_tenant_id_to_kwargs is always
    # current_user.id. For a team member (e.g., iwen), their own tenant_id is
    # iwen.id, but they may belong to other tenants (e.g., thomas.id) via the
    # user_tenant table. We need to find those tenants and inject their
    # team-shared files.
    #
    # This mirrors the pattern used in knowledgebase_service.get_list() and
    # canvas_app.py for listing team resources.
    if is_root:
        # Get all tenants this user belongs to (as a normal member, not owner)
        joined_tenants = TenantService.get_joined_tenants_by_user_id(user_id)
        joined_tenant_ids = [t["tenant_id"] for t in joined_tenants]

        for joined_tenant_id in joined_tenant_ids:
            # For each tenant the user is a member of, find team-shared files
            shared_file_ids = TeamPermissionService.get_shared_file_ids_for_user(
                user_id=user_id,
                user_tenant_id=joined_tenant_id
            )
            if shared_file_ids:
                shared_files = _get_shared_folder_details(shared_file_ids)
                # Merge: deduplicate by id (own files take priority)
                own_ids = {f["id"] for f in files}
                extra = [f for f in shared_files if f["id"] not in own_ids]
                files = files + extra
                total += len(extra)

    parent_folder = FileService.get_parent_folder(pf_id)
    if not parent_folder:
        return False, "File not found!"

    return True, {"total": total, "files": files, "parent_folder": parent_folder.to_json()}


def _get_shared_folder_details(file_ids: list) -> list:
    """
    获取共享文件夹的详细信息，并加上标识共享来源的字段。

    返回与 FileService.get_by_pf_id 相同格式的数据，包含:
    - kbs_info: 关联的知识库列表
    - has_child_folder: 是否有子文件夹
    - is_team_shared: 标识这是一个团队共享文件夹
    """
    result = []
    for file_id in file_ids:
        e, file = FileService.get_by_id(file_id)
        if e and file:
            file_dict = file.to_dict()
            # Add kbs_info — same logic as get_by_pf_id
            if file_dict.get("type") == FileType.FOLDER.value:
                file_dict["kbs_info"] = []
                try:
                    file_dict["size"] = FileService.get_folder_size(file_id)
                except Exception:
                    file_dict["size"] = file_dict.get("size", 0)
                # has_child_folder: default False; real value requires DB query which we
                # skip here to avoid N+1 DB roundtrips for the root listing.
                file_dict.setdefault("has_child_folder", False)
            else:
                try:
                    file_dict["kbs_info"] = FileService.get_kb_id_by_file_id(file_id)
                except Exception:
                    file_dict["kbs_info"] = []
                file_dict.setdefault("has_child_folder", False)
            file_dict["is_team_shared"] = True  # mark so frontend can display badge
            result.append(file_dict)
    return result



def get_parent_folder(file_id: str):
    """
    Get parent folder of a file.

    :param file_id: file ID
    :return: (success, result) or (success, error_message)
    """
    e, file = FileService.get_by_id(file_id)
    if not e:
        return False, "Folder not found!"

    parent_folder = FileService.get_parent_folder(file_id)
    return True, {"parent_folder": parent_folder.to_json()}


def get_all_parent_folders(file_id: str):
    """
    Get all ancestor folders of a file.

    :param file_id: file ID
    :return: (success, result) or (success, error_message)
    """
    e, file = FileService.get_by_id(file_id)
    if not e:
        return False, "Folder not found!"

    parent_folders = FileService.get_all_parent_folders(file_id)
    return True, {"parent_folders": [pf.to_json() for pf in parent_folders]}


async def delete_files(uid: str, file_ids: list):
    """
    Delete files/folders with permission check and recursive deletion.

    :param uid: user ID
    :param file_ids: list of file IDs to delete
    :return: (success, result) or (success, error_message)
    """
    def _delete_single_file(file):
        try:
            if file.location:
                settings.STORAGE_IMPL.rm(file.parent_id, file.location)
        except Exception as e:
            logging.exception(f"Fail to remove object: {file.parent_id}/{file.location}, error: {e}")

        informs = File2DocumentService.get_by_file_id(file.id)
        for inform in informs:
            doc_id = inform.document_id
            e, doc = DocumentService.get_by_id(doc_id)
            if e and doc:
                tenant_id = DocumentService.get_tenant_id(doc_id)
                if tenant_id:
                    DocumentService.remove_document(doc, tenant_id)
            File2DocumentService.delete_by_file_id(file.id)

        # Delete file shares
        FilePermissionService.delete_file_shares(file.id)
        FileService.delete(file)

    def _delete_folder_recursive(folder, tenant_id):
        sub_files = FileService.list_all_files_by_parent_id(folder.id)
        for sub_file in sub_files:
            if sub_file.type == FileType.FOLDER.value:
                _delete_folder_recursive(sub_file, tenant_id)
            else:
                _delete_single_file(sub_file)
        # Delete folder shares
        FilePermissionService.delete_file_shares(folder.id)
        FileService.delete(folder)

    def _rm_sync():
        for file_id in file_ids:
            e, file = FileService.get_by_id(file_id)
            if not e or not file:
                return False, "File or Folder not found!"
            if not file.tenant_id:
                return False, "Tenant not found!"

            # Check permission: need ADMIN permission to delete
            has_perm, msg = check_file_operation_permission(file_id, uid, "delete")
            if not has_perm:
                return False, msg or "You don't have permission to delete this file."

            # Also check team permission as fallback
            if not check_file_team_permission(file, uid):
                return False, "No authorization."

            if file.source_type == FileSource.KNOWLEDGEBASE:
                continue

            if file.type == FileType.FOLDER.value:
                _delete_folder_recursive(file, uid)
                continue

            _delete_single_file(file)

        return True, True

    return await thread_pool_exec(_rm_sync)


async def move_files(uid: str, src_file_ids: list, dest_file_id: str = None, new_name: str = None):
    """
    Move and/or rename files. Follows Linux mv semantics:
    - new_name only: rename in place (no storage operation)
    - dest_file_id only: move to new folder (keep names)
    - both: move and rename simultaneously

    :param uid: user ID
    :param src_file_ids: list of source file IDs
    :param dest_file_id: destination folder ID (optional)
    :param new_name: new name for the file (optional, single file only)
    :return: (success, result) or (success, error_message)
    """
    files = FileService.get_by_ids(src_file_ids)
    if not files:
        return False, "Source files not found!"

    files_dict = {f.id: f for f in files}

    # Check permission for each source file (need ADMIN permission)
    for file_id in src_file_ids:
        file = files_dict.get(file_id)
        if not file:
            return False, "File or folder not found!"
        if not file.tenant_id:
            return False, "Tenant not found!"

        has_perm, msg = check_file_operation_permission(file_id, uid, "move")
        if not has_perm:
            return False, msg or "You don't have permission to move this file."

    # Check permission for destination folder (need EDIT permission)
    dest_folder = None
    if dest_file_id:
        ok, dest_folder = FileService.get_by_id(dest_file_id)
        if not ok or not dest_folder:
            return False, "Parent folder not found!"

        has_perm, msg = check_file_permission(dest_file_id, uid, FilePermissionLevel.EDIT)
        if not has_perm:
            return False, msg or "You don't have permission to move files to this folder."

    if new_name:
        file = files_dict[src_file_ids[0]]
        if file.type != FileType.FOLDER.value and \
                pathlib.Path(new_name.lower()).suffix != pathlib.Path(file.name.lower()).suffix:
            return False, "The extension of file can't be changed"
        target_parent_id = dest_folder.id if dest_folder else file.parent_id
        for f in FileService.query(name=new_name, parent_id=target_parent_id):
            if f.name == new_name:
                return False, "Duplicated file name in the same folder."

    def _move_entry_recursive(source_file_entry, dest_folder_entry, override_name=None):
        effective_name = override_name or source_file_entry.name

        if source_file_entry.type == FileType.FOLDER.value:
            existing_folder = FileService.query(name=effective_name, parent_id=dest_folder_entry.id)
            if existing_folder:
                new_folder = existing_folder[0]
            else:
                new_folder = FileService.insert({
                    "id": get_uuid(),
                    "parent_id": dest_folder_entry.id,
                    "tenant_id": source_file_entry.tenant_id,
                    "created_by": source_file_entry.tenant_id,
                    "name": effective_name,
                    "location": "",
                    "size": 0,
                    "type": FileType.FOLDER.value,
                })

            sub_files = FileService.list_all_files_by_parent_id(source_file_entry.id)
            for sub_file in sub_files:
                _move_entry_recursive(sub_file, new_folder)

            FileService.delete_by_id(source_file_entry.id)
            return

        # Non-folder file
        need_storage_move = dest_folder_entry.id != source_file_entry.parent_id
        updates = {}

        if need_storage_move:
            new_location = effective_name
            while settings.STORAGE_IMPL.obj_exist(dest_folder_entry.id, new_location):
                new_location += "_"
            try:
                settings.STORAGE_IMPL.move(
                    source_file_entry.parent_id, source_file_entry.location,
                    dest_folder_entry.id, new_location,
                )
            except Exception as storage_err:
                raise RuntimeError(f"Move file failed at storage layer: {str(storage_err)}")
            updates["parent_id"] = dest_folder_entry.id
            updates["location"] = new_location

        if override_name:
            updates["name"] = override_name

        if updates:
            FileService.update_by_id(source_file_entry.id, updates)

        if override_name:
            informs = File2DocumentService.get_by_file_id(source_file_entry.id)
            if informs:
                if not DocumentService.update_by_id(informs[0].document_id, {"name": override_name}):
                    raise RuntimeError("Database error (Document rename)!")

    def _move_or_rename_sync():
        if dest_folder:
            for file in files:
                _move_entry_recursive(file, dest_folder, override_name=new_name)
        else:
            # Pure rename: no storage operation needed
            file = files[0]
            if not FileService.update_by_id(file.id, {"name": new_name}):
                return False, "Database error (File rename)!"
            informs = File2DocumentService.get_by_file_id(file.id)
            if informs:
                if not DocumentService.update_by_id(informs[0].document_id, {"name": new_name}):
                    return False, "Database error (Document rename)!"
        return True, True

    return await thread_pool_exec(_move_or_rename_sync)


def get_file_content(uid: str, file_id: str):
    """
    Get file content and metadata for download.

    :param uid: user ID
    :param file_id: file ID
    :return: (success, file_obj) or (success, error_message)
    """
    e, file = FileService.get_by_id(file_id)
    if not e:
        return False, "Document not found!"

    # Check permission: need VIEW permission
    has_perm, msg = check_file_permission(file_id, uid, FilePermissionLevel.VIEW)
    if not has_perm:
        return False, msg or "You don't have permission to access this file."

    return True, file
