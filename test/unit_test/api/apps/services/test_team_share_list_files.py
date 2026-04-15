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
Unit tests for team shared folder listing functionality.

TDD RED PHASE: These tests verify the integration of:
1. TenantService.get_joined_tenants_by_user_id - find user's tenants
2. TeamPermissionService.get_shared_file_ids_for_user - find shared folders
3. file_api_service.list_files - inject shared folders into root listing

Run with: uv run pytest test/unit_test/api/apps/services/test_team_share_list_files.py -v
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


# ---------------------------------------------------------------------------
# Test constants
# ---------------------------------------------------------------------------

OWNER_TENANT_ID = "owner-thomas"
MEMBER_USER_ID = "member-iwen"
SHARED_FOLDER_ID = "shared-folder-001"
OWNER_ROOT_FOLDER_ID = "owner-root-001"
MEMBER_ROOT_FOLDER_ID = "member-root-001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _DummyFile:
    """Minimal file object for testing."""
    def __init__(
        self,
        file_id,
        file_type="folder",
        *,
        tenant_id="tenant1",
        created_by="tenant1",
        parent_id=None,
        name="test_folder",
        size=0,
    ):
        self.id = file_id
        self.type = file_type
        self.tenant_id = tenant_id
        self.created_by = created_by
        self.parent_id = parent_id
        self.name = name
        self.size = size

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "tenant_id": self.tenant_id,
            "created_by": self.created_by,
            "parent_id": self.parent_id,
            "size": self.size,
        }

    def to_json(self):
        return self.to_dict()


def _create_mock_modules(monkeypatch, repo_root):
    """Create minimal mock modules for isolated unit testing."""
    # api package
    api_pkg = ModuleType("api")
    api_pkg.__path__ = [str(repo_root / "api")]
    monkeypatch.setitem(sys.modules, "api", api_pkg)

    # api.db
    db_pkg = ModuleType("api.db")
    db_pkg.__path__ = []

    class _FileType:
        FOLDER = "folder"
        DOC = "doc"

        @property
        def value(self):
            return self

    class _FilePermissionLevel:
        VIEW = "view"
        EDIT = "edit"
        ADMIN = "admin"
        OWNER = "owner"

    # Make FileType behave like an enum with .value
    class _FileTypeEnum:
        FOLDER = type("FOLDER", (), {"value": "folder"})()
        DOC = type("DOC", (), {"value": "doc"})()

    db_pkg.FileType = _FileTypeEnum
    db_pkg.FilePermissionLevel = _FilePermissionLevel
    monkeypatch.setitem(sys.modules, "api.db", db_pkg)
    api_pkg.db = db_pkg

    # api.db.services
    services_pkg = ModuleType("api.db.services")
    services_pkg.__path__ = []
    services_pkg.duplicate_name = lambda query, **kwargs: kwargs.get("name", "")
    monkeypatch.setitem(sys.modules, "api.db.services", services_pkg)

    return api_pkg, db_pkg, services_pkg


def _load_file_api_service(monkeypatch, repo_root=None):
    """Load file_api_service module with mocked dependencies."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[5]

    api_pkg, db_pkg, services_pkg = _create_mock_modules(monkeypatch, repo_root)

    # FileService mock
    file_service_mod = ModuleType("api.db.services.file_service")
    file_service_mod.FileService = SimpleNamespace(
        get_root_folder=lambda tenant_id: {"id": f"root-{tenant_id}"},
        get_by_id=lambda file_id: (True, _DummyFile(file_id)),
        get_by_pf_id=lambda *args, **kwargs: ([], 0),
        get_parent_folder=lambda file_id: _DummyFile(file_id, parent_id="root"),
        init_knowledgebase_docs=lambda *a, **kw: None,
        get_kb_id_by_file_id=lambda file_id: [],
        get_folder_size=lambda folder_id: 0,
    )
    monkeypatch.setitem(sys.modules, "api.db.services.file_service", file_service_mod)
    services_pkg.file_service = file_service_mod

    # TenantService mock
    user_service_mod = ModuleType("api.db.services.user_service")
    user_service_mod.TenantService = SimpleNamespace(
        get_joined_tenants_by_user_id=lambda user_id: []
    )
    monkeypatch.setitem(sys.modules, "api.db.services.user_service", user_service_mod)
    services_pkg.user_service = user_service_mod

    # TeamPermissionService mock
    team_perm_mod = ModuleType("api.db.services.team_permission_service")
    team_perm_mod.TeamPermissionService = SimpleNamespace(
        get_shared_file_ids_for_user=lambda user_id, user_tenant_id: []
    )
    monkeypatch.setitem(sys.modules, "api.db.services.team_permission_service", team_perm_mod)
    services_pkg.team_permission_service = team_perm_mod

    # check_file_permission mock
    check_perm_mod = ModuleType("api.common.check_file_permission")
    check_perm_mod.check_file_permission = lambda file_id, user_id, level: (True, "")
    check_perm_mod.check_file_operation_permission = lambda file_id, user_id, op: (True, "")
    check_perm_mod.check_parent_folder_permission = lambda file_id, user_id, level: (True, "")
    check_perm_mod.FilePermissionLevel = db_pkg.FilePermissionLevel
    monkeypatch.setitem(sys.modules, "api.common.check_file_permission", check_perm_mod)

    # check_team_permission mock
    check_team_mod = ModuleType("api.common.check_team_permission")
    check_team_mod.check_file_team_permission = lambda *args, **kw: True
    monkeypatch.setitem(sys.modules, "api.common.check_team_permission", check_team_mod)

    # common mock
    common_mod = ModuleType("common")
    common_mod.__path__ = [str(repo_root / "common")]
    monkeypatch.setitem(sys.modules, "common", common_mod)

    # common.constants mock
    constants_mod = ModuleType("common.constants")
    constants_mod.FileSource = type("_FileSource", (), {"KNOWLEDGEBASE": "knowledgebase"})()
    monkeypatch.setitem(sys.modules, "common.constants", constants_mod)

    # common.misc_utils mock
    misc_mod = ModuleType("common.misc_utils")
    misc_mod.get_uuid = lambda: "test-uuid"
    misc_mod.thread_pool_exec = lambda func, *args, **kwargs: func(*args, **kwargs)
    monkeypatch.setitem(sys.modules, "common.misc_utils", misc_mod)

    # api.utils mock
    utils_pkg = ModuleType("api.utils")
    utils_pkg.__path__ = [str(repo_root / "api" / "utils")]
    monkeypatch.setitem(sys.modules, "api.utils", utils_pkg)

    # api.utils.file_utils mock
    file_utils_mod = ModuleType("api.utils.file_utils")
    file_utils_mod.filename_type = lambda filename: "doc"
    monkeypatch.setitem(sys.modules, "api.utils.file_utils", file_utils_mod)

    # api.db.services.document_service mock
    doc_svc_mod = ModuleType("api.db.services.document_service")
    doc_svc_mod.DocumentService = SimpleNamespace(get_doc_count=lambda tenant_id: 0)
    monkeypatch.setitem(sys.modules, "api.db.services.document_service", doc_svc_mod)

    # api.db.services.file2document_service mock
    f2d_svc_mod = ModuleType("api.db.services.file2document_service")
    f2d_svc_mod.File2DocumentService = SimpleNamespace(get_by_file_id=lambda file_id: [])
    monkeypatch.setitem(sys.modules, "api.db.services.file2document_service", f2d_svc_mod)

    # api.db.services.file_permission_service mock
    fp_svc_mod = ModuleType("api.db.services.file_permission_service")
    fp_svc_mod.FilePermissionService = SimpleNamespace(delete_file_shares=lambda *a, **kw: None)
    monkeypatch.setitem(sys.modules, "api.db.services.file_permission_service", fp_svc_mod)

    # common.settings mock
    settings_mod = ModuleType("common.settings")
    settings_mod.STORAGE_IMPL = SimpleNamespace(
        obj_exist=lambda *a, **kw: False,
        put=lambda *a, **kw: None,
    )
    monkeypatch.setitem(sys.modules, "common.settings", settings_mod)
    common_mod.settings = settings_mod

    # Load the real module
    module_path = repo_root / "api" / "apps" / "services" / "file_api_service.py"
    spec = importlib.util.spec_from_file_location(
        "api.apps.services.file_api_service", module_path
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "api.apps.services.file_api_service", module)
    spec.loader.exec_module(module)

    return module


# ===========================================================================
# TDD TESTS
# ===========================================================================


class TestTeamMemberSeesSharedFolderInRootList:
    """
    TC-LIST-001: Team member should see shared folders in root directory listing.

    Scenario:
    1. Owner (thomas) creates a folder and shares it with the team
    2. Team member (iwen) lists files at root level (no parent_id)
    3. iwen should see the shared folder in the list with is_team_shared=True
    """

    @pytest.mark.p1
    def test_shared_folder_appears_in_member_root_list(self, monkeypatch):
        """
        RED PHASE: Verify team member sees shared folders in root listing.
        """
        module = _load_file_api_service(monkeypatch)

        # Mock: Member has joined owner's tenant (patch on the loaded module's imports)
        import api.db.services.user_service as user_svc_mod
        monkeypatch.setattr(
            user_svc_mod.TenantService,
            "get_joined_tenants_by_user_id",
            lambda user_id: [{"tenant_id": OWNER_TENANT_ID, "name": "thomas-team"}]
            if user_id == MEMBER_USER_ID
            else []
        )

        # Mock: Owner has shared a folder with the team
        import api.db.services.team_permission_service as team_perm_mod
        monkeypatch.setattr(
            team_perm_mod.TeamPermissionService,
            "get_shared_file_ids_for_user",
            lambda user_id, user_tenant_id: [SHARED_FOLDER_ID]
            if user_id == MEMBER_USER_ID and user_tenant_id == OWNER_TENANT_ID
            else []
        )

        # Mock: Shared folder exists
        shared_folder = _DummyFile(
            SHARED_FOLDER_ID,
            file_type="folder",
            tenant_id=OWNER_TENANT_ID,
            created_by=OWNER_TENANT_ID,
            name="Shared Project Folder",
        )

        def mock_get_by_id(file_id):
            if file_id == SHARED_FOLDER_ID:
                return (True, shared_folder)
            return (True, _DummyFile(file_id))

        monkeypatch.setattr(module.FileService, "get_by_id", mock_get_by_id)

        monkeypatch.setattr(
            module.FileService,
            "get_root_folder",
            lambda tenant_id: {"id": MEMBER_ROOT_FOLDER_ID}
            if tenant_id == MEMBER_USER_ID
            else {"id": OWNER_ROOT_FOLDER_ID}
        )

        monkeypatch.setattr(
            module,
            "check_file_permission",
            lambda file_id, user_id, level: (True, "")
        )

        monkeypatch.setattr(
            module.FileService,
            "get_by_pf_id",
            lambda tenant_id, pf_id, *args, **kwargs: ([], 0)
        )

        monkeypatch.setattr(
            module.FileService,
            "get_parent_folder",
            lambda file_id: _DummyFile(file_id, name="parent", parent_id=None)
        )

        # ACT: Member lists root directory
        success, result = module.list_files(
            tenant_id=MEMBER_USER_ID,
            args={},
            user_id=MEMBER_USER_ID
        )

        # ASSERT: Should succeed
        assert success is True, f"list_files should succeed but got error: {result}"
        assert "files" in result, "Result should contain 'files' key"

        # KEY ASSERTION: Shared folder should appear
        file_ids = [f["id"] for f in result["files"]]
        assert SHARED_FOLDER_ID in file_ids, (
            f"Shared folder {SHARED_FOLDER_ID} should appear in member's root list. "
            f"Got files: {file_ids}"
        )

        # ASSERT: Shared folder should be marked
        shared_file = next(f for f in result["files"] if f["id"] == SHARED_FOLDER_ID)
        assert shared_file.get("is_team_shared") is True, (
            "Shared folder should have is_team_shared=True marker"
        )


class TestTeamMemberDoesNotSeeOwnSharedFolders:
    """
    TC-LIST-002: Owner should not see their own folder as "shared".
    """

    @pytest.mark.p1
    def test_owner_sees_shared_folder_as_normal(self, monkeypatch):
        """
        Verify owner sees their own folder without shared marker.
        """
        module = _load_file_api_service(monkeypatch)

        # Mock: Owner has no joined tenants
        import api.db.services.user_service as user_svc_mod
        monkeypatch.setattr(
            user_svc_mod.TenantService,
            "get_joined_tenants_by_user_id",
            lambda user_id: []
        )

        owner_folder = _DummyFile(
            SHARED_FOLDER_ID,
            file_type="folder",
            tenant_id=OWNER_TENANT_ID,
            created_by=OWNER_TENANT_ID,
            name="My Folder",
        )

        def mock_get_by_id(file_id):
            if file_id == SHARED_FOLDER_ID:
                return (True, owner_folder)
            return (True, _DummyFile(file_id, tenant_id=OWNER_TENANT_ID))

        monkeypatch.setattr(module.FileService, "get_by_id", mock_get_by_id)

        monkeypatch.setattr(
            module.FileService,
            "get_root_folder",
            lambda tenant_id: {"id": OWNER_ROOT_FOLDER_ID}
        )

        monkeypatch.setattr(
            module,
            "check_file_permission",
            lambda file_id, user_id, level: (True, "")
        )

        def mock_get_by_pf_id(tenant_id, pf_id, *args, **kwargs):
            if tenant_id == OWNER_TENANT_ID and pf_id == OWNER_ROOT_FOLDER_ID:
                return ([owner_folder.to_dict()], 1)
            return ([], 0)

        monkeypatch.setattr(module.FileService, "get_by_pf_id", mock_get_by_pf_id)

        monkeypatch.setattr(
            module.FileService,
            "get_parent_folder",
            lambda file_id: _DummyFile(file_id, name="parent", parent_id=None)
        )

        # ACT
        success, result = module.list_files(
            tenant_id=OWNER_TENANT_ID,
            args={},
            user_id=OWNER_TENANT_ID
        )

        # ASSERT
        assert success is True
        file_ids = [f["id"] for f in result["files"]]
        assert SHARED_FOLDER_ID in file_ids

        # KEY: Owner should NOT see is_team_shared marker
        owner_file = next(f for f in result["files"] if f["id"] == SHARED_FOLDER_ID)
        assert owner_file.get("is_team_shared") is not True


class TestTeamMemberNavigatesIntoSharedFolder:
    """
    TC-LIST-003: Team member can navigate into shared folder.
    """

    @pytest.mark.p1
    def test_member_sees_shared_folder_contents(self, monkeypatch):
        """
        Verify member can see contents of shared folder.
        """
        module = _load_file_api_service(monkeypatch)

        shared_folder = _DummyFile(
            SHARED_FOLDER_ID,
            file_type="folder",
            tenant_id=OWNER_TENANT_ID,
            created_by=OWNER_TENANT_ID,
            parent_id=OWNER_ROOT_FOLDER_ID,
            name="Shared Project",
        )

        child_file = _DummyFile(
            "child-file-001",
            file_type="doc",
            tenant_id=OWNER_TENANT_ID,
            created_by=OWNER_TENANT_ID,
            parent_id=SHARED_FOLDER_ID,
            name="report.pdf",
        )

        def mock_get_by_id(file_id):
            if file_id == SHARED_FOLDER_ID:
                return (True, shared_folder)
            if file_id == "child-file-001":
                return (True, child_file)
            return (True, _DummyFile(file_id))

        monkeypatch.setattr(module.FileService, "get_by_id", mock_get_by_id)

        def mock_check_permission(file_id, user_id, level):
            if user_id == OWNER_TENANT_ID:
                return (True, "")
            if file_id == SHARED_FOLDER_ID and user_id == MEMBER_USER_ID:
                return (True, "")
            return (False, "No permission")

        monkeypatch.setattr(module, "check_file_permission", mock_check_permission)

        def mock_get_by_pf_id(tenant_id, pf_id, *args, **kwargs):
            if pf_id == SHARED_FOLDER_ID:
                if tenant_id == OWNER_TENANT_ID:
                    return ([child_file.to_dict()], 1)
                else:
                    return ([], 0)
            return ([], 0)

        monkeypatch.setattr(module.FileService, "get_by_pf_id", mock_get_by_pf_id)

        monkeypatch.setattr(
            module.FileService,
            "get_parent_folder",
            lambda file_id: _DummyFile(file_id, name="parent", parent_id="root")
        )

        # ACT: Member navigates into shared folder
        success, result = module.list_files(
            tenant_id=MEMBER_USER_ID,
            args={"parent_id": SHARED_FOLDER_ID},
            user_id=MEMBER_USER_ID
        )

        # ASSERT
        assert success is True, f"Should succeed but got: {result}"
        file_ids = [f["id"] for f in result["files"]]
        assert "child-file-001" in file_ids, (
            f"Member should see contents of shared folder. Got: {file_ids}"
        )


class TestNoJoinedTenantsReturnsOwnFilesOnly:
    """
    TC-LIST-004: User without joined tenants sees only their own files.
    """

    @pytest.mark.p1
    def test_user_without_teams_sees_own_files(self, monkeypatch):
        """
        Verify graceful degradation when user has no team memberships.
        """
        module = _load_file_api_service(monkeypatch)

        import api.db.services.user_service as user_svc_mod
        monkeypatch.setattr(
            user_svc_mod.TenantService,
            "get_joined_tenants_by_user_id",
            lambda user_id: []
        )

        # Mock root folder for member
        member_root = _DummyFile(
            MEMBER_ROOT_FOLDER_ID,
            file_type="folder",
            tenant_id=MEMBER_USER_ID,
            created_by=MEMBER_USER_ID,
            name="root",
        )

        user_file = _DummyFile(
            "user-file-001",
            tenant_id=MEMBER_USER_ID,
            created_by=MEMBER_USER_ID,
            parent_id=MEMBER_ROOT_FOLDER_ID,
            name="my_document.pdf",
        )

        def mock_get_by_id(file_id):
            if file_id == MEMBER_ROOT_FOLDER_ID:
                return (True, member_root)
            if file_id == "user-file-001":
                return (True, user_file)
            return (True, _DummyFile(file_id, tenant_id=MEMBER_USER_ID))

        monkeypatch.setattr(module.FileService, "get_by_id", mock_get_by_id)

        monkeypatch.setattr(
            module.FileService,
            "get_root_folder",
            lambda tenant_id: {"id": MEMBER_ROOT_FOLDER_ID}
        )

        monkeypatch.setattr(
            module,
            "check_file_permission",
            lambda file_id, user_id, level: (True, "")
        )

        def mock_get_by_pf_id(tenant_id, pf_id, *args, **kwargs):
            if pf_id == MEMBER_ROOT_FOLDER_ID and tenant_id == MEMBER_USER_ID:
                return ([user_file.to_dict()], 1)
            return ([], 0)

        monkeypatch.setattr(module.FileService, "get_by_pf_id", mock_get_by_pf_id)

        monkeypatch.setattr(
            module.FileService,
            "get_parent_folder",
            lambda file_id: _DummyFile(file_id, name="parent", parent_id=None)
        )

        # ACT
        success, result = module.list_files(
            tenant_id=MEMBER_USER_ID,
            args={},
            user_id=MEMBER_USER_ID
        )

        # ASSERT
        assert success is True
        assert result["total"] == 1
        assert result["files"][0]["id"] == "user-file-001"
