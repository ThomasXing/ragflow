'use client';

import { useToast } from '@/components/hooks/use-toast';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import filePermissionService, {
  FilePermissionLevel,
  PermissionLevelLabels,
  type ITeamShareStatus,
} from '@/services/file-permission-service';
import { Globe, Loader2, Lock } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface FileTeamShareToggleProps {
  fileId: string;
  fileName: string;
  isOwner: boolean;
  canManage: boolean;
  tenantId: string;
  onStatusChange?: (enabled: boolean, level?: string) => void;
}

export function FileTeamShareToggle({
  fileId,
  fileName: _fileName,
  isOwner,
  canManage,
  tenantId,
  onStatusChange,
}: FileTeamShareToggleProps) {
  const { t } = useTranslation();
  const { toast } = useToast();

  const [loading, setLoading] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [status, setStatus] = useState<ITeamShareStatus | null>(null);
  const [selectedPermission, setSelectedPermission] = useState<string>(
    FilePermissionLevel.VIEW,
  );

  // 加载团队共享状态
  const loadTeamShareStatus = async () => {
    if (!fileId || !canManage) return;

    setLoading(true);
    try {
      const response = await filePermissionService.getTeamShareStatus({
        file_id: fileId,
      });
      if (response.data?.data) {
        setStatus(response.data.data);
        // 无论是否启用，都更新权限级别
        if (response.data.data.permission_level) {
          setSelectedPermission(response.data.data.permission_level);
        } else {
          // 如果后端返回的permission_level为空，重置为默认值
          setSelectedPermission(FilePermissionLevel.VIEW);
        }
      }
    } catch (error) {
      console.error('Failed to load team share status:', error);
      toast({
        variant: 'destructive',
        title: t('common.error'),
        description: t('fileManager.failedToLoadTeamShareStatus'),
      });
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
        if (response.data?.data?.success) {
          setStatus({
            file_id: fileId,
            tenant_id: tenantId,
            permission_level: selectedPermission,
            is_enabled: true,
            created_by: '', // 后端会填充
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          });
          toast({
            title: t('common.success'),
            description: t('fileManager.teamShareEnabled'),
          });
          onStatusChange?.(true, selectedPermission);
        } else {
          throw new Error(response.data?.message || '启用团队共享失败');
        }
      } else {
        // 禁用团队共享
        const response = await filePermissionService.disableTeamShare({
          file_id: fileId,
        });
        if (response.data?.data?.success) {
          // 重置权限级别为默认值
          setSelectedPermission(FilePermissionLevel.VIEW);
          setStatus({
            file_id: fileId,
            tenant_id: tenantId,
            is_enabled: false,
          });
          toast({
            title: t('common.success'),
            description: t('fileManager.teamShareDisabled'),
          });
          onStatusChange?.(false);
        } else {
          throw new Error(response.data?.message || '禁用团队共享失败');
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
      setStatus((prev) => (prev ? { ...prev, is_enabled: !enabled } : null));
      // 如果禁用失败，也重置权限级别
      if (!enabled) {
        setSelectedPermission(FilePermissionLevel.VIEW);
      }
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
      if (response.data?.data?.success) {
        setSelectedPermission(permissionLevel);
        setStatus((prev) =>
          prev ? { ...prev, permission_level: permissionLevel } : null,
        );
        toast({
          title: t('common.success'),
          description: t('fileManager.teamPermissionUpdated'),
        });
        onStatusChange?.(true, permissionLevel);
      } else {
        throw new Error(response.data?.message || '更新团队权限失败');
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
            {PermissionLevelLabels[status.permission_level] ||
              status.permission_level}
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
          aria-label={
            isEnabled
              ? t('fileManager.disableTeamShare')
              : t('fileManager.enableTeamShare')
          }
        />
      </div>

      {isEnabled && (
        <div className="space-y-2">
          <Label
            htmlFor="team-permission-level"
            className="text-sm font-medium"
          >
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
              {PermissionLevelLabels[selectedPermission] || selectedPermission}
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
