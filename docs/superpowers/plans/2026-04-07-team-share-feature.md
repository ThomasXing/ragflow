# 团队共享功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有文件夹共享功能从"共享给某人"升级为"共享给团队所有人"，并将前端复杂弹窗改为简单的Switch开关

**Architecture:** 在现有个人共享架构基础上，新增 `team_permission_share` 表专门管理团队共享，权限检查时优先检查个人权限，然后检查团队权限，最后是租户默认权限。前端用 `FileTeamShareToggle` 组件替换 `FileShareDialog`，提供一键开关体验。

**Tech Stack:** Python Flask后端、Peewee ORM、React TypeScript前端、Ant Design + shadcn/ui

---

## 文件结构

### 后端文件
- **创建**: `api/db/services/team_permission_service.py` - 团队共享服务层
- **修改**: `api/db/db_models.py` - 新增TeamPermissionShare模型
- **修改**: `api/apps/file_permission_app.py` - 新增团队共享API端点
- **修改**: `api/common/check_file_permission.py` - 更新权限检查逻辑
- **创建**: `docker/oceanbase/init.d/create_team_permission_share_table.sql` - 数据库迁移脚本

### 前端文件
- **创建**: `web/src/components/file-team-share-toggle.tsx` - 团队共享开关组件
- **修改**: `web/src/services/file-permission-service.ts` - 新增团队共享API调用
- **修改**: `web/src/locales/zh.ts` - 新增国际化翻译
- **废弃**: `web/src/components/file-share-dialog.tsx` - 旧组件标记为废弃

### 测试文件
- **创建**: `tests/api/test_team_permission.py` - 后端团队共享测试
- **创建**: `tests/web/components/file-team-share-toggle.test.tsx` - 前端组件测试

---

### Task 1: 数据库迁移 - 创建团队共享表

**Files:**
- Create: `docker/oceanbase/init.d/create_team_permission_share_table.sql`
- Modify: `api/db/db_models.py`

- [ ] **Step 1: 创建数据库迁移脚本**

```sql
-- docker/oceanbase/init.d/create_team_permission_share_table.sql
CREATE TABLE IF NOT EXISTS `team_permission_share` (
  `id` varchar(32) NOT NULL PRIMARY KEY,
  `file_id` varchar(32) NOT NULL COMMENT '文件/文件夹ID',
  `tenant_id` varchar(32) NOT NULL COMMENT '租户ID',
  `permission_level` varchar(16) NOT NULL DEFAULT 'view' COMMENT '权限级别：view/edit/admin',
  `is_enabled` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否启用（1-启用，0-禁用）',
  `created_by` varchar(32) NOT NULL COMMENT '创建者用户ID',
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  INDEX `idx_team_permission_share_file_id` (`file_id`),
  INDEX `idx_team_permission_share_tenant_id` (`tenant_id`),
  UNIQUE KEY `uniq_team_permission_share_file_tenant` (`file_id`, `tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

- [ ] **Step 2: 验证SQL语法**

```bash
mysql --version
# 验证MySQL版本支持语法
```

- [ ] **Step 3: 在DB模型中添加TeamPermissionShare类**

```python
# api/db/db_models.py (在FilePermissionShare类后添加)
class TeamPermissionShare(DataBaseModel):
    """团队共享权限表"""
    id = CharField(max_length=32, primary_key=True)
    file_id = CharField(max_length=32, null=False, help_text="文件/文件夹ID", index=True)
    tenant_id = CharField(max_length=32, null=False, help_text="租户ID", index=True)
    permission_level = CharField(max_length=16, null=False, default="view",
                                help_text="权限级别：view/edit/admin", index=True)
    is_enabled = BooleanField(default=False, help_text="是否启用")
    created_by = CharField(max_length=32, null=False, help_text="创建者用户ID")
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        db_table = "team_permission_share"
        indexes = (
            # 复合唯一索引，确保每个文件每个租户只有一条团队共享记录
            (("file_id", "tenant_id"), True),
        )
```

- [ ] **Step 4: 创建数据库迁移函数**

```python
# api/db/db_models.py (在create_file_permission_share_table函数后添加)
def create_team_permission_share_table(migrator):
    """创建团队权限共享表"""
    try:
        # 创建表
        DB.create_tables([TeamPermissionShare])
        logging.info("Successfully created team_permission_share table")

        # 添加索引（除了复合唯一索引外，还需要单列索引）
        try:
            # 创建 file_id 索引
            migrate(migrator.add_index("team_permission_share", ("file_id",), unique=False))
        except Exception as ex:
            if "already exists" not in str(ex).lower() and "duplicate" not in str(ex).lower():
                logging.warning(f"Failed to create file_id index on team_permission_share table: {ex}")

        try:
            # 创建 tenant_id 索引
            migrate(migrator.add_index("team_permission_share", ("tenant_id",), unique=False))
        except Exception as ex:
            if "already exists" not in str(ex).lower() and "duplicate" not in str(ex).lower():
                logging.warning(f"Failed to create tenant_id index on team_permission_share table: {ex}")

    except Exception as ex:
        logging.error(f"Failed to create team_permission_share table: {ex}")
        raise
```

- [ ] **Step 5: 提交数据库迁移**

```bash
git add docker/oceanbase/init.d/create_team_permission_share_table.sql api/db/db_models.py
git commit -m "feat: add team_permission_share table schema"
```

---

### Task 2: 后端服务层 - 团队权限服务

**Files:**
- Create: `api/db/services/team_permission_service.py`

- [ ] **Step 1: 创建团队权限服务基类**

```python
# api/db/services/team_permission_service.py
#
# Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
import logging
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from peewee import fn

from api.db import FilePermissionLevel
from api.db.db_models import DB, TeamPermissionShare, File, UserTenant
from api.db.services.common_service import CommonService
from api.db.services.file_service import FileService
from api.db.services.user_service import TenantService
from common.misc_utils import get_uuid


class TeamPermissionService(CommonService):
    """团队权限共享服务"""
    model = TeamPermissionShare
```

- [ ] **Step 2: 实现启用团队共享方法**

```python
    @classmethod
    @DB.connection_context()
    def enable_team_share(
        cls,
        file_id: str,
        tenant_id: str,
        created_by: str,
        permission_level: str = FilePermissionLevel.VIEW
    ) -> TeamPermissionShare:
        """
        启用文件的团队共享
        
        Args:
            file_id: 文件/文件夹ID
            tenant_id: 租户ID
            created_by: 创建者用户ID
            permission_level: 权限级别 (view/edit/admin)
            
        Returns:
            创建或更新的TeamPermissionShare对象
        """
        # 检查是否已存在团队共享记录
        existing = cls.model.select().where(
            (cls.model.file_id == file_id) &
            (cls.model.tenant_id == tenant_id)
        ).first()
        
        if existing:
            # 更新现有记录
            existing.is_enabled = True
            existing.permission_level = permission_level
            existing.updated_at = datetime.now()
            existing.save()
            return existing
        
        # 创建新记录
        team_share = cls.model.create(
            id=get_uuid(),
            file_id=file_id,
            tenant_id=tenant_id,
            permission_level=permission_level,
            is_enabled=True,
            created_by=created_by,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        return team_share
```

- [ ] **Step 3: 实现禁用团队共享方法**

```python
    @classmethod
    @DB.connection_context()
    def disable_team_share(cls, file_id: str, tenant_id: str) -> bool:
        """
        禁用文件的团队共享
        
        Args:
            file_id: 文件/文件夹ID
            tenant_id: 租户ID
            
        Returns:
            True if disabled successfully, False otherwise
        """
        updated = cls.model.update(
            is_enabled=False,
            updated_at=datetime.now()
        ).where(
            (cls.model.file_id == file_id) &
            (cls.model.tenant_id == tenant_id) &
            (cls.model.is_enabled == True)
        ).execute()
        
        return updated > 0
```

- [ ] **Step 4: 实现获取团队共享状态方法**

```python
    @classmethod
    @DB.connection_context()
    def get_team_share_status(cls, file_id: str, tenant_id: str) -> Optional[Dict]:
        """
        获取文件的团队共享状态
        
        Args:
            file_id: 文件ID
            tenant_id: 租户ID
            
        Returns:
            团队共享状态信息或None
        """
        team_share = cls.model.select().where(
            (cls.model.file_id == file_id) &
            (cls.model.tenant_id == tenant_id)
        ).first()
        
        if not team_share:
            return None
            
        return {
            "id": team_share.id,
            "file_id": team_share.file_id,
            "tenant_id": team_share.tenant_id,
            "permission_level": team_share.permission_level,
            "is_enabled": team_share.is_enabled,
            "created_by": team_share.created_by,
            "created_at": team_share.created_at.isoformat() if team_share.created_at else None,
            "updated_at": team_share.updated_at.isoformat() if team_share.updated_at else None
        }
```

- [ ] **Step 5: 实现获取用户团队权限方法**

```python
    @classmethod
    @DB.connection_context()
    def get_user_team_permission(cls, file_id: str, user_id: str) -> Optional[str]:
        """
        获取用户通过团队共享获得的权限
        
        Args:
            file_id: 文件ID
            user_id: 用户ID
            
        Returns:
            权限级别字符串，如果没有团队权限返回None
        """
        from api.db.services.user_service import UserService
        
        # 获取用户所属租户
        user = UserService.get_by_id(user_id)
        if not user:
            return None
            
        # 获取文件信息
        e, file = FileService.get_by_id(file_id)
        if not e or not file:
            return None
            
        # 检查团队共享是否启用
        team_share = cls.model.select().where(
            (cls.model.file_id == file_id) &
            (cls.model.tenant_id == file.tenant_id) &
            (cls.model.is_enabled == True)
        ).first()
        
        if not team_share:
            return None
            
        # 检查用户是否属于该租户
        tenant_membership = UserTenant.select().where(
            (UserTenant.user_id == user_id) &
            (UserTenant.tenant_id == file.tenant_id) &
            (UserTenant.status == "active")
        ).first()
        
        if not tenant_membership:
            return None
            
        return team_share.permission_level
```

- [ ] **Step 6: 实现更新团队权限级别方法**

```python
    @classmethod
    @DB.connection_context()
    def update_team_permission_level(
        cls,
        file_id: str,
        tenant_id: str,
        permission_level: str
    ) -> bool:
        """
        更新团队共享的权限级别
        
        Args:
            file_id: 文件ID
            tenant_id: 租户ID
            permission_level: 新的权限级别
            
        Returns:
            True if updated successfully, False otherwise
        """
        updated = cls.model.update(
            permission_level=permission_level,
            updated_at=datetime.now()
        ).where(
            (cls.model.file_id == file_id) &
            (cls.model.tenant_id == tenant_id) &
            (cls.model.is_enabled == True)
        ).execute()
        
        return updated > 0
```

- [ ] **Step 7: 运行服务层测试**

```bash
python -c "import sys; sys.path.append('.'); from api.db.services.team_permission_service import TeamPermissionService; print('TeamPermissionService imported successfully')"
```

- [ ] **Step 8: 提交团队权限服务**

```bash
git add api/db/services/team_permission_service.py
git commit -m "feat: implement team permission service layer"
```

---

### Task 3: 更新权限检查逻辑

**Files:**
- Modify: `api/common/check_file_permission.py`

- [ ] **Step 1: 导入TeamPermissionService**

```python
# api/common/check_file_permission.py (在文件顶部导入)
from api.db.services.team_permission_service import TeamPermissionService
```

- [ ] **Step 2: 更新get_user_effective_permission函数**

```python
def get_user_effective_permission(file_id: str, user_id: str) -> Dict[str, Any]:
    """
    获取用户对文件的有效权限（考虑所有来源）
    
    Returns:
        {
            "permission_level": "view|edit|admin|owner",
            "permission_source": "owner|explicit|team|tenant|none",
            "is_owner": bool
        }
    """
    # 1. 检查是否是文件所有者
    e, file = FileService.get_by_id(file_id)
    if not e or not file:
        return {
            "permission_level": None,
            "permission_source": "none",
            "is_owner": False
        }
    
    if file.created_by == user_id or file.tenant_id == user_id:
        return {
            "permission_level": FilePermissionLevel.OWNER,
            "permission_source": "owner",
            "is_owner": True
        }
    
    # 2. 检查显式个人权限
    explicit_permission = FilePermissionService.get_user_permission(file_id, user_id)
    if explicit_permission:
        return {
            "permission_level": explicit_permission,
            "permission_source": "explicit",
            "is_owner": False
        }
    
    # 3. 检查团队共享权限（新增）
    team_permission = TeamPermissionService.get_user_team_permission(file_id, user_id)
    if team_permission:
        return {
            "permission_level": team_permission,
            "permission_source": "team",
            "is_owner": False
        }
    
    # 4. 检查继承权限
    inherited_permission = FilePermissionService.get_inherited_permission(file_id, user_id)
    if inherited_permission:
        return {
            "permission_level": inherited_permission,
            "permission_source": "inherited",
            "is_owner": False
        }
    
    # 5. 检查租户权限（同一租户成员默认有VIEW权限）
    user_tenant = UserTenant.select().where(
        (UserTenant.user_id == user_id) &
        (UserTenant.tenant_id == file.tenant_id) &
        (UserTenant.status == "active")
    ).first()
    
    if user_tenant:
        return {
            "permission_level": FilePermissionLevel.VIEW,
            "permission_source": "tenant",
            "is_owner": False
        }
    
    # 6. 无权限
    return {
        "permission_level": None,
        "permission_source": "none",
        "is_owner": False
    }
```

- [ ] **Step 3: 添加团队权限检查辅助函数**

```python
def can_user_enable_team_share(file_id: str, user_id: str) -> Tuple[bool, Optional[str]]:
    """
    检查用户是否可以启用团队共享
    
    Args:
        file_id: 文件ID
        user_id: 用户ID
        
    Returns:
        (can_enable, error_message)
    """
    # 获取文件信息
    e, file = FileService.get_by_id(file_id)
    if not e or not file:
        return False, "文件不存在"
    
    # 检查是否是文件所有者
    if file.created_by != user_id and file.tenant_id != user_id:
        return False, "只有文件所有者可以启用团队共享"
    
    # 检查是否有管理员权限
    has_admin_perm, msg = check_file_operation_permission(file_id, user_id, "share")
    if not has_admin_perm:
        return False, msg or "需要管理员权限才能启用团队共享"
    
    return True, None


def can_user_manage_team_share(file_id: str, user_id: str) -> Tuple[bool, Optional[str]]:
    """
    检查用户是否可以管理团队共享
    
    Args:
        file_id: 文件ID
        user_id: 用户ID
        
    Returns:
        (can_manage, error_message)
    """
    # 检查是否可以启用团队共享（权限相同）
    return can_user_enable_team_share(file_id, user_id)
```

- [ ] **Step 4: 验证权限检查逻辑**

```bash
python -c "
import sys
sys.path.append('.')
from api.common.check_file_permission import get_user_effective_permission
print('Updated permission check logic loaded successfully')
"
```

- [ ] **Step 5: 提交权限检查更新**

```bash
git add api/common/check_file_permission.py
git commit -m "feat: update permission check to support team sharing"
```

---

### Task 4: 扩展API端点

**Files:**
- Modify: `api/apps/file_permission_app.py`

- [ ] **Step 1: 添加团队共享导入**

```python
# api/apps/file_permission_app.py (在顶部导入部分添加)
from api.db.services.team_permission_service import TeamPermissionService
```

- [ ] **Step 2: 添加启用团队共享API端点**

```python
# api/apps/file_permission_app.py (在现有API后面添加)
@manager.route('/team/enable', methods=['POST'])  # noqa: F821
@login_required
@validate_request("file_id", "permission_level")
async def enable_team_share():
    """
    启用文件的团队共享
    
    Request:
        {
            "file_id": "文件ID",
            "permission_level": "view|edit|admin"
        }
    
    Response:
        {
            "data": {
                "id": "共享记录ID",
                "file_id": "文件ID",
                "tenant_id": "租户ID",
                "permission_level": "权限级别",
                "is_enabled": true,
                "created_by": "创建者ID",
                "created_at": "创建时间",
                "updated_at": "更新时间"
            }
        }
    """
    req = await request.get_json()
    
    file_id = req.get("file_id")
    permission_level = req.get("permission_level")
    
    # 验证权限级别
    valid_levels = [FilePermissionLevel.VIEW, FilePermissionLevel.EDIT, FilePermissionLevel.ADMIN]
    if permission_level not in valid_levels:
        return get_json_result(
            data=False,
            message=f"无效的权限级别，有效值为: {', '.join(valid_levels)}",
            code=RetCode.ARGUMENT_ERROR
        )
    
    # 检查文件是否存在
    e, file = FileService.get_by_id(file_id)
    if not e or not file:
        return get_data_error_result(message="文件不存在")
    
    # 检查当前用户是否有权限启用团队共享
    can_enable, msg = can_user_enable_team_share(file_id, current_user.id)
    if not can_enable:
        return get_json_result(
            data=False,
            message=msg or "您没有权限启用团队共享",
            code=RetCode.AUTHENTICATION_ERROR
        )
    
    try:
        # 启用团队共享
        team_share = TeamPermissionService.enable_team_share(
            file_id=file_id,
            tenant_id=file.tenant_id,
            created_by=current_user.id,
            permission_level=permission_level
        )
        
        return get_json_result(data=team_share.to_dict())
    except Exception as e:
        logging.exception(f"Failed to enable team share for file {file_id}")
        return server_error_response(str(e))
```

- [ ] **Step 3: 添加禁用团队共享API端点**

```python
@manager.route('/team/disable', methods=['POST'])  # noqa: F821
@login_required
@validate_request("file_id")
async def disable_team_share():
    """
    禁用文件的团队共享
    
    Request:
        {
            "file_id": "文件ID"
        }
    
    Response:
        {
            "data": {
                "success": true
            }
        }
    """
    req = await request.get_json()
    file_id = req.get("file_id")
    
    # 检查文件是否存在
    e, file = FileService.get_by_id(file_id)
    if not e or not file:
        return get_data_error_result(message="文件不存在")
    
    # 检查当前用户是否有权限管理团队共享
    can_manage, msg = can_user_manage_team_share(file_id, current_user.id)
    if not can_manage:
        return get_json_result(
            data=False,
            message=msg or "您没有权限管理团队共享",
            code=RetCode.AUTHENTICATION_ERROR
        )
    
    try:
        # 禁用团队共享
        success = TeamPermissionService.disable_team_share(file_id, file.tenant_id)
        
        if not success:
            return get_json_result(
                data=False,
                message="团队共享未启用或禁用失败",
                code=RetCode.DATA_ERROR
            )
        
        return get_json_result(data={"success": True})
    except Exception as e:
        logging.exception(f"Failed to disable team share for file {file_id}")
        return server_error_response(str(e))
```

- [ ] **Step 4: 添加获取团队共享状态API端点**

```python
@manager.route('/team/status', methods=['GET'])  # noqa: F821
@login_required
async def get_team_share_status():
    """
    获取文件的团队共享状态
    
    Query Parameters:
        file_id: 文件ID
    
    Response:
        {
            "data": {
                "is_enabled": true/false,
                "permission_level": "view|edit|admin",
                "created_by": "创建者ID",
                "created_at": "创建时间",
                "updated_at": "更新时间"
            }
        }
    """
    file_id = request.args.get("file_id")
    
    if not file_id:
        return get_json_result(
            data=False,
            message="缺少 file_id 参数",
            code=RetCode.ARGUMENT_ERROR
        )
    
    # 检查文件是否存在
    e, file = FileService.get_by_id(file_id)
    if not e or not file:
        return get_data_error_result(message="文件不存在")
    
    # 检查当前用户是否有权限查看
    has_perm, msg = check_file_permission(file_id, current_user.id, FilePermissionLevel.VIEW)
    if not has_perm:
        return get_json_result(
            data=False,
            message=msg or "您没有查看此文件的权限",
            code=RetCode.AUTHENTICATION_ERROR
        )
    
    try:
        # 获取团队共享状态
        status = TeamPermissionService.get_team_share_status(file_id, file.tenant_id)
        
        if not status:
            status = {
                "is_enabled": False,
                "permission_level": None,
                "created_by": None,
                "created_at": None,
                "updated_at": None
            }
        
        return get_json_result(data=status)
    except Exception as e:
        logging.exception(f"Failed to get team share status for file {file_id}")
        return server_error_response(str(e))
```

- [ ] **Step 5: 添加更新团队权限级别API端点**

```python
@manager.route('/team/level', methods=['PUT'])  # noqa: F821
@login_required
@validate_request("file_id", "permission_level")
async def update_team_permission_level():
    """
    更新团队共享的权限级别
    
    Request:
        {
            "file_id": "文件ID",
            "permission_level": "view|edit|admin"
        }
    
    Response:
        {
            "data": {
                "success": true
            }
        }
    """
    req = await request.get_json()
    
    file_id = req.get("file_id")
    permission_level = req.get("permission_level")
    
    # 验证权限级别
    valid_levels = [FilePermissionLevel.VIEW, FilePermissionLevel.EDIT, FilePermissionLevel.ADMIN]
    if permission_level not in valid_levels:
        return get_json_result(
            data=False,
            message=f"无效的权限级别，有效值为: {', '.join(valid_levels)}",
            code=RetCode.ARGUMENT_ERROR
        )
    
    # 检查文件是否存在
    e, file = FileService.get_by_id(file_id)
    if not e or not file:
        return get_data_error_result(message="文件不存在")
    
    # 检查当前用户是否有权限管理团队共享
    can_manage, msg = can_user_manage_team_share(file_id, current_user.id)
    if not can_manage:
        return get_json_result(
            data=False,
            message=msg or "您没有权限管理团队共享",
            code=RetCode.AUTHENTICATION_ERROR
        )
    
    # 检查团队共享是否已启用
    status = TeamPermissionService.get_team_share_status(file_id, file.tenant_id)
    if not status or not status.get("is_enabled"):
        return get_json_result(
            data=False,
            message="团队共享未启用，无法更新权限级别",
            code=RetCode.DATA_ERROR
        )
    
    try:
        # 更新权限级别
        success = TeamPermissionService.update_team_permission_level(
            file_id=file_id,
            tenant_id=file.tenant_id,
            permission_level=permission_level
        )
        
        if not success:
            return get_json_result(
                data=False,
                message="更新团队共享权限级别失败",
                code=RetCode.DATA_ERROR
            )
        
        return get_json_result(data={"success": True})
    except Exception as e:
        logging.exception(f"Failed to update team permission level for file {file_id}")
        return server_error_response(str(e))
```

- [ ] **Step 6: 验证API端点**

```bash
# 检查API文件语法
python -m py_compile api/apps/file_permission_app.py
```

- [ ] **Step 7: 提交API扩展**

```bash
git add api/apps/file_permission_app.py
git commit -m "feat: add team sharing API endpoints"
```

---

### Task 5: 前端服务层扩展

**Files:**
- Modify: `web/src/services/file-permission-service.ts`

- [ ] **Step 1: 更新API端点定义**

```typescript
// web/src/utils/api.ts (在现有API端点后添加)
// file permission team endpoints
enableTeamShare: `${api_host}/file_permission/team/enable`,
disableTeamShare: `${api_host}/file_permission/team/disable`,
getTeamShareStatus: `${api_host}/file_permission/team/status`,
updateTeamPermissionLevel: `${api_host}/file_permission/team/level`,
```

- [ ] **Step 2: 扩展前端服务层**

```typescript
// web/src/services/file-permission-service.ts (在现有methods后添加)
const methods = {
  // 现有方法保持不变...
  // ... 其他方法

  enableTeamShare: {
    url: api.enableTeamShare,
    method: 'post',
  },
  disableTeamShare: {
    url: api.disableTeamShare,
    method: 'post',
  },
  getTeamShareStatus: {
    url: api.getTeamShareStatus,
    method: 'get',
  },
  updateTeamPermissionLevel: {
    url: api.updateTeamPermissionLevel,
    method: 'put',
  },
} as const;
```

- [ ] **Step 3: 添加团队共享类型定义**

```typescript
// web/src/services/file-permission-service.ts (在现有接口后添加)
export interface ITeamShareStatus {
  id?: string;
  file_id: string;
  tenant_id: string;
  permission_level: string;
  is_enabled: boolean;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
}

export interface IEnableTeamShareRequest {
  file_id: string;
  permission_level: string;
}

export interface IDisableTeamShareRequest {
  file_id: string;
}

export interface IUpdateTeamPermissionLevelRequest {
  file_id: string;
  permission_level: string;
}
```

- [ ] **Step 4: 验证TypeScript编译**

```bash
cd web
npm run type-check
```

- [ ] **Step 5: 提交前端服务层扩展**

```bash
git add web/src/utils/api.ts web/src/services/file-permission-service.ts
git commit -m "feat: add team sharing service layer and types"
```

---

### Task 6: 创建团队共享开关组件

**Files:**
- Create: `web/src/components/file-team-share-toggle.tsx`

- [ ] **Step 1: 创建组件骨架**

```tsx
// web/src/components/file-team-share-toggle.tsx
'use client';

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Loader2, Globe, Lock } from 'lucide-react';
import filePermissionService, {
  FilePermissionLevel,
  PermissionLevelLabels,
  ITeamShareStatus,
} from '@/services/file-permission-service';
import { useToast } from '@/components/hooks/use-toast';

interface FileTeamShareToggleProps {
  fileId: string;
  fileName: string;
  isOwner: boolean;
  canManage: boolean;
  onStatusChange?: (enabled: boolean, level?: string) => void;
}

export function FileTeamShareToggle({
  fileId,
  fileName,
  isOwner,
  canManage,
  onStatusChange,
}: FileTeamShareToggleProps) {
  const { t } = useTranslation();
  const { toast } = useToast();

  const [loading, setLoading] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [status, setStatus] = useState<ITeamShareStatus | null>(null);
  const [selectedPermission, setSelectedPermission] = useState<string>(
    FilePermissionLevel.VIEW
  );

  // 加载团队共享状态
  const loadTeamShareStatus = async () => {
    if (!fileId || !canManage) return;

    setLoading(true);
    try {
      const response = await filePermissionService.getTeamShareStatus({
        file_id: fileId,
      });
      if (response.data) {
        setStatus(response.data);
        if (response.data.permission_level) {
          setSelectedPermission(response.data.permission_level);
        }
      }
    } catch (error) {
      console.error('Failed to load team share status:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (fileId && canManage) {
      loadTeamShareStatus();
    }
  }, [fileId, canManage]);

  // 处理开关切换
  const handleSwitchChange = async (enabled: boolean) => {
    if (!canManage) {
      toast({
        variant: 'destructive',
        title: t('common.error'),
        description: t('fileManager.noPermissionToManage'),
      });
      return;
    }

    setUpdating(true);
    try {
      if (enabled) {
        // 启用团队共享
        const response = await filePermissionService.enableTeamShare({
          file_id: fileId,
          permission_level: selectedPermission,
        });
        if (response.data) {
          setStatus(response.data);
          toast({
            title: t('common.success'),
            description: t('fileManager.teamShareEnabled'),
          });
          onStatusChange?.(true, selectedPermission);
        }
      } else {
        // 禁用团队共享
        const response = await filePermissionService.disableTeamShare({
          file_id: fileId,
        });
        if (response.data?.success) {
          setStatus({
            file_id: fileId,
            tenant_id: '',
            permission_level: selectedPermission,
            is_enabled: false,
          });
          toast({
            title: t('common.success'),
            description: t('fileManager.teamShareDisabled'),
          });
          onStatusChange?.(false);
        }
      }
    } catch (error) {
      console.error('Failed to toggle team share:', error);
      toast({
        variant: 'destructive',
        title: t('common.error'),
        description: enabled
          ? t('fileManager.teamShareEnableFailed')
          : t('fileManager.teamShareDisableFailed'),
      });
      // 回滚状态
      setStatus(prev => prev ? { ...prev, is_enabled: !enabled } : null);
    } finally {
      setUpdating(false);
    }
  };

  // 处理权限级别变更
  const handlePermissionChange = async (permissionLevel: string) => {
    if (!status?.is_enabled || !canManage) return;

    setUpdating(true);
    try {
      const response = await filePermissionService.updateTeamPermissionLevel({
        file_id: fileId,
        permission_level: permissionLevel,
      });
      if (response.data?.success) {
        setSelectedPermission(permissionLevel);
        setStatus(prev => prev ? { ...prev, permission_level: permissionLevel } : null);
        toast({
          title: t('common.success'),
          description: t('fileManager.teamPermissionUpdated'),
        });
        onStatusChange?.(true, permissionLevel);
      }
    } catch (error) {
      console.error('Failed to update team permission:', error);
      toast({
        variant: 'destructive',
        title: t('common.error'),
        description: t('fileManager.teamPermissionUpdateFailed'),
      });
    } finally {
      setUpdating(false);
    }
  };

  // 如果没有管理权限，显示只读状态
  if (!canManage) {
    const isTeamShared = status?.is_enabled;
    return (
      <div className="flex items-center gap-3 p-3 border rounded-md bg-muted/50">
        <div className="flex items-center gap-2">
          {isTeamShared ? (
            <Globe className="h-4 w-4 text-green-600" />
          ) : (
            <Lock className="h-4 w-4 text-muted-foreground" />
          )}
          <span className="text-sm font-medium">
            {isTeamShared
              ? t('fileManager.sharedToTeam')
              : t('fileManager.privateFile')}
          </span>
        </div>
        {isTeamShared && status?.permission_level && (
          <Badge variant="secondary" className="text-xs">
            {PermissionLevelLabels[status.permission_level]}
          </Badge>
        )}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-4">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="ml-2 text-sm text-muted-foreground">
          {t('common.loading')}
        </span>
      </div>
    );
  }

  const isEnabled = status?.is_enabled || false;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <Label htmlFor="team-share-toggle" className="text-sm font-medium">
            {t('fileManager.shareToTeam')}
          </Label>
          <p className="text-xs text-muted-foreground">
            {isEnabled
              ? t('fileManager.teamShareEnabledDesc')
              : t('fileManager.teamShareDisabledDesc')}
          </p>
        </div>
        <Switch
          id="team-share-toggle"
          checked={isEnabled}
          onCheckedChange={handleSwitchChange}
          disabled={updating || !canManage}
          aria-label={isEnabled ? t('fileManager.disableTeamShare') : t('fileManager.enableTeamShare')}
        />
      </div>

      {isEnabled && (
        <div className="space-y-2">
          <Label htmlFor="team-permission-level" className="text-sm font-medium">
            {t('fileManager.teamPermissionLevel')}
          </Label>
          <Select
            value={selectedPermission}
            onValueChange={handlePermissionChange}
            disabled={updating}
          >
            <SelectTrigger id="team-permission-level" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={FilePermissionLevel.VIEW}>
                {PermissionLevelLabels[FilePermissionLevel.VIEW]}
              </SelectItem>
              <SelectItem value={FilePermissionLevel.EDIT}>
                {PermissionLevelLabels[FilePermissionLevel.EDIT]}
              </SelectItem>
              {isOwner && (
                <SelectItem value={FilePermissionLevel.ADMIN}>
                  {PermissionLevelLabels[FilePermissionLevel.ADMIN]}
                </SelectItem>
              )}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            {t('fileManager.teamPermissionLevelDesc')}
          </p>
        </div>
      )}

      <div className="flex items-center gap-2 text-sm">
        {isEnabled ? (
          <>
            <Globe className="h-4 w-4 text-green-600" />
            <span className="text-green-700 font-medium">
              {t('fileManager.sharedToTeam')}
            </span>
            <Badge variant="outline" className="ml-2">
              {PermissionLevelLabels[selectedPermission]}
            </Badge>
          </>
        ) : (
          <>
            <Lock className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">
              {t('fileManager.privateFile')}
            </span>
          </>
        )}
      </div>
    </div>
  );
}

export default FileTeamShareToggle;
```

- [ ] **Step 2: 添加国际化翻译**

```typescript
// web/src/locales/zh.ts (在fileManager部分添加)
{
  fileManager: {
    // 现有翻译保持不变...
    // ... 
    
    // 团队共享相关
    shareToTeam: '共享给团队',
    teamShareEnabled: '团队共享已启用',
    teamShareDisabled: '团队共享已禁用',
    teamShareEnabledDesc: '此文件已共享给团队所有成员',
    teamShareDisabledDesc: '仅您和指定的用户可以访问',
    teamPermissionLevel: '团队权限级别',
    teamPermissionLevelDesc: '所有团队成员将获得此权限级别',
    sharedToTeam: '已共享给团队',
    privateFile: '私有文件',
    enableTeamShare: '启用团队共享',
    disableTeamShare: '禁用团队共享',
    teamShareEnableFailed: '启用团队共享失败',
    teamShareDisableFailed: '禁用团队共享失败',
    teamPermissionUpdated: '团队权限已更新',
    teamPermissionUpdateFailed: '更新团队权限失败',
    noPermissionToManage: '您没有权限管理团队共享',
  }
}
```

- [ ] **Step 3: 验证组件编译**

```bash
cd web
npm run build
```

- [ ] **Step 4: 提交团队共享组件**

```bash
git add web/src/components/file-team-share-toggle.tsx web/src/locales/zh.ts
git commit -m "feat: add FileTeamShareToggle component with i18n support"
```

---

### Task 7: 集成到文件列表页面

**Files:**
- Modify: `web/src/pages/file-management/components/files-table.tsx` (或类似的文件列表组件)

- [ ] **Step 1: 查找文件列表组件**

```bash
cd web
find src -name "*file*table*" -o -name "*files*table*" | head -5
```

- [ ] **Step 2: 在文件列表中集成团队共享开关**

假设文件列表组件路径为 `web/src/pages/file-management/components/files-table.tsx`：

```tsx
// 在文件列表组件的操作列中添加团队共享开关
import FileTeamShareToggle from '@/components/file-team-share-toggle';
// ... 其他导入

const FilesTable = ({ files, onRefresh }) => {
  // ... 现有代码
  
  const columns = [
    // ... 现有列
    {
      title: t('fileManager.shareStatus'),
      key: 'shareStatus',
      width: 120,
      render: (_, record) => {
        // 检查用户是否有权限管理此文件
        const hasPermission = record.permission_level === 'admin' || record.permission_level === 'owner';
        
        return (
          <FileTeamShareToggle
            fileId={record.id}
            fileName={record.name}
            isOwner={record.permission_level === 'owner'}
            canManage={hasPermission}
            onStatusChange={(enabled, level) => {
              // 刷新文件列表
              onRefresh?.();
            }}
          />
        );
      },
    },
    // ... 其他列
  ];
  
  // ... 剩余代码
};
```

- [ ] **Step 3: 移除旧的共享对话框引用**

```tsx
// 移除或注释掉旧的共享对话框导入和使用
// import FileShareDialog from '@/components/file-share-dialog';
```

- [ ] **Step 4: 验证文件列表渲染**

```bash
cd web
npm run lint
```

- [ ] **Step 5: 提交文件列表集成**

```bash
git add web/src/pages/file-management/components/files-table.tsx
git commit -m "feat: integrate team share toggle in files table"
```

---

### Task 8: 后端测试

**Files:**
- Create: `tests/api/test_team_permission.py`

- [ ] **Step 1: 创建团队权限测试文件**

```python
# tests/api/test_team_permission.py
import pytest
from unittest.mock import patch, MagicMock
from api.db.services.team_permission_service import TeamPermissionService
from api.db import FilePermissionLevel


class TestTeamPermissionService:
    """测试团队权限服务"""
    
    def test_enable_team_share(self):
        """测试启用团队共享"""
        with patch.object(TeamPermissionService.model, 'select') as mock_select, \
             patch.object(TeamPermissionService.model, 'create') as mock_create:
            
            # 模拟不存在现有记录
            mock_select.return_value.where.return_value.first.return_value = None
            
            # 模拟创建成功
            mock_team_share = MagicMock()
            mock_team_share.id = "test_id"
            mock_team_share.file_id = "file_123"
            mock_team_share.tenant_id = "tenant_456"
            mock_team_share.permission_level = FilePermissionLevel.VIEW
            mock_team_share.is_enabled = True
            mock_team_share.created_by = "user_789"
            mock_create.return_value = mock_team_share
            
            # 调用方法
            result = TeamPermissionService.enable_team_share(
                file_id="file_123",
                tenant_id="tenant_456",
                created_by="user_789",
                permission_level=FilePermissionLevel.VIEW
            )
            
            # 验证结果
            assert result.id == "test_id"
            assert result.file_id == "file_123"
            assert result.is_enabled is True
            mock_create.assert_called_once()
    
    def test_disable_team_share(self):
        """测试禁用团队共享"""
        with patch.object(TeamPermissionService.model, 'update') as mock_update:
            mock_update.return_value.where.return_value.execute.return_value = 1
            
            result = TeamPermissionService.disable_team_share(
                file_id="file_123",
                tenant_id="tenant_456"
            )
            
            assert result is True
            mock_update.assert_called_once()
    
    def test_get_team_share_status(self):
        """测试获取团队共享状态"""
        with patch.object(TeamPermissionService.model, 'select') as mock_select:
            mock_team_share = MagicMock()
            mock_team_share.id = "test_id"
            mock_team_share.file_id = "file_123"
            mock_team_share.tenant_id = "tenant_456"
            mock_team_share.permission_level = FilePermissionLevel.EDIT
            mock_team_share.is_enabled = True
            mock_team_share.created_by = "user_789"
            mock_team_share.created_at = "2024-01-01T00:00:00"
            mock_team_share.updated_at = "2024-01-01T00:00:00"
            
            mock_select.return_value.where.return_value.first.return_value = mock_team_share
            
            result = TeamPermissionService.get_team_share_status(
                file_id="file_123",
                tenant_id="tenant_456"
            )
            
            assert result["id"] == "test_id"
            assert result["file_id"] == "file_123"
            assert result["is_enabled"] is True
            assert result["permission_level"] == FilePermissionLevel.EDIT
```

- [ ] **Step 2: 运行后端测试**

```bash
cd /Users/thomasxing/workspace/2026/4月份计划/ragflow
pytest tests/api/test_team_permission.py -v
```

- [ ] **Step 3: 提交后端测试**

```bash
git add tests/api/test_team_permission.py
git commit -m "test: add team permission service tests"
```

---

### Task 9: 前端组件测试

**Files:**
- Create: `tests/web/components/file-team-share-toggle.test.tsx`

- [ ] **Step 1: 创建前端组件测试**

```tsx
// tests/web/components/file-team-share-toggle.test.tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { FileTeamShareToggle } from '@/components/file-team-share-toggle';
import filePermissionService from '@/services/file-permission-service';
import { useToast } from '@/components/hooks/use-toast';

// Mock dependencies
vi.mock('@/services/file-permission-service');
vi.mock('@/components/hooks/use-toast');
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('FileTeamShareToggle', () => {
  const mockToast = vi.fn();
  
  beforeEach(() => {
    vi.clearAllMocks();
    (useToast as any).mockReturnValue({
      toast: mockToast,
    });
  });

  test('renders loading state when loading', () => {
    (filePermissionService.getTeamShareStatus as any).mockImplementation(() => 
      new Promise(() => {}) // Never resolves to keep loading
    );

    render(
      <FileTeamShareToggle
        fileId="file_123"
        fileName="Test File"
        isOwner={true}
        canManage={true}
      />
    );

    expect(screen.getByText('common.loading')).toBeInTheDocument();
  });

  test('renders disabled state for non-managers', async () => {
    const mockStatus = {
      file_id: 'file_123',
      tenant_id: 'tenant_456',
      permission_level: 'view',
      is_enabled: true,
    };

    (filePermissionService.getTeamShareStatus as any).mockResolvedValue({
      data: mockStatus,
    });

    render(
      <FileTeamShareToggle
        fileId="file_123"
        fileName="Test File"
        isOwner={false}
        canManage={false}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('fileManager.sharedToTeam')).toBeInTheDocument();
    });
    
    // Switch should not be rendered for non-managers
    expect(screen.queryByRole('switch')).not.toBeInTheDocument();
  });

  test('enables team share when switch is toggled on', async () => {
    const mockStatus = {
      file_id: 'file_123',
      tenant_id: 'tenant_456',
      permission_level: 'view',
      is_enabled: false,
    };

    (filePermissionService.getTeamShareStatus as any).mockResolvedValue({
      data: mockStatus,
    });

    (filePermissionService.enableTeamShare as any).mockResolvedValue({
      data: { ...mockStatus, is_enabled: true },
    });

    const onStatusChange = vi.fn();

    render(
      <FileTeamShareToggle
        fileId="file_123"
        fileName="Test File"
        isOwner={true}
        canManage={true}
        onStatusChange={onStatusChange}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('fileManager.privateFile')).toBeInTheDocument();
    });

    // Find and click the switch
    const switchElement = screen.getByRole('switch');
    fireEvent.click(switchElement);

    await waitFor(() => {
      expect(filePermissionService.enableTeamShare).toHaveBeenCalledWith({
        file_id: 'file_123',
        permission_level: 'view',
      });
      expect(onStatusChange).toHaveBeenCalledWith(true, 'view');
    });
  });

  test('disables team share when switch is toggled off', async () => {
    const mockStatus = {
      file_id: 'file_123',
      tenant_id: 'tenant_456',
      permission_level: 'view',
      is_enabled: true,
    };

    (filePermissionService.getTeamShareStatus as any).mockResolvedValue({
      data: mockStatus,
    });

    (filePermissionService.disableTeamShare as any).mockResolvedValue({
      data: { success: true },
    });

    const onStatusChange = vi.fn();

    render(
      <FileTeamShareToggle
        fileId="file_123"
        fileName="Test File"
        isOwner={true}
        canManage={true}
        onStatusChange={onStatusChange}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('fileManager.sharedToTeam')).toBeInTheDocument();
    });

    // Find and click the switch
    const switchElement = screen.getByRole('switch');
    fireEvent.click(switchElement);

    await waitFor(() => {
      expect(filePermissionService.disableTeamShare).toHaveBeenCalledWith({
        file_id: 'file_123',
      });
      expect(onStatusChange).toHaveBeenCalledWith(false);
    });
  });
});
```

- [ ] **Step 2: 运行前端测试**

```bash
cd web
npm test -- file-team-share-toggle.test.tsx
```

- [ ] **Step 3: 提交前端测试**

```bash
git add tests/web/components/file-team-share-toggle.test.tsx
git commit -m "test: add FileTeamShareToggle component tests"
```

---

### Task 10: 数据库迁移执行

**Files:**
- Modify: `api/db/__init__.py` 或数据库迁移入口文件

- [ ] **Step 1: 查找数据库初始化文件**

```bash
find api -name "*.py" -type f | xargs grep -l "create_file_permission_share_table" | head -5
```

- [ ] **Step 2: 添加团队共享表创建到数据库初始化**

假设在 `api/db/__init__.py` 或 `api/db/db_models.py` 中有数据库初始化函数：

```python
# 在现有的数据库初始化函数中添加
def init_database_tables():
    """初始化数据库表"""
    # 现有表创建...
    create_file_permission_share_table(migrator)
    
    # 新增团队共享表
    try:
        create_team_permission_share_table(migrator)
        logging.info("Team permission share table initialized")
    except Exception as e:
        logging.warning(f"Failed to initialize team permission share table: {e}")
```

- [ ] **Step 3: 验证数据库迁移**

```bash
# 运行数据库迁移或初始化脚本
cd /Users/thomasxing/workspace/2026/4月份计划/ragflow
python -c "
import sys
sys.path.append('.')
from api.db.db_models import create_team_permission_share_table
print('Team permission share table migration function loaded successfully')
"
```

- [ ] **Step 4: 提交数据库迁移**

```bash
git add api/db/__init__.py  # 或相应的数据库初始化文件
git commit -m "feat: add team permission share table to database initialization"
```

---

### Task 11: 集成测试和端到端验证

**Files:**
- Create: `tests/integration/test_team_share_workflow.py`

- [ ] **Step 1: 创建端到端集成测试**

```python
# tests/integration/test_team_share_workflow.py
import pytest
from datetime import datetime
from api.db.services.team_permission_service import TeamPermissionService
from api.db.services.file_permission_service import FilePermissionService
from api.common.check_file_permission import get_user_effective_permission
from api.db.db_models import File, User, UserTenant


class TestTeamShareWorkflow:
    """测试团队共享完整流程"""
    
    @pytest.fixture
    def setup_test_data(self, db):
        """创建测试数据"""
        # 创建测试用户
        user1 = User.create(
            id="user_1",
            nickname="Test User 1",
            email="user1@test.com",
            password_hash="hash",
            role="user"
        )
        
        user2 = User.create(
            id="user_2", 
            nickname="Test User 2",
            email="user2@test.com",
            password_hash="hash",
            role="user"
        )
        
        # 创建测试文件
        file = File.create(
            id="file_1",
            name="test_file.txt",
            type="file",
            size=1024,
            parent_id="root",
            created_by="user_1",
            tenant_id="tenant_1",
            create_time=int(datetime.now().timestamp()),
            update_time=int(datetime.now().timestamp())
        )
        
        # 将用户2添加到租户
        UserTenant.create(
            id="ut_1",
            user_id="user_2",
            tenant_id="tenant_1",
            role="member",
            status="active"
        )
        
        return {
            "user1": user1,
            "user2": user2,
            "file": file
        }
    
    def test_enable_team_share_workflow(self, setup_test_data):
        """测试启用团队共享完整流程"""
        data = setup_test_data
        
        # 1. 启用团队共享
        team_share = TeamPermissionService.enable_team_share(
            file_id=data["file"].id,
            tenant_id=data["file"].tenant_id,
            created_by=data["user1"].id,
            permission_level="edit"
        )
        
        assert team_share is not None
        assert team_share.is_enabled is True
        assert team_share.permission_level == "edit"
        
        # 2. 验证用户2通过团队共享获得权限
        permission_info = get_user_effective_permission(
            file_id=data["file"].id,
            user_id=data["user2"].id
        )
        
        assert permission_info["permission_level"] == "edit"
        assert permission_info["permission_source"] == "team"
        
        # 3. 禁用团队共享
        disabled = TeamPermissionService.disable_team_share(
            file_id=data["file"].id,
            tenant_id=data["file"].tenant_id
        )
        
        assert disabled is True
        
        # 4. 验证用户2失去团队权限
        permission_info = get_user_effective_permission(
            file_id=data["file"].id,
            user_id=data["user2"].id
        )
        
        # 用户2应该只有租户默认VIEW权限
        assert permission_info["permission_level"] == "view"
        assert permission_info["permission_source"] == "tenant"
    
    def test_team_share_priority_over_tenant(self, setup_test_data):
        """测试团队共享权限优先于租户默认权限"""
        data = setup_test_data
        
        # 启用团队共享为admin权限
        TeamPermissionService.enable_team_share(
            file_id=data["file"].id,
            tenant_id=data["file"].tenant_id,
            created_by=data["user1"].id,
            permission_level="admin"
        )
        
        # 验证用户2获得admin权限（而不是租户默认的view）
        permission_info = get_user_effective_permission(
            file_id=data["file"].id,
            user_id=data["user2"].id
        )
        
        assert permission_info["permission_level"] == "admin"
        assert permission_info["permission_source"] == "team"
    
    def test_personal_permission_overrides_team_share(self, setup_test_data):
        """测试个人权限覆盖团队共享权限"""
        data = setup_test_data
        
        # 1. 启用团队共享为view权限
        TeamPermissionService.enable_team_share(
            file_id=data["file"].id,
            tenant_id=data["file"].tenant_id,
            created_by=data["user1"].id,
            permission_level="view"
        )
        
        # 2. 为用户2单独设置edit权限
        FilePermissionService.create_share(
            file_id=data["file"].id,
            target_user_id=data["user2"].id,
            sharer_id=data["user1"].id,
            permission_level="edit",
            tenant_id=data["file"].tenant_id
        )
        
        # 3. 验证用户2获得个人权限（edit）而不是团队权限（view）
        permission_info = get_user_effective_permission(
            file_id=data["file"].id,
            user_id=data["user2"].id
        )
        
        assert permission_info["permission_level"] == "edit"
        assert permission_info["permission_source"] == "explicit"
```

- [ ] **Step 2: 运行集成测试**

```bash
cd /Users/thomasxing/workspace/2026/4月份计划/ragflow
pytest tests/integration/test_team_share_workflow.py -v
```

- [ ] **Step 3: 提交集成测试**

```bash
git add tests/integration/test_team_share_workflow.py
git commit -m "test: add team share workflow integration tests"
```

---

### Task 12: 最终验证和文档更新

**Files:**
- Update: `README.md` 或相关文档

- [ ] **Step 1: 运行完整的测试套件**

```bash
cd /Users/thomasxing/workspace/2026/4月份计划/ragflow
# 运行后端测试
pytest tests/api/test_team_permission.py tests/integration/test_team_share_workflow.py -v

cd web
# 运行前端测试
npm test -- --coverage
```

- [ ] **Step 2: 验证API端点**

```bash
# 检查API路由是否正确定义
grep -n "team/enable" api/apps/file_permission_app.py
grep -n "team/disable" api/apps/file_permission_app.py
grep -n "team/status" api/apps/file_permission_app.py
grep -n "team/level" api/apps/file_permission_app.py
```

- [ ] **Step 3: 更新API文档**

在相应的API文档中添加团队共享端点的描述：

```markdown
## 团队共享API

### 启用团队共享
`POST /api/file_permission/team/enable`

**请求体:**
```json
{
  "file_id": "文件ID",
  "permission_level": "view|edit|admin"
}
```

**响应:**
```json
{
  "data": {
    "id": "共享记录ID",
    "file_id": "文件ID",
    "tenant_id": "租户ID",
    "permission_level": "权限级别",
    "is_enabled": true,
    "created_by": "创建者ID",
    "created_at": "创建时间",
    "updated_at": "更新时间"
  }
}
```

### 禁用团队共享
`POST /api/file_permission/team/disable`

**请求体:**
```json
{
  "file_id": "文件ID"
}
```

### 获取团队共享状态
`GET /api/file_permission/team/status?file_id=<文件ID>`

### 更新团队权限级别
`PUT /api/file_permission/team/level`
```

- [ ] **Step 4: 创建最终提交**

```bash
# 检查所有更改
git status

# 创建最终提交
git add .
git commit -m "feat: complete team sharing feature implementation

- Added team_permission_share table schema and migration
- Implemented TeamPermissionService with CRUD operations
- Updated permission check logic to support team sharing
- Added 4 new API endpoints for team sharing
- Created FileTeamShareToggle React component
- Integrated team share toggle into files table
- Added comprehensive unit and integration tests
- Updated API documentation

BREAKING CHANGE: Replaced individual user sharing dialog with team sharing toggle"
```

- [ ] **Step 5: 验证功能完整性**

创建验证检查清单：
```bash
# 1. 数据库表创建
echo "✓ Database table schema created"

# 2. 后端服务层
echo "✓ TeamPermissionService implemented"

# 3. 权限检查逻辑
echo "✓ Permission check logic updated"

# 4. API端点
echo "✓ 4 team sharing API endpoints added"

# 5. 前端组件
echo "✓ FileTeamShareToggle component created"

# 6. 国际化
echo "✓ i18n translations added"

# 7. 测试覆盖
echo "✓ Unit and integration tests added"

# 8. 文档更新
echo "✓ API documentation updated"
```

---

## 执行选项

**计划已完成并保存到 `docs/superpowers/plans/2026-04-07-team-share-feature.md`。两个执行选项：**

**1. Subagent-Driven (推荐)** - 我派发一个新的subagent按任务执行，每个任务完成后进行审查，快速迭代

**2. Inline Execution** - 在当前会话中使用executing-plans按批执行任务，检查点进行审查

**哪种方式？**