# 文件夹团队共享功能开发文档

## 功能概述

已实现文件夹团队共享功能，允许用户将文件夹共享给整个团队，并设置不同的权限级别（查看、编辑、管理）。

## 实现的功能

### 1. 文件夹团队共享组件 (`FolderTeamShareToggle`)
- 基于现有的 `FileTeamShareToggle` 组件适配
- 支持文件夹特定的UI展示（文件夹图标）
- 支持与文件相同的权限级别：查看、编辑、管理
- 响应式设计，适配文件管理界面的Popover组件

### 2. 国际化支持
- 添加了文件夹相关的国际化词条（中英文）
- 包括：共享文件夹、文件夹权限级别、文件夹团队共享描述等

### 3. 集成到文件管理界面
- 在 `ActionCell` 组件中根据文件类型显示不同的团队共享组件
- 文件夹显示 `FolderTeamShareToggle`
- 文件显示 `FileTeamShareToggle`

### 4. API调用链路
文件夹共享复用现有的文件权限API接口：
- `GET /file_permission/team/status` - 获取团队共享状态
- `POST /file_permission/team/enable` - 启用团队共享
- `POST /file_permission/team/disable` - 禁用团队共享
- `PUT /file_permission/team/level` - 更新权限级别
- `GET /file_permission/check` - 检查权限

### 5. 权限级别说明
- **查看 (VIEW)**: 可以查看和下载文件/文件夹内容
- **编辑 (EDIT)**: 可以查看、下载、编辑、上传文件和创建子文件夹
- **管理 (ADMIN)**: 拥有编辑权限外，还可以删除、重命名、移动、共享文件/文件夹

## 技术实现

### 前端组件
```
web/src/components/folder-team-share-toggle.tsx
├── 文件夹团队共享主组件
├── 支持三种权限级别
├── 实时状态加载和更新
└── 完整的错误处理
```

### 国际化词条
```typescript
// 英文
shareFolder: 'Share folder',
shareFolderDescription: 'Share this folder with your entire team',
shareFolderToTeam: 'Share folder with team',
folderTeamShareEnabledDesc: 'All team members can access this folder and its contents',
folderTeamShareDisabledDesc: 'Only you can access this folder and its contents',
folderPermissionLevel: 'Permission level',
folderPermissionLevelDesc: 'Set the permission level for all team members for this folder',
folderTeamShareEnabled: 'Folder shared with the entire team',
folderTeamShareDisabled: 'Folder team sharing disabled',
folderTeamShareEnableFailed: 'Failed to enable folder team sharing',
folderTeamShareDisableFailed: 'Failed to disable folder team sharing',
sharedFolderToTeam: 'Shared folder with team',
privateFolder: 'Private folder',

// 中文
shareFolder: '共享文件夹',
shareFolderDescription: '将此文件夹与您的整个团队共享',
shareFolderToTeam: '共享文件夹给团队',
folderTeamShareEnabledDesc: '所有团队成员均可访问此文件夹及其内容',
folderTeamShareDisabledDesc: '仅你自己可以访问此文件夹及其内容',
folderPermissionLevel: '权限级别',
folderPermissionLevelDesc: '设置所有团队成员对此文件夹的权限级别',
folderTeamShareEnabled: '文件夹已共享给所有团队成员',
folderTeamShareDisabled: '文件夹团队共享已关闭',
folderTeamShareEnableFailed: '启用文件夹团队共享失败',
folderTeamShareDisableFailed: '关闭文件夹团队共享失败',
sharedFolderToTeam: '文件夹已共享给团队',
privateFolder: '私有文件夹',
```

### 集成位置
- 文件管理界面 (`web/src/pages/files/action-cell.tsx`)
- 根据 `isFolderType(record.type)` 判断显示文件或文件夹共享组件

## 测试覆盖

### 单元测试
1. **文件夹团队共享组件测试** (`web/src/components/__tests__/folder-team-share-toggle.test.tsx`)
   - 组件渲染测试
   - API调用测试
   - 交互测试（开关切换、权限级别变更）
   - 错误处理测试

2. **API集成测试** (`web/src/services/__tests__/folder-team-share-integration.test.ts`)
   - API调用链路验证
   - 参数格式验证
   - 错误处理验证
   - 响应格式验证

## 使用方法

### 启用文件夹团队共享
1. 在文件管理界面找到文件夹
2. 点击共享按钮（Share2图标）
3. 打开文件夹团队共享开关
4. 选择权限级别
5. 保存设置

### 权限说明
- **查看**: 团队成员可以查看文件夹内容
- **编辑**: 团队成员可以上传文件、创建子文件夹
- **管理**: 团队成员可以删除、重命名、移动文件夹内容

## 后端API兼容性

文件夹共享复用文件权限系统的API，后端已经支持：
- `TeamPermissionService` 处理文件夹ID
- 权限检查支持文件夹ID
- 数据库模型支持文件夹ID字段

## 后续改进建议

1. **递归权限继承**（未来功能）
   - 支持子文件夹自动继承父文件夹权限
   - 可选的 `include_subfolders` 参数

2. **批量操作**
   - 批量设置文件夹团队共享
   - 批量修改权限级别

3. **权限预览**
   - 显示文件夹内文件的权限状态
   - 权限冲突检测和解决

4. **审计日志**
   - 记录文件夹共享操作历史
   - 权限变更跟踪

## 注意事项

1. 文件夹团队共享使用与文件相同的API接口
2. 权限级别定义与文件保持一致
3. 后端需要确保文件夹ID在权限系统中正确识别
4. 文件夹删除时应自动移除团队共享权限

## 验证状态

✅ 组件创建完成
✅ 国际化词条添加完成  
✅ 文件管理界面集成完成
✅ API调用链路测试完成
✅ 错误处理实现完成
❌ 完整单元测试（由于Jest配置问题暂未运行）
❌ 端到端集成测试（需要后端环境）

## 依赖关系

- 文件权限服务 (`file-permission-service.ts`)
- 文件类型判断工具 (`isFolderType`)
- UI组件库（Switch, Select, Badge等）
- 国际化系统（react-i18next）
- 通知系统（toast）