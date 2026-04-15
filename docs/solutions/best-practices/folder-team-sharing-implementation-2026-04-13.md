---
title: 文件夹团队共享功能开发实践
date: 2026-04-13
category: best-practices
module: file-manager
problem_type: best_practice
component: frontend_stimulus
severity: medium
applies_when:
  - 为相似但不同的资源类型添加相同功能
  - 现有组件已有成熟的业务逻辑，但UI需要微调
  - 多种资源类型需要共享相同的API调用链路
tags:
  - react
  - typescript
  - component-design
  - api-integration
  - team-sharing
---

# 文件夹团队共享功能开发实践

## Context

RAGFlow 原有的文件团队共享功能（`FileTeamShareToggle`）仅支持单个文件的权限管理。随着用户需求的增长，需要为文件夹也提供类似的团队共享能力，允许用户对整个文件夹设置团队访问权限。

开发过程中发现，直接复用文件共享组件会导致 UI 和逻辑不匹配的问题，需要针对文件夹特性进行适配。

## Guidance

### 1. 基于现有组件进行适配扩展

当需要为新类型添加类似功能时，应基于现有组件创建新的专用组件，而非强行复用：

```tsx
// web/src/components/folder-team-share-toggle.tsx
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
import { Loader2, Globe, Lock, Folder } from 'lucide-react';
import filePermissionService, {
  FilePermissionLevel,
  PermissionLevelLabels,
  PermissionLevelDescriptions,
  type ITeamShareStatus,
} from '@/services/file-permission-service';
import { useToast } from '@/components/hooks/use-toast';

interface FolderTeamShareToggleProps {
  folderId: string;
  folderName: string;
  folderType?: 'folder' | 'directory';
  isOwner: boolean;
  canManage: boolean;
  tenantId: string;
  onStatusChange?: (enabled: boolean, level?: string) => void;
}

export function FolderTeamShareToggle({
  folderId,
  folderName: _folderName,
  folderType = 'folder',
  isOwner,
  canManage,
  tenantId,
  onStatusChange,
}: FolderTeamShareToggleProps) {
  const { t } = useTranslation();
  const { toast } = useToast();

  const [loading, setLoading] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [status, setStatus] = useState<ITeamShareStatus | null>(null);
  const [selectedPermission, setSelectedPermission] = useState<string>(
    FilePermissionLevel.VIEW
  );

  // ... 组件实现
}
```

### 2. 根据资源类型条件渲染不同组件

在集成点使用条件判断，根据资源类型显示对应组件：

```tsx
// web/src/pages/files/action-cell.tsx
import { FileTeamShareToggle } from '@/components/file-team-share-toggle';
import { FolderTeamShareToggle } from '@/components/folder-team-share-toggle';

export function ActionCell({ record }: { record: IFile }) {
  const isFolder = isFolderType(record.type);

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="transparent" size="icon-sm">
          <Share2 />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80">
        {isFolder ? (
          <FolderTeamShareToggle
            folderId={documentId}
            folderName={name}
            isOwner={record.tenant_id === record.created_by}
            canManage={true}
            tenantId={record.tenant_id || ''}
            onStatusChange={() => {
              // 刷新逻辑
            }}
          />
        ) : (
          <FileTeamShareToggle
            fileId={documentId}
            fileName={name}
            isOwner={record.tenant_id === record.created_by}
            canManage={true}
            tenantId={record.tenant_id || ''}
            onStatusChange={() => {
              // 刷新逻辑
            }}
          />
        )}
      </PopoverContent>
    </Popover>
  );
}
```

### 3. 国际化词条应提前规划

```typescript
// web/src/locales/en.ts
fileManager: {
  // 文件夹团队共享相关
  shareFolder: 'Share folder',
  shareFolderDescription: 'Share this folder with your entire team',
  shareFolderToTeam: 'Share folder with team',
  folderTeamShareEnabledDesc: 'All team members can access this folder and its contents',
  folderTeamShareDisabledDesc: 'Only you can access this folder and its contents',
  folderPermissionLevel: 'Permission level',
  folderPermissionLevelDesc: 'Set the permission level for all team members for this folder',
  sharedFolderToTeam: 'Shared folder with team',
  privateFolder: 'Private folder',
}

// web/src/locales/zh.ts
fileManager: {
  shareFolder: '共享文件夹',
  shareFolderDescription: '将此文件夹与您的整个团队共享',
  shareFolderToTeam: '共享文件夹给团队',
  folderTeamShareEnabledDesc: '所有团队成员均可访问此文件夹及其内容',
  folderTeamShareDisabledDesc: '仅你自己可以访问此文件夹及其内容',
  folderPermissionLevel: '权限级别',
  folderPermissionLevelDesc: '设置所有团队成员对此文件夹的权限级别',
  sharedFolderToTeam: '文件夹已共享给团队',
  privateFolder: '私有文件夹',
}
```

### 4. 复用现有 API 接口

文件夹共享复用现有的文件权限API接口，后端已支持通过 `file_id` 参数处理文件夹ID：

```typescript
// API端点
GET  /file_permission/team/status   - 获取团队共享状态
POST /file_permission/team/enable   - 启用团队共享
POST /file_permission/team/disable  - 禁用团队共享
PUT  /file_permission/team/level    - 更新权限级别
GET  /file_permission/check         - 检查权限
```

## Why This Matters

遵循此指导可以：

- **减少代码重复**：复用核心逻辑和 API，避免重复开发
- **保持 UI 一致性**：文件和文件夹的共享体验保持一致
- **提高可维护性**：组件职责单一，修改时不会相互影响
- **降低测试成本**：复用已验证的 API 和服务层逻辑

不遵循此指导可能导致：

- 组件耦合严重，修改一处影响多处
- UI/UX 不一致，用户体验混乱
- API 接口冗余，增加后端维护负担

## When to Apply

- 需要为相似但不同的资源类型添加相同功能时
- 现有组件已有成熟的业务逻辑，但 UI 需要微调
- 多种资源类型需要共享相同的 API 调用链路

## Examples

### Before（强行复用，导致逻辑混乱）

```tsx
// ❌ 错误：在 FileTeamShareToggle 中添加 folder 相关判断
function FileTeamShareToggle({ fileId, isFolder }: Props) {
  // 组件内部充斥着 if (isFolder) 分支
  // 难以维护和测试
  if (isFolder) {
    // 文件夹特定逻辑
  } else {
    // 文件特定逻辑
  }
}
```

### After（职责分离，清晰可扩展）

```tsx
// ✅ 正确：创建专用组件，各自职责明确
// 文件共享
<FileTeamShareToggle
  fileId={record.id}
  fileName={record.name}
  isOwner={...}
  canManage={...}
  tenantId={...}
/>

// 文件夹共享
<FolderTeamShareToggle
  folderId={record.id}
  folderName={record.name}
  isOwner={...}
  canManage={...}
  tenantId={...}
/>
```

## Key Files

| 文件路径 | 用途 |
|---------|------|
| `web/src/components/folder-team-share-toggle.tsx` | 文件夹团队共享主组件 |
| `web/src/components/file-team-share-toggle.tsx` | 文件团队共享组件（参考） |
| `web/src/pages/files/action-cell.tsx` | 文件管理界面集成点 |
| `web/src/locales/en.ts` | 英文国际化词条 |
| `web/src/locales/zh.ts` | 中文国际化词条 |
| `web/src/services/file-permission-service.ts` | 文件权限服务 |

## Permission Levels

| 权限级别 | 说明 |
|---------|------|
| **VIEW** | 可以查看和下载文件/文件夹内容 |
| **EDIT** | 可以查看、下载、编辑、上传文件和创建子文件夹 |
| **ADMIN** | 拥有编辑权限外，还可以删除、重命名、移动、共享文件/文件夹 |

## Related

- [文件权限服务实现](../../../api/db/services/file_permission_service.py)
- [团队权限服务实现](../../../api/db/services/team_permission_service.py)
- [文件管理界面设计](../../../docs/folder-team-sharing-development.md)
