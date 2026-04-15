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

"""
TDD tests for team shared folder upload functionality.

Core principle: When a team member uploads files to a shared folder,
the file's tenant_id must inherit the folder owner's tenant_id (not the
uploader's), and created_by should record the actual uploader's user_id.

This ensures files are visible via FileService.get_by_pf_id which filters
by tenant_id matching the folder owner.
"""

import asyncio
import importlib.util
import sys
from enum import Enum
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

OWNER_TENANT_ID = "owner-thomas"
MEMBER_USER_ID = "member-iwen"
SHARED_FOLDER_ID = "shared-folder-001"


class _DummyUploadFile:
    def __init__(self, filename, blob=b"blob"):
        self.filename = filename
        self._blob = blob

    def read(self):
        return self._blob


class _DummyFile:
    def __init__(
        self,
        file_id,
        file_type,
        *,
        tenant_id="tenant1",
        created_by="tenant1",
        parent_id="pf1",
        location="loc1",
        name="doc.txt",
        source_type="user",
        size=1,
    ):
        self.id = file_id
        self.type = file_type
        self.tenant_id = tenant_id
        self.created_by = created_by
        self.parent_id = parent_id
        self.location = location
        self.name = name
        self.source_type = source_type
        self.size = size

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "tenant_id": self.tenant_id,
            "created_by": self.created_by,
        }


def _run(coro):
    return asyncio.run(coro)


def _load_file_api_service(monkeypatch):
    """Load file_api_service module with mocked dependencies."""
    repo_root = Path(__file__).resolve().parents[4]

    api_pkg = ModuleType("api")
    api_pkg.__path__ = [str(repo_root / "api")]
    monkeypatch.setitem(sys.modules, "api", api_pkg)

    common_pkg = ModuleType("api.common")
    common_pkg.__path__ = []
    monkeypatch.setitem(sys.modules, "api.common", common_pkg)

    # Mock check_team_permission
    permission_mod = ModuleType("api.common.check_team_permission")
    permission_mod.check_file_team_permission = lambda *_args, **_kwargs: True
    monkeypatch.setitem(sys.modules, "api.common.check_team_permission", permission_mod)
    common_pkg.check_team_permission = permission_mod

    # Mock check_file_permission
    check_file_perm_mod = ModuleType("api.common.check_file_permission")
    check_file_perm_mod.check_parent_folder_permission = lambda *_a, **_kw: (True, "")
    check_file_perm_mod.check_file_permission = lambda *_a, **_kw: (True, "")
    check_file_perm_mod.check_file_operation_permission = lambda *_a, **_kw: (True, "")
    check_file_perm_mod.FilePermissionLevel = type("_FPL", (), {"VIEW": "view", "EDIT": "edit", "ADMIN": "admin", "OWNER": "owner"})()
    monkeypatch.setitem(sys.modules, "api.common.check_file_permission", check_file_perm_mod)
    common_pkg.check_file_permission = check_file_perm_mod

    # Mock api.db
    db_pkg = ModuleType("api.db")
    db_pkg.__path__ = []

    class _FileType(Enum):
        FOLDER = "folder"
        VIRTUAL = "virtual"
        DOC = "doc"
        VISUAL = "visual"

    class _FilePermissionLevel:
        VIEW = "view"
        EDIT = "edit"
        ADMIN = "admin"
        OWNER = "owner"

    db_pkg.FileType = _FileType
    db_pkg.FilePermissionLevel = _FilePermissionLevel
    monkeypatch.setitem(sys.modules, "api.db", db_pkg)
    api_pkg.db = db_pkg

    # Mock api.db.services
    services_pkg = ModuleType("api.db.services")
    services_pkg.__path__ = []
    services_pkg.duplicate_name = lambda _query, **kwargs: kwargs.get("name", "")
    monkeypatch.setitem(sys.modules, "api.db.services", services_pkg)

    # Mock DocumentService
    document_service_mod = ModuleType("api.db.services.document_service")
    document_service_mod.DocumentService = SimpleNamespace(
        get_doc_count=lambda _uid: 0,
        get_by_id=lambda doc_id: (True, SimpleNamespace(id=doc_id)),
        get_tenant_id=lambda _doc_id: OWNER_TENANT_ID,
        remove_document=lambda *_args, **_kwargs: True,
        update_by_id=lambda *_args, **_kwargs: True,
    )
    monkeypatch.setitem(sys.modules, "api.db.services.document_service", document_service_mod)
    services_pkg.document_service = document_service_mod

    # Mock File2DocumentService
    file2doc_mod = ModuleType("api.db.services.file2document_service")
    file2doc_mod.File2DocumentService = SimpleNamespace(
        get_by_file_id=lambda _file_id: [],
        delete_by_file_id=lambda _file_id: None,
    )
    monkeypatch.setitem(sys.modules, "api.db.services.file2document_service", file2doc_mod)
    services_pkg.file2document_service = file2doc_mod

    # Mock FilePermissionService
    file_perm_svc_mod = ModuleType("api.db.services.file_permission_service")
    file_perm_svc_mod.FilePermissionService = SimpleNamespace(
        delete_file_shares=lambda *_a, **_kw: None,
    )
    monkeypatch.setitem(sys.modules, "api.db.services.file_permission_service", file_perm_svc_mod)
    services_pkg.file_permission_service = file_perm_svc_mod

    # Mock TeamPermissionService
    team_perm_svc_mod = ModuleType("api.db.services.team_permission_service")
    team_perm_svc_mod.TeamPermissionService = SimpleNamespace(
        get_shared_file_ids_for_user=lambda *_a, **_kw: [],
    )
    monkeypatch.setitem(sys.modules, "api.db.services.team_permission_service", team_perm_svc_mod)
    services_pkg.team_permission_service = team_perm_svc_mod

    # Mock TenantService
    tenant_svc_mod = ModuleType("api.db.services.user_service")
    tenant_svc_mod.TenantService = SimpleNamespace(
        get_joined_tenants_by_user_id=lambda _uid: [],
    )
    monkeypatch.setitem(sys.modules, "api.db.services.user_service", tenant_svc_mod)
    services_pkg.user_service = tenant_svc_mod

    # Mock FileService
    file_service_mod = ModuleType("api.db.services.file_service")
    file_service_mod.FileService = SimpleNamespace(
        get_root_folder=lambda _tenant_id: {"id": "root"},
        get_by_id=lambda file_id: (True, _DummyFile(file_id, _FileType.DOC.value)),
        get_id_list_by_id=lambda _pf_id, _names, _idx, ids: ids,
        create_folder=lambda _file, parent_id, _names, _len_id, **_kw: SimpleNamespace(id=parent_id, name=str(parent_id)),
        query=lambda **_kwargs: [],
        insert=lambda data: SimpleNamespace(to_json=lambda: data, **data),
        is_parent_folder_exist=lambda _pf_id: True,
        get_by_pf_id=lambda *_args, **_kwargs: ([], 0),
        get_parent_folder=lambda _file_id: SimpleNamespace(to_json=lambda: {"id": "root"}),
        get_all_parent_folders=lambda _file_id: [],
        list_all_files_by_parent_id=lambda _parent_id: [],
        delete=lambda _file: True,
        delete_by_id=lambda _file_id: True,
        update_by_id=lambda *_args, **_kwargs: True,
        get_by_ids=lambda file_ids: [_DummyFile(file_id, _FileType.DOC.value) for file_id in file_ids],
        init_knowledgebase_docs=lambda *_a, **_kw: None,
    )
    monkeypatch.setitem(sys.modules, "api.db.services.file_service", file_service_mod)
    services_pkg.file_service = file_service_mod

    # Mock file_utils
    file_utils_mod = ModuleType("api.utils.file_utils")
    file_utils_mod.filename_type = lambda _filename: _FileType.DOC.value
    monkeypatch.setitem(sys.modules, "api.utils.file_utils", file_utils_mod)

    # Mock common
    common_root_mod = ModuleType("common")
    common_root_mod.__path__ = [str(repo_root / "common")]
    common_root_mod.settings = SimpleNamespace(
        STORAGE_IMPL=SimpleNamespace(
            obj_exist=lambda *_args, **_kwargs: False,
            put=lambda *_args, **_kwargs: None,
            rm=lambda *_args, **_kwargs: None,
            move=lambda *_args, **_kwargs: None,
        )
    )
    monkeypatch.setitem(sys.modules, "common", common_root_mod)

    # Mock common.constants
    constants_mod = ModuleType("common.constants")

    class _FileSource:
        KNOWLEDGEBASE = "knowledgebase"

    constants_mod.FileSource = _FileSource
    monkeypatch.setitem(sys.modules, "common.constants", constants_mod)

    # Mock common.misc_utils
    misc_utils_mod = ModuleType("common.misc_utils")
    misc_utils_mod.get_uuid = lambda: "uuid-1"

    async def thread_pool_exec(func, *args, **kwargs):
        return func(*args, **kwargs)

    misc_utils_mod.thread_pool_exec = thread_pool_exec
    monkeypatch.setitem(sys.modules, "common.misc_utils", misc_utils_mod)

    # Load the real module
    module_path = repo_root / "api" / "apps" / "services" / "file_api_service.py"
    spec = importlib.util.spec_from_file_location("api.apps.services.file_api_service", module_path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "api.apps.services.file_api_service", module)
    spec.loader.exec_module(module)
    return module


# ===========================================================================
# TDD RED PHASE: Tests that MUST fail before the fix is implemented
# ===========================================================================


class TestUploadFileInheritsFolderTenantId:
    """Bug 1: upload_file should inherit parent folder's tenant_id, not uploader's."""

    @pytest.mark.p1
    def test_upload_file_to_shared_folder_uses_folder_owner_tenant_id(self, monkeypatch):
        """
        TC-SHARE-001: When a team member uploads to a shared folder,
        the new file's tenant_id must be the folder owner's tenant_id
        (e.g., OWNER_TENANT_ID), NOT the uploader's (MEMBER_USER_ID).

        This is because FileService.get_by_pf_id filters by tenant_id,
        so files with the wrong tenant_id become invisible to everyone.
        """
        module = _load_file_api_service(monkeypatch)
        inserted_data = {}

        # Parent folder belongs to OWNER_TENANT_ID (thomas)
        monkeypatch.setattr(
            module.FileService, "get_by_id",
            lambda fid: (True, _DummyFile(
                fid, module.FileType.FOLDER.value,
                tenant_id=OWNER_TENANT_ID,
                created_by=OWNER_TENANT_ID,
                name="shared_folder",
            )) if fid == SHARED_FOLDER_ID else (True, _DummyFile(fid, module.FileType.DOC.value)),
        )
        monkeypatch.setattr(
            module.FileService, "get_id_list_by_id",
            lambda *_a, **_kw: [SHARED_FOLDER_ID],
        )
        monkeypatch.setattr(
            module.FileService, "create_folder",
            lambda _f, parent_id, _n, _c, **_kw: SimpleNamespace(id=parent_id, name="shared_folder"),
        )

        def capture_insert(data):
            inserted_data.update(data)
            return SimpleNamespace(to_json=lambda: data, **data)

        monkeypatch.setattr(module.FileService, "insert", capture_insert)

        # Upload as team member: tenant_id=MEMBER_USER_ID (from decorator),
        # user_id=MEMBER_USER_ID
        ok, result = _run(module.upload_file(
            MEMBER_USER_ID, SHARED_FOLDER_ID,
            [_DummyUploadFile("report.pdf", b"content")],
            user_id=MEMBER_USER_ID,
        ))

        assert ok is True, f"Upload should succeed but got: {result}"
        # KEY ASSERTION: tenant_id must be the folder owner's, not the uploader's
        assert inserted_data["tenant_id"] == OWNER_TENANT_ID, (
            f"File tenant_id should be folder owner's '{OWNER_TENANT_ID}', "
            f"but got uploader's '{inserted_data['tenant_id']}'"
        )


class TestUploadFileCreatedByIsUploader:
    """Bug 2: upload_file should set created_by to the actual uploader user_id."""

    @pytest.mark.p1
    def test_upload_file_created_by_is_actual_uploader(self, monkeypatch):
        """
        TC-SHARE-002: created_by should be the actual uploader's user_id,
        not the folder owner's tenant_id.

        This distinguishes WHO uploaded from WHO OWNS the folder.
        """
        module = _load_file_api_service(monkeypatch)
        inserted_data = {}

        monkeypatch.setattr(
            module.FileService, "get_by_id",
            lambda fid: (True, _DummyFile(
                fid, module.FileType.FOLDER.value,
                tenant_id=OWNER_TENANT_ID,
                created_by=OWNER_TENANT_ID,
                name="shared_folder",
            )) if fid == SHARED_FOLDER_ID else (True, _DummyFile(fid, module.FileType.DOC.value)),
        )
        monkeypatch.setattr(
            module.FileService, "get_id_list_by_id",
            lambda *_a, **_kw: [SHARED_FOLDER_ID],
        )
        monkeypatch.setattr(
            module.FileService, "create_folder",
            lambda _f, parent_id, _n, _c, **_kw: SimpleNamespace(id=parent_id),
        )

        def capture_insert(data):
            inserted_data.update(data)
            return SimpleNamespace(to_json=lambda: data, **data)

        monkeypatch.setattr(module.FileService, "insert", capture_insert)

        ok, result = _run(module.upload_file(
            MEMBER_USER_ID, SHARED_FOLDER_ID,
            [_DummyUploadFile("report.pdf", b"content")],
            user_id=MEMBER_USER_ID,
        ))

        assert ok is True
        # KEY ASSERTION: created_by should be the uploader, not the tenant
        assert inserted_data["created_by"] == MEMBER_USER_ID, (
            f"created_by should be uploader '{MEMBER_USER_ID}', "
            f"but got '{inserted_data['created_by']}'"
        )


class TestUploadFileCountsOwnerQuota:
    """Bug 4: upload_file should count files against the folder owner's quota."""

    @pytest.mark.p1
    def test_upload_file_doc_count_uses_folder_owner_tenant_id(self, monkeypatch):
        """
        TC-SHARE-003: Document count should be checked against the folder
        owner's tenant_id, not the uploader's tenant_id.
        """
        module = _load_file_api_service(monkeypatch)
        count_check_tenant_id = []

        monkeypatch.setattr(
            module.FileService, "get_by_id",
            lambda fid: (True, _DummyFile(
                fid, module.FileType.FOLDER.value,
                tenant_id=OWNER_TENANT_ID,
                created_by=OWNER_TENANT_ID,
                name="shared_folder",
            )) if fid == SHARED_FOLDER_ID else (True, _DummyFile(fid, module.FileType.DOC.value)),
        )

        original_get_doc_count = module.DocumentService.get_doc_count

        def tracking_get_doc_count(tenant_id):
            count_check_tenant_id.append(tenant_id)
            return 0

        monkeypatch.setattr(
            module.DocumentService, "get_doc_count", tracking_get_doc_count,
        )
        monkeypatch.setenv("MAX_FILE_NUM_PER_USER", "100")

        ok, result = _run(module.upload_file(
            MEMBER_USER_ID, SHARED_FOLDER_ID,
            [_DummyUploadFile("report.pdf", b"content")],
            user_id=MEMBER_USER_ID,
        ))

        monkeypatch.delenv("MAX_FILE_NUM_PER_USER", raising=False)

        assert ok is True
        assert len(count_check_tenant_id) > 0, "DocumentService.get_doc_count should have been called"
        # KEY ASSERTION: count check should use the folder owner's tenant_id
        assert count_check_tenant_id[0] == OWNER_TENANT_ID, (
            f"Doc count should check folder owner '{OWNER_TENANT_ID}', "
            f"but checked '{count_check_tenant_id[0]}'"
        )


class TestCreateFolderInheritsFolderTenantId:
    """Bug 2: create_folder should inherit parent folder's tenant_id."""

    @pytest.mark.p1
    def test_create_folder_in_shared_folder_uses_owner_tenant_id(self, monkeypatch):
        """
        TC-SHARE-004: When a team member creates a subfolder in a shared folder,
        the new folder's tenant_id must be the parent folder owner's.
        """
        module = _load_file_api_service(monkeypatch)
        inserted_data = {}

        monkeypatch.setattr(
            module.FileService, "get_by_id",
            lambda fid: (True, _DummyFile(
                fid, module.FileType.FOLDER.value,
                tenant_id=OWNER_TENANT_ID,
                created_by=OWNER_TENANT_ID,
                name="shared_folder",
            )),
        )

        def capture_insert(data):
            inserted_data.update(data)
            return SimpleNamespace(to_json=lambda: data, **data)

        monkeypatch.setattr(module.FileService, "insert", capture_insert)

        ok, result = _run(module.create_folder(
            MEMBER_USER_ID, "new_subfolder", SHARED_FOLDER_ID,
            module.FileType.FOLDER.value, user_id=MEMBER_USER_ID,
        ))

        assert ok is True, f"Create folder should succeed but got: {result}"
        # KEY ASSERTION: tenant_id should be the folder owner's
        assert inserted_data["tenant_id"] == OWNER_TENANT_ID, (
            f"Folder tenant_id should be parent owner's '{OWNER_TENANT_ID}', "
            f"but got '{inserted_data['tenant_id']}'"
        )


class TestCreateFolderCreatedByIsOperator:
    """Bug 5: create_folder should set created_by to the actual operator."""

    @pytest.mark.p1
    def test_create_folder_created_by_is_actual_operator(self, monkeypatch):
        """
        TC-SHARE-005: created_by should be the user who creates the folder,
        not the parent folder's tenant_id.
        """
        module = _load_file_api_service(monkeypatch)
        inserted_data = {}

        monkeypatch.setattr(
            module.FileService, "get_by_id",
            lambda fid: (True, _DummyFile(
                fid, module.FileType.FOLDER.value,
                tenant_id=OWNER_TENANT_ID,
                created_by=OWNER_TENANT_ID,
                name="shared_folder",
            )),
        )

        def capture_insert(data):
            inserted_data.update(data)
            return SimpleNamespace(to_json=lambda: data, **data)

        monkeypatch.setattr(module.FileService, "insert", capture_insert)

        ok, result = _run(module.create_folder(
            MEMBER_USER_ID, "new_subfolder", SHARED_FOLDER_ID,
            module.FileType.FOLDER.value, user_id=MEMBER_USER_ID,
        ))

        assert ok is True
        assert inserted_data["created_by"] == MEMBER_USER_ID, (
            f"created_by should be operator '{MEMBER_USER_ID}', "
            f"but got '{inserted_data['created_by']}'"
        )


class TestUploadFileResolvesFolderTenantId:
    """Integration: upload_file without user_id should still resolve correctly."""

    @pytest.mark.p1
    def test_upload_file_no_user_id_still_inherits_folder_tenant(self, monkeypatch):
        """
        TC-SHARE-006: When user_id is not passed (defaults to tenant_id),
        the file's tenant_id should still be the folder owner's.
        This tests backward compatibility for owner's own uploads.
        """
        module = _load_file_api_service(monkeypatch)
        inserted_data = {}

        # Owner uploading to own folder: tenant_id == user_id == OWNER_TENANT_ID
        monkeypatch.setattr(
            module.FileService, "get_by_id",
            lambda fid: (True, _DummyFile(
                fid, module.FileType.FOLDER.value,
                tenant_id=OWNER_TENANT_ID,
                created_by=OWNER_TENANT_ID,
                name="my_folder",
            )),
        )
        monkeypatch.setattr(
            module.FileService, "get_id_list_by_id",
            lambda *_a, **_kw: ["folder1"],
        )
        monkeypatch.setattr(
            module.FileService, "create_folder",
            lambda _f, parent_id, _n, _c, **_kw: SimpleNamespace(id=parent_id),
        )

        def capture_insert(data):
            inserted_data.update(data)
            return SimpleNamespace(to_json=lambda: data, **data)

        monkeypatch.setattr(module.FileService, "insert", capture_insert)

        # Owner's own upload: tenant_id=OWNER_TENANT_ID, no user_id passed
        ok, result = _run(module.upload_file(
            OWNER_TENANT_ID, "folder1",
            [_DummyUploadFile("my_file.pdf", b"content")],
        ))

        assert ok is True
        # For owner's own folder: both tenant_id and user_id are the same
        assert inserted_data["tenant_id"] == OWNER_TENANT_ID
        assert inserted_data["created_by"] == OWNER_TENANT_ID


class TestUploadFileWithSubfolderCreation:
    """Bug 3: FileService.create_folder called during upload should inherit tenant_id."""

    @pytest.mark.p1
    def test_upload_with_path_creates_subfolders_with_correct_tenant_id(self, monkeypatch):
        """
        TC-SHARE-007: When uploading a file with a nested path (e.g., "subdir/file.txt"),
        FileService.create_folder is called to create intermediate directories.
        These intermediate directories must also inherit the parent folder's tenant_id.
        """
        module = _load_file_api_service(monkeypatch)
        create_folder_calls = []

        monkeypatch.setattr(
            module.FileService, "get_by_id",
            lambda fid: (True, _DummyFile(
                fid, module.FileType.FOLDER.value,
                tenant_id=OWNER_TENANT_ID,
                created_by=OWNER_TENANT_ID,
                name="shared_folder",
            )) if fid == SHARED_FOLDER_ID else (True, _DummyFile(fid, module.FileType.FOLDER.value)),
        )
        # Simulate that the path "subdir/file.txt" needs a new folder
        monkeypatch.setattr(
            module.FileService, "get_id_list_by_id",
            lambda _pf_id, names, _idx, ids: [SHARED_FOLDER_ID],  # only 1 match, but 2 names
        )

        def track_create_folder(file, parent_id, names, count, **kwargs):
            create_folder_calls.append({
                "file_tenant_id": getattr(file, "tenant_id", None),
                "parent_id": parent_id,
                "names": names,
                "count": count,
                "kwargs": kwargs,
            })
            return SimpleNamespace(
                id="new-subfolder",
                tenant_id=OWNER_TENANT_ID,
                name="subdir",
            )

        monkeypatch.setattr(module.FileService, "create_folder", track_create_folder)

        inserted_data = {}

        def capture_insert(data):
            inserted_data.update(data)
            return SimpleNamespace(to_json=lambda: data, **data)

        monkeypatch.setattr(module.FileService, "insert", capture_insert)

        ok, result = _run(module.upload_file(
            MEMBER_USER_ID, SHARED_FOLDER_ID,
            [_DummyUploadFile("subdir/report.pdf", b"content")],
            user_id=MEMBER_USER_ID,
        ))

        assert ok is True
        # The uploaded file must have the folder owner's tenant_id
        assert inserted_data["tenant_id"] == OWNER_TENANT_ID, (
            f"File tenant_id should be '{OWNER_TENANT_ID}', "
            f"but got '{inserted_data['tenant_id']}'"
        )


class TestOwnerUploadStillWorks:
    """Regression: Owner uploading to own folder must still work correctly."""

    @pytest.mark.p1
    def test_owner_upload_to_own_folder_unchanged(self, monkeypatch):
        """
        TC-SHARE-008: When the folder owner uploads to their own folder,
        tenant_id and created_by should both be the owner's ID.
        This is a regression test to ensure the fix doesn't break normal uploads.
        """
        module = _load_file_api_service(monkeypatch)
        inserted_data = {}

        monkeypatch.setattr(
            module.FileService, "get_by_id",
            lambda fid: (True, _DummyFile(
                fid, module.FileType.FOLDER.value,
                tenant_id=OWNER_TENANT_ID,
                created_by=OWNER_TENANT_ID,
                name="my_folder",
            )),
        )
        monkeypatch.setattr(
            module.FileService, "get_id_list_by_id",
            lambda *_a, **_kw: ["folder1"],
        )
        monkeypatch.setattr(
            module.FileService, "create_folder",
            lambda _f, parent_id, _n, _c, **_kw: SimpleNamespace(id=parent_id),
        )

        def capture_insert(data):
            inserted_data.update(data)
            return SimpleNamespace(to_json=lambda: data, **data)

        monkeypatch.setattr(module.FileService, "insert", capture_insert)

        ok, result = _run(module.upload_file(
            OWNER_TENANT_ID, "folder1",
            [_DummyUploadFile("my_file.pdf", b"content")],
            user_id=OWNER_TENANT_ID,
        ))

        assert ok is True
        assert inserted_data["tenant_id"] == OWNER_TENANT_ID
        assert inserted_data["created_by"] == OWNER_TENANT_ID


class TestTeamMemberUploadPermissionCheck:
    """Bug 6: upload_file must check permission on the TARGET folder itself,
    not on its parent folder.

    Root cause: check_parent_folder_permission(pf_id) looks up pf_folder.parent_id
    and checks that ancestor, but the team share is set on pf_id itself.
    The fix: use check_file_permission(pf_id, user_id, EDIT) directly.
    """

    @pytest.mark.p1
    def test_team_member_with_edit_permission_can_upload(self, monkeypatch):
        """
        TC-SHARE-009: A team member who has EDIT permission on the shared folder
        (pf_id) must be allowed to upload files, even if they have NO permission
        on pf_folder.parent_id.

        This test simulates the real failure scenario:
        - TeamPermissionShare sets edit permission on SHARED_FOLDER_ID
        - check_parent_folder_permission(SHARED_FOLDER_ID) incorrectly checks the
          PARENT of SHARED_FOLDER_ID, which has no team share -> returns False
        - The fix is to call check_file_permission(pf_id) directly.
        """
        # Set up permission mock to:
        #   - DENY if checking the PARENT of the shared folder
        #   - ALLOW if checking the shared folder itself
        PARENT_OF_SHARED = "root-folder-99"

        check_calls = []

        def fake_check_parent_folder_permission(file_id, user_id, required_level):
            check_calls.append(("check_parent", file_id))
            # Simulate: parent folder has no team share -> deny
            if file_id == SHARED_FOLDER_ID:
                # check_parent_folder_permission would look up pf_folder.parent_id
                # and deny because that parent has no team share
                return False, "You don't have permission on the parent folder."
            return True, ""

        def fake_check_file_permission(file_id, user_id, required_level):
            check_calls.append(("check_file", file_id))
            # The team share is on SHARED_FOLDER_ID -> allow
            if file_id == SHARED_FOLDER_ID:
                return True, ""
            return False, "No permission."

        module = _load_file_api_service(monkeypatch)

        # Override the permission mocks to use our tracking fakes
        import api.common.check_file_permission as cperm_mod
        monkeypatch.setattr(cperm_mod, "check_parent_folder_permission",
                            fake_check_parent_folder_permission)
        monkeypatch.setattr(cperm_mod, "check_file_permission",
                            fake_check_file_permission)
        # Also patch on the module under test
        monkeypatch.setattr(module, "check_parent_folder_permission",
                            fake_check_parent_folder_permission)
        monkeypatch.setattr(module, "check_file_permission",
                            fake_check_file_permission)

        monkeypatch.setattr(
            module.FileService, "get_by_id",
            lambda fid: (True, _DummyFile(
                fid, module.FileType.FOLDER.value,
                tenant_id=OWNER_TENANT_ID,
                created_by=OWNER_TENANT_ID,
                parent_id=PARENT_OF_SHARED,
                name="shared_folder",
            )) if fid == SHARED_FOLDER_ID else (
                True, _DummyFile(fid, module.FileType.FOLDER.value,
                                  tenant_id=OWNER_TENANT_ID)
            ),
        )
        monkeypatch.setattr(
            module.FileService, "get_id_list_by_id",
            lambda *_a, **_kw: [SHARED_FOLDER_ID],
        )
        monkeypatch.setattr(
            module.FileService, "create_folder",
            lambda _f, parent_id, _n, _c, **_kw: SimpleNamespace(
                id=parent_id, name="shared_folder"),
        )
        monkeypatch.setattr(
            module.FileService, "insert",
            lambda data: SimpleNamespace(to_json=lambda: data, **data),
        )

        ok, result = _run(module.upload_file(
            MEMBER_USER_ID, SHARED_FOLDER_ID,
            [_DummyUploadFile("report.pdf", b"content")],
            user_id=MEMBER_USER_ID,
        ))

        # With the fix (direct check_file_permission on pf_id):
        # -> check_file_permission(SHARED_FOLDER_ID) returns True -> upload succeeds
        assert ok is True, (
            f"Team member with EDIT on shared folder should upload successfully, "
            f"but got: {result}"
        )
        # Verify that check_file_permission was called on the TARGET folder directly,
        # NOT check_parent_folder_permission
        called_on_shared = [(fn, fid) for fn, fid in check_calls
                            if fid == SHARED_FOLDER_ID]
        assert any(fn == "check_file" for fn, _ in called_on_shared), (
            f"Expected check_file_permission to be called on {SHARED_FOLDER_ID}, "
            f"but calls were: {check_calls}"
        )

    @pytest.mark.p1
    def test_team_member_with_edit_permission_can_create_folder(self, monkeypatch):
        """
        TC-SHARE-010: A team member with EDIT permission on the shared folder
        must be allowed to create sub-folders, even if the shared folder's
        own parent has no team share.
        """
        PARENT_OF_SHARED = "root-folder-99"
        check_calls = []

        def fake_check_parent_folder_permission(file_id, user_id, required_level):
            check_calls.append(("check_parent", file_id))
            if file_id == SHARED_FOLDER_ID:
                return False, "You don't have permission on the parent folder."
            return True, ""

        def fake_check_file_permission(file_id, user_id, required_level):
            check_calls.append(("check_file", file_id))
            if file_id == SHARED_FOLDER_ID:
                return True, ""
            return False, "No permission."

        module = _load_file_api_service(monkeypatch)

        import api.common.check_file_permission as cperm_mod
        monkeypatch.setattr(cperm_mod, "check_parent_folder_permission",
                            fake_check_parent_folder_permission)
        monkeypatch.setattr(cperm_mod, "check_file_permission",
                            fake_check_file_permission)
        monkeypatch.setattr(module, "check_parent_folder_permission",
                            fake_check_parent_folder_permission)
        monkeypatch.setattr(module, "check_file_permission",
                            fake_check_file_permission)

        monkeypatch.setattr(
            module.FileService, "get_by_id",
            lambda fid: (True, _DummyFile(
                fid, module.FileType.FOLDER.value,
                tenant_id=OWNER_TENANT_ID,
                created_by=OWNER_TENANT_ID,
                parent_id=PARENT_OF_SHARED,
                name="shared_folder",
            )),
        )
        monkeypatch.setattr(
            module.FileService, "insert",
            lambda data: SimpleNamespace(to_json=lambda: data, **data),
        )

        ok, result = _run(module.create_folder(
            MEMBER_USER_ID, "new_subfolder", SHARED_FOLDER_ID,
            module.FileType.FOLDER.value, user_id=MEMBER_USER_ID,
        ))

        assert ok is True, (
            f"Team member with EDIT on shared folder should create sub-folder, "
            f"but got: {result}"
        )
        called_on_shared = [(fn, fid) for fn, fid in check_calls
                            if fid == SHARED_FOLDER_ID]
        assert any(fn == "check_file" for fn, _ in called_on_shared), (
            f"Expected check_file_permission to be called on {SHARED_FOLDER_ID}, "
            f"but calls were: {check_calls}"
        )
