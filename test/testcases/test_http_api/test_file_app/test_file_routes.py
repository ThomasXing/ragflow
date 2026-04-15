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

import asyncio
import importlib.util
import sys
from enum import Enum
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


@pytest.fixture(scope="session")
def auth():
    return "unit-auth"


@pytest.fixture(scope="session", autouse=True)
def set_tenant_info():
    return None


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
        parent_id="pf1",
        location="loc1",
        name="doc.txt",
        source_type="user",
        size=1,
    ):
        self.id = file_id
        self.type = file_type
        self.tenant_id = tenant_id
        self.parent_id = parent_id
        self.location = location
        self.name = name
        self.source_type = source_type
        self.size = size

    def to_json(self):
        return {"id": self.id, "name": self.name, "type": self.type}

    def to_dict(self):
        return {"id": self.id, "name": self.name, "type": self.type,
                "tenant_id": self.tenant_id, "parent_id": self.parent_id}


def _run(coro):
    return asyncio.run(coro)


def _load_file_api_service(monkeypatch):
    repo_root = Path(__file__).resolve().parents[4]

    api_pkg = ModuleType("api")
    api_pkg.__path__ = [str(repo_root / "api")]
    monkeypatch.setitem(sys.modules, "api", api_pkg)

    common_pkg = ModuleType("api.common")
    common_pkg.__path__ = []
    monkeypatch.setitem(sys.modules, "api.common", common_pkg)

    permission_mod = ModuleType("api.common.check_team_permission")
    permission_mod.check_file_team_permission = lambda *_args, **_kwargs: True
    monkeypatch.setitem(sys.modules, "api.common.check_team_permission", permission_mod)
    common_pkg.check_team_permission = permission_mod

    # Mock check_file_permission (required by file_api_service)
    check_file_perm_mod = ModuleType("api.common.check_file_permission")
    check_file_perm_mod.check_parent_folder_permission = lambda *_a, **_kw: (True, "")
    check_file_perm_mod.check_file_permission = lambda *_a, **_kw: (True, "")
    check_file_perm_mod.check_file_operation_permission = lambda *_a, **_kw: (True, "")
    check_file_perm_mod.FilePermissionLevel = type("_FPL", (), {"VIEW": "view", "EDIT": "edit", "ADMIN": "admin", "OWNER": "owner"})()
    monkeypatch.setitem(sys.modules, "api.common.check_file_permission", check_file_perm_mod)
    common_pkg.check_file_permission = check_file_perm_mod

    # Mock FilePermissionService (module registered early; services_pkg attr set later)
    file_perm_svc_mod = ModuleType("api.db.services.file_permission_service")
    file_perm_svc_mod.FilePermissionService = SimpleNamespace(
        delete_file_shares=lambda *_a, **_kw: None,
    )
    monkeypatch.setitem(sys.modules, "api.db.services.file_permission_service", file_perm_svc_mod)

    # Mock TeamPermissionService
    team_perm_svc_mod = ModuleType("api.db.services.team_permission_service")
    team_perm_svc_mod.TeamPermissionService = SimpleNamespace(
        get_shared_file_ids_for_user=lambda *_a, **_kw: [],
    )
    monkeypatch.setitem(sys.modules, "api.db.services.team_permission_service", team_perm_svc_mod)

    # Mock TenantService
    tenant_svc_mod = ModuleType("api.db.services.user_service")
    tenant_svc_mod.TenantService = SimpleNamespace(
        get_joined_tenants_by_user_id=lambda _uid: [],
    )
    monkeypatch.setitem(sys.modules, "api.db.services.user_service", tenant_svc_mod)

    db_pkg = ModuleType("api.db")
    db_pkg.__path__ = []

    class _FileType(Enum):
        FOLDER = "folder"
        VIRTUAL = "virtual"
        DOC = "doc"
        VISUAL = "visual"

    db_pkg.FileType = _FileType

    class _FilePermissionLevel:
        VIEW = "view"
        EDIT = "edit"
        ADMIN = "admin"
        OWNER = "owner"

    db_pkg.FilePermissionLevel = _FilePermissionLevel
    monkeypatch.setitem(sys.modules, "api.db", db_pkg)
    api_pkg.db = db_pkg

    services_pkg = ModuleType("api.db.services")
    services_pkg.__path__ = []
    services_pkg.duplicate_name = lambda _query, **kwargs: kwargs.get("name", "")
    monkeypatch.setitem(sys.modules, "api.db.services", services_pkg)

    # Attach service modules to services_pkg (must be after services_pkg creation)
    services_pkg.file_permission_service = file_perm_svc_mod
    services_pkg.team_permission_service = team_perm_svc_mod
    services_pkg.user_service = tenant_svc_mod

    document_service_mod = ModuleType("api.db.services.document_service")
    document_service_mod.DocumentService = SimpleNamespace(
        get_doc_count=lambda _uid: 0,
        get_by_id=lambda doc_id: (True, SimpleNamespace(id=doc_id)),
        get_tenant_id=lambda _doc_id: "tenant1",
        remove_document=lambda *_args, **_kwargs: True,
        update_by_id=lambda *_args, **_kwargs: True,
    )
    monkeypatch.setitem(sys.modules, "api.db.services.document_service", document_service_mod)
    services_pkg.document_service = document_service_mod

    file2doc_mod = ModuleType("api.db.services.file2document_service")
    file2doc_mod.File2DocumentService = SimpleNamespace(
        get_by_file_id=lambda _file_id: [],
        delete_by_file_id=lambda _file_id: None,
    )
    monkeypatch.setitem(sys.modules, "api.db.services.file2document_service", file2doc_mod)
    services_pkg.file2document_service = file2doc_mod

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

    file_utils_mod = ModuleType("api.utils.file_utils")
    file_utils_mod.filename_type = lambda _filename: _FileType.DOC.value
    monkeypatch.setitem(sys.modules, "api.utils.file_utils", file_utils_mod)

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

    constants_mod = ModuleType("common.constants")

    class _FileSource:
        KNOWLEDGEBASE = "knowledgebase"

    constants_mod.FileSource = _FileSource
    monkeypatch.setitem(sys.modules, "common.constants", constants_mod)

    misc_utils_mod = ModuleType("common.misc_utils")
    misc_utils_mod.get_uuid = lambda: "uuid-1"

    async def thread_pool_exec(func, *args, **kwargs):
        return func(*args, **kwargs)

    misc_utils_mod.thread_pool_exec = thread_pool_exec
    monkeypatch.setitem(sys.modules, "common.misc_utils", misc_utils_mod)

    module_path = repo_root / "api" / "apps" / "services" / "file_api_service.py"
    spec = importlib.util.spec_from_file_location("api.apps.services.file_api_service", module_path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "api.apps.services.file_api_service", module)
    spec.loader.exec_module(module)
    return module


@pytest.mark.p2
def test_upload_file_requires_existing_folder(monkeypatch):
    module = _load_file_api_service(monkeypatch)
    monkeypatch.setattr(module.FileService, "get_by_id", lambda _file_id: (False, None))

    ok, message = _run(module.upload_file("tenant1", "pf1", [_DummyUploadFile("a.txt")]))
    assert ok is False
    assert message == "Can't find this folder!"


@pytest.mark.p2
def test_upload_file_respects_user_limit(monkeypatch):
    module = _load_file_api_service(monkeypatch)
    monkeypatch.setattr(module.FileService, "get_by_id", lambda _file_id: (True, SimpleNamespace(id="pf1", name="pf1", tenant_id="tenant1")))
    monkeypatch.setattr(module.DocumentService, "get_doc_count", lambda _uid: 1)
    monkeypatch.setenv("MAX_FILE_NUM_PER_USER", "1")

    ok, message = _run(module.upload_file("tenant1", "pf1", [_DummyUploadFile("a.txt")]))
    assert ok is False
    assert message == "Exceed the maximum file number of a free user!"
    monkeypatch.delenv("MAX_FILE_NUM_PER_USER", raising=False)


@pytest.mark.p2
def test_upload_file_success_uses_new_service_layer(monkeypatch):
    module = _load_file_api_service(monkeypatch)
    storage_puts = []

    monkeypatch.setattr(module.FileService, "get_by_id", lambda _file_id: (True, SimpleNamespace(id="pf1", name="pf1", tenant_id="tenant1")))
    monkeypatch.setattr(module.FileService, "get_id_list_by_id", lambda *_args, **_kwargs: ["pf1"])
    monkeypatch.setattr(
        module.FileService,
        "create_folder",
        lambda _file, parent_id, _names, _len_id, **_kw: SimpleNamespace(id=parent_id),
    )
    monkeypatch.setattr(module.settings, "STORAGE_IMPL", SimpleNamespace(
        obj_exist=lambda *_args, **_kwargs: False,
        put=lambda bucket, location, blob: storage_puts.append((bucket, location, blob)),
        rm=lambda *_args, **_kwargs: None,
        move=lambda *_args, **_kwargs: None,
    ))

    ok, data = _run(module.upload_file("tenant1", "pf1", [_DummyUploadFile("a.txt", b"hello")]))
    assert ok is True
    assert data[0]["name"] == "a.txt"
    assert storage_puts == [("pf1", "a.txt", b"hello")]


@pytest.mark.p2
def test_create_folder_rejects_duplicate_name(monkeypatch):
    module = _load_file_api_service(monkeypatch)
    monkeypatch.setattr(module.FileService, "query", lambda **_kwargs: [SimpleNamespace(id="existing")])

    ok, message = _run(module.create_folder("tenant1", "dup", "pf1", module.FileType.FOLDER.value))
    assert ok is False
    assert message == "Duplicated folder name in the same folder."


@pytest.mark.p2
def test_delete_files_checks_team_permission(monkeypatch):
    module = _load_file_api_service(monkeypatch)
    monkeypatch.setattr(
        module.FileService,
        "get_by_id",
        lambda _file_id: (True, _DummyFile("file1", module.FileType.DOC.value)),
    )
    monkeypatch.setattr(module, "check_file_team_permission", lambda *_args, **_kwargs: False)

    ok, message = _run(module.delete_files("tenant1", ["file1"]))
    assert ok is False
    assert message == "No authorization."


@pytest.mark.p2
def test_move_files_rejects_extension_change_in_new_name(monkeypatch):
    module = _load_file_api_service(monkeypatch)
    monkeypatch.setattr(
        module.FileService,
        "get_by_ids",
        lambda _ids: [_DummyFile("file1", module.FileType.DOC.value, name="a.txt")],
    )

    ok, message = _run(module.move_files("tenant1", ["file1"], new_name="a.pdf"))
    assert ok is False
    assert message == "The extension of file can't be changed"


@pytest.mark.p2
def test_move_files_handles_dest_and_storage_move(monkeypatch):
    module = _load_file_api_service(monkeypatch)
    moved = []
    updated = []

    monkeypatch.setattr(
        module.FileService,
        "get_by_id",
        lambda file_id: (False, None) if file_id == "missing" else (True, _DummyFile(file_id, module.FileType.FOLDER.value, name="dest")),
    )
    monkeypatch.setattr(
        module.FileService,
        "get_by_ids",
        lambda _ids: [_DummyFile("file1", module.FileType.DOC.value, parent_id="src", location="old", name="a.txt")],
    )
    monkeypatch.setattr(module.settings, "STORAGE_IMPL", SimpleNamespace(
        obj_exist=lambda *_args, **_kwargs: False,
        put=lambda *_args, **_kwargs: None,
        rm=lambda *_args, **_kwargs: None,
        move=lambda old_bucket, old_loc, new_bucket, new_loc: moved.append((old_bucket, old_loc, new_bucket, new_loc)),
    ))
    monkeypatch.setattr(module.FileService, "update_by_id", lambda file_id, data: updated.append((file_id, data)) or True)

    ok, message = _run(module.move_files("tenant1", ["file1"], "missing"))
    assert ok is False
    assert message == "Parent folder not found!"

    ok, data = _run(module.move_files("tenant1", ["file1"], "dest"))
    assert ok is True
    assert data is True
    assert moved == [("src", "old", "dest", "a.txt")]
    assert updated == [("file1", {"parent_id": "dest", "location": "a.txt"})]


@pytest.mark.p2
def test_move_files_renames_in_place_without_storage_move(monkeypatch):
    module = _load_file_api_service(monkeypatch)
    db_updates = []
    doc_updates = []

    monkeypatch.setattr(
        module.FileService,
        "get_by_ids",
        lambda _ids: [_DummyFile("file1", module.FileType.DOC.value, parent_id="pf1", name="a.txt")],
    )
    monkeypatch.setattr(module.FileService, "update_by_id", lambda file_id, data: db_updates.append((file_id, data)) or True)
    monkeypatch.setattr(
        module.File2DocumentService,
        "get_by_file_id",
        lambda _file_id: [SimpleNamespace(document_id="doc1")],
    )
    monkeypatch.setattr(module.DocumentService, "update_by_id", lambda doc_id, data: doc_updates.append((doc_id, data)) or True)

    ok, data = _run(module.move_files("tenant1", ["file1"], new_name="b.txt"))
    assert ok is True
    assert data is True
    assert db_updates == [("file1", {"name": "b.txt"})]
    assert doc_updates == [("doc1", {"name": "b.txt"})]


@pytest.mark.p2
def test_list_files_root_injects_team_shared_folders(monkeypatch):
    """
    TC-LIST-001: When listing root directory, shared folders from tenants
    that the user belongs to (via UserTenant.NORMAL) must be injected.

    Scenario: iwen is a NORMAL member of thomas's tenant.
    thomas has enabled team share on 'test2' folder.
    iwen's root listing should include 'test2'.
    """
    module = _load_file_api_service(monkeypatch)

    THOMAS_TENANT_ID = "thomas-id"
    IWEN_USER_ID = "iwen-id"
    SHARED_FOLDER_ID = "test2-folder-id"

    shared_folder = _DummyFile(
        SHARED_FOLDER_ID, "folder",
        tenant_id=THOMAS_TENANT_ID,
        name="test2",
        parent_id="thomas-root",
    )

    # iwen's own root folder
    iwen_root = _DummyFile("iwen-root", "folder", tenant_id=IWEN_USER_ID, name="root")

    monkeypatch.setattr(module.FileService, "get_root_folder",
                        lambda tid: {"id": "iwen-root"})
    monkeypatch.setattr(module.FileService, "get_by_id",
                        lambda fid: (True, iwen_root) if fid == "iwen-root"
                        else (True, shared_folder) if fid == SHARED_FOLDER_ID
                        else (False, None))
    monkeypatch.setattr(module.FileService, "get_by_pf_id",
                        lambda *_a, **_kw: ([], 0))  # iwen's own root is empty
    monkeypatch.setattr(module.FileService, "get_parent_folder",
                        lambda fid: SimpleNamespace(to_json=lambda: {"id": fid}))

    # Patch TenantService and TeamPermissionService on the module's imported references
    # (They are accessed via the module's own namespace after import)
    user_svc_mod = sys.modules.get("api.db.services.user_service")

    # iwen is a NORMAL member of thomas's tenant
    user_svc_mod.TenantService = SimpleNamespace(
        get_joined_tenants_by_user_id=lambda uid: [{"tenant_id": THOMAS_TENANT_ID}] if uid == IWEN_USER_ID else []
    )

    # thomas has shared SHARED_FOLDER_ID with his tenant
    # TeamPermissionService is top-level imported in file_api_service, so patch it directly
    # on the module object to override the already-bound name.
    monkeypatch.setattr(module, "TeamPermissionService", SimpleNamespace(
        get_shared_file_ids_for_user=lambda user_id, user_tenant_id:
            [SHARED_FOLDER_ID] if user_tenant_id == THOMAS_TENANT_ID else []
    ))

    ok, result = module.list_files(IWEN_USER_ID, {}, user_id=IWEN_USER_ID)

    assert ok is True, f"list_files failed: {result}"
    file_ids = [f["id"] if isinstance(f, dict) else f.id for f in result["files"]]
    assert SHARED_FOLDER_ID in file_ids, (
        f"Shared folder '{SHARED_FOLDER_ID}' not injected into root listing. "
        f"Got: {file_ids}"
    )
    assert result["total"] >= 1


@pytest.mark.p2
def test_list_files_root_no_injection_without_user_tenant(monkeypatch):
    """
    TC-LIST-002: When iwen is NOT in UserTenant for thomas's tenant,
    the shared folder should NOT appear in iwen's root listing.
    Documents current expected behavior.
    """
    module = _load_file_api_service(monkeypatch)

    IWEN_USER_ID = "iwen-id"
    SHARED_FOLDER_ID = "test2-folder-id"

    iwen_root = _DummyFile("iwen-root", "folder", tenant_id=IWEN_USER_ID, name="root")

    monkeypatch.setattr(module.FileService, "get_root_folder",
                        lambda tid: {"id": "iwen-root"})
    monkeypatch.setattr(module.FileService, "get_by_id",
                        lambda fid: (True, iwen_root) if fid == "iwen-root"
                        else (False, None))
    monkeypatch.setattr(module.FileService, "get_by_pf_id",
                        lambda *_a, **_kw: ([], 0))
    monkeypatch.setattr(module.FileService, "get_parent_folder",
                        lambda fid: SimpleNamespace(to_json=lambda: {"id": fid}))

    # iwen is NOT in UserTenant for any other tenant
    user_svc_mod = sys.modules.get("api.db.services.user_service")
    user_svc_mod.TenantService = SimpleNamespace(
        get_joined_tenants_by_user_id=lambda uid: []  # empty
    )

    ok, result = module.list_files(IWEN_USER_ID, {}, user_id=IWEN_USER_ID)

    assert ok is True
    file_ids = [f["id"] if isinstance(f, dict) else f.id for f in result["files"]]
    assert SHARED_FOLDER_ID not in file_ids


@pytest.mark.p2
def test_get_file_content_checks_permission(monkeypatch):
    module = _load_file_api_service(monkeypatch)
    # The new permission check uses check_file_permission which returns (True, "") by default
    # and check_file_team_permission returns True by default, so the file is accessible.
    # To test the "no permission" path, we need to make both return false/denied.
    monkeypatch.setattr(module, "check_file_permission", lambda *_a, **_kw: (False, "No authorization."))
    monkeypatch.setattr(module, "check_file_team_permission", lambda *_args, **_kwargs: False)

    ok, message = module.get_file_content("tenant1", "file1")
    assert ok is False
    assert "permission" in message.lower() or "authorization" in message.lower()

    # Restore permission and verify access
    monkeypatch.setattr(module, "check_file_permission", lambda *_a, **_kw: (True, ""))
    monkeypatch.setattr(module, "check_file_team_permission", lambda *_args, **_kwargs: True)
    ok, file = module.get_file_content("tenant1", "file1")
    assert ok is True
    assert file.id == "file1"
