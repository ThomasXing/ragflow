'use client';

import { useToast } from '@/components/hooks/use-toast';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import filePermissionService, {
  FilePermissionLevel,
  IFileShare,
  PermissionLevelDescriptions,
  PermissionLevelLabels,
} from '@/services/file-permission-service';
import {
  Loader2,
  Share2,
  Shield,
  Trash2,
  UserPlus,
  Users,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface FileShareDialogProps {
  open: boolean;
  fileId: string;
  fileName: string;
  onClose: () => void;
  onShared?: () => void;
}

export function FileShareDialog({
  open,
  fileId,
  fileName,
  onClose,
  onShared,
}: FileShareDialogProps) {
  const { t } = useTranslation();
  const { toast } = useToast();

  const [loading, setLoading] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [permissions, setPermissions] = useState<IFileShare[]>([]);
  const [inheritedPermissions, setInheritedPermissions] = useState<any[]>([]);
  const [canManage, setCanManage] = useState(false);
  const [isOwner, setIsOwner] = useState(false);
  const [shareableUsers, setShareableUsers] = useState<any[]>([]);

  // Form state
  const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);
  const [selectedPermission, setSelectedPermission] = useState<string>(
    FilePermissionLevel.VIEW,
  );
  const [searchQuery, setSearchQuery] = useState('');

  // Load existing permissions
  const loadPermissions = useCallback(async () => {
    if (!fileId) return;

    setLoading(true);
    try {
      const response = await filePermissionService.listShares({
        file_id: fileId,
      });
      if (response.data) {
        setPermissions(response.data.permissions || []);
        setInheritedPermissions(response.data.inherited || []);
        setCanManage(response.data.can_manage || false);
        setIsOwner(response.data.is_owner || false);
      }
    } catch (error) {
      console.error('Failed to load permissions:', error);
      toast({
        variant: 'destructive',
        title: t('common.error'),
        description: t('fileManager.failedToLoadPermissions'),
      });
    } finally {
      setLoading(false);
    }
  }, [fileId, toast, t]);

  // Load shareable users
  const loadShareableUsers = useCallback(async () => {
    if (!fileId) return;

    try {
      const response = await filePermissionService.shareableUsers({
        file_id: fileId,
      });
      if (response.data?.users) {
        setShareableUsers(response.data.users);
      }
    } catch (error) {
      console.error('Failed to load shareable users:', error);
    }
  }, [fileId]);

  useEffect(() => {
    if (open) {
      loadPermissions();
      loadShareableUsers();
    }
  }, [open, loadPermissions, loadShareableUsers]);

  // Handle share
  const handleShare = async () => {
    if (selectedUserIds.length === 0) {
      toast({
        variant: 'destructive',
        title: t('common.error'),
        description: t('fileManager.selectUserToShare'),
      });
      return;
    }

    setSharing(true);
    try {
      const response = await filePermissionService.createShare({
        file_id: fileId,
        target_user_ids: selectedUserIds,
        permission_level: selectedPermission,
      });

      if (response.data) {
        const { shares, failed } = response.data;
        if (shares.length > 0) {
          toast({
            title: t('common.success'),
            description: t('fileManager.shareSuccess', {
              count: shares.length,
            }),
          });
          loadPermissions();
          setSelectedUserIds([]);
          onShared?.();
        }
        if (failed.length > 0) {
          toast({
            variant: 'destructive',
            title: t('common.warning'),
            description: failed.map((f: any) => f.error).join(', '),
          });
        }
      }
    } catch (error) {
      console.error('Failed to share:', error);
      toast({
        variant: 'destructive',
        title: t('common.error'),
        description: t('fileManager.shareFailed'),
      });
    } finally {
      setSharing(false);
    }
  };

  // Handle revoke
  const handleRevoke = async (shareId: string) => {
    try {
      const response = await filePermissionService.revokeShare({
        share_id: shareId,
      });
      if (response.data) {
        toast({
          title: t('common.success'),
          description: t('fileManager.revokeSuccess'),
        });
        loadPermissions();
      }
    } catch (error) {
      console.error('Failed to revoke:', error);
      toast({
        variant: 'destructive',
        title: t('common.error'),
        description: t('fileManager.revokeFailed'),
      });
    }
  };

  // Handle update permission
  const handleUpdatePermission = async (
    shareId: string,
    permissionLevel: string,
  ) => {
    try {
      const response = await filePermissionService.updateShare({
        share_id: shareId,
        permission_level: permissionLevel,
      });
      if (response.data) {
        toast({
          title: t('common.success'),
          description: t('fileManager.updatePermissionSuccess'),
        });
        loadPermissions();
      }
    } catch (error) {
      console.error('Failed to update permission:', error);
      toast({
        variant: 'destructive',
        title: t('common.error'),
        description: t('fileManager.updatePermissionFailed'),
      });
    }
  };

  // Filter users by search query
  const filteredUsers = shareableUsers.filter(
    (user) =>
      user.nickname?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.email?.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  // Get user initials for avatar fallback
  const getUserInitials = (user: any) => {
    if (user.nickname) {
      return user.nickname.substring(0, 2).toUpperCase();
    }
    if (user.email) {
      return user.email.substring(0, 2).toUpperCase();
    }
    return 'U';
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Share2 className="h-5 w-5" />
            {t('fileManager.shareFile')}
          </DialogTitle>
          <DialogDescription>
            {t('fileManager.shareFileDescription', { name: fileName })}
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-4">
            {/* Add new share */}
            {canManage && (
              <div className="space-y-3">
                <div className="text-sm font-medium">
                  {t('fileManager.addPeople')}
                </div>
                <div className="flex gap-2">
                  <div className="flex-1">
                    <Input
                      placeholder={t('fileManager.searchUsers')}
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>
                  <Select
                    value={selectedPermission}
                    onValueChange={setSelectedPermission}
                  >
                    <SelectTrigger className="w-[140px]">
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
                  <Button
                    onClick={handleShare}
                    disabled={sharing || selectedUserIds.length === 0}
                  >
                    {sharing ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <UserPlus className="h-4 w-4" />
                    )}
                  </Button>
                </div>

                {/* Selected users count and clear button */}
                {selectedUserIds.length > 0 && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">
                      {t('fileManager.selectedUsers', {
                        count: selectedUserIds.length,
                      })}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedUserIds([])}
                      className="h-8 px-2 text-muted-foreground hover:text-destructive"
                    >
                      <X className="h-3 w-3 mr-1" />
                      {t('fileManager.clearSelection')}
                    </Button>
                  </div>
                )}

                {/* User suggestions */}
                {searchQuery && filteredUsers.length > 0 && (
                  <ScrollArea className="h-[120px] border rounded-md">
                    <div className="p-2 space-y-1">
                      {filteredUsers.map((user) => {
                        const isSelected = selectedUserIds.includes(user.id);
                        return (
                          <div
                            key={user.id}
                            className={`flex items-center gap-2 p-2 rounded-md hover:bg-accent cursor-pointer ${
                              isSelected ? 'bg-accent' : ''
                            }`}
                            onClick={() => {
                              if (isSelected) {
                                setSelectedUserIds(
                                  selectedUserIds.filter(
                                    (id) => id !== user.id,
                                  ),
                                );
                              } else {
                                setSelectedUserIds([
                                  ...selectedUserIds,
                                  user.id,
                                ]);
                              }
                            }}
                          >
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setSelectedUserIds([
                                    ...selectedUserIds,
                                    user.id,
                                  ]);
                                } else {
                                  setSelectedUserIds(
                                    selectedUserIds.filter(
                                      (id) => id !== user.id,
                                    ),
                                  );
                                }
                              }}
                              className="h-4 w-4"
                            />
                            <Avatar className="h-8 w-8">
                              <AvatarImage src={user.avatar} />
                              <AvatarFallback>
                                {getUserInitials(user)}
                              </AvatarFallback>
                            </Avatar>
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-medium truncate">
                                {user.nickname || user.email}
                              </div>
                              {user.email && (
                                <div className="text-xs text-muted-foreground truncate">
                                  {user.email}
                                </div>
                              )}
                            </div>
                            {user.existing_permission && (
                              <Badge variant="secondary" className="text-xs">
                                {
                                  PermissionLevelLabels[
                                    user.existing_permission
                                  ]
                                }
                              </Badge>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </ScrollArea>
                )}
              </div>
            )}

            {/* Current permissions */}
            <div className="space-y-2">
              <div className="text-sm font-medium flex items-center gap-2">
                <Users className="h-4 w-4" />
                {t('fileManager.peopleWithAccess')}
              </div>

              <ScrollArea className="h-[200px] border rounded-md">
                <div className="p-2 space-y-1">
                  {permissions.length === 0 &&
                    inheritedPermissions.length === 0 && (
                      <div className="text-center text-sm text-muted-foreground py-4">
                        {t('fileManager.noSharedUsers')}
                      </div>
                    )}

                  {/* Explicit permissions */}
                  {permissions.map((perm) => (
                    <div
                      key={perm.id}
                      className="flex items-center gap-2 p-2 rounded-md hover:bg-accent"
                    >
                      <Avatar className="h-8 w-8">
                        <AvatarImage src={perm.target_user?.avatar} />
                        <AvatarFallback>
                          {getUserInitials(perm.target_user)}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium truncate">
                          {perm.target_user?.nickname ||
                            perm.target_user?.email ||
                            'Unknown'}
                        </div>
                        {perm.target_user?.email && (
                          <div className="text-xs text-muted-foreground truncate">
                            {perm.target_user.email}
                          </div>
                        )}
                      </div>
                      {canManage ? (
                        <div className="flex items-center gap-2">
                          <Select
                            value={perm.permission_level}
                            onValueChange={(value) =>
                              handleUpdatePermission(perm.id, value)
                            }
                          >
                            <SelectTrigger className="w-[100px] h-8">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value={FilePermissionLevel.VIEW}>
                                {
                                  PermissionLevelLabels[
                                    FilePermissionLevel.VIEW
                                  ]
                                }
                              </SelectItem>
                              <SelectItem value={FilePermissionLevel.EDIT}>
                                {
                                  PermissionLevelLabels[
                                    FilePermissionLevel.EDIT
                                  ]
                                }
                              </SelectItem>
                              {isOwner && (
                                <SelectItem value={FilePermissionLevel.ADMIN}>
                                  {
                                    PermissionLevelLabels[
                                      FilePermissionLevel.ADMIN
                                    ]
                                  }
                                </SelectItem>
                              )}
                            </SelectContent>
                          </Select>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                              >
                                <Trash2 className="h-4 w-4 text-destructive" />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>
                                  {t('fileManager.revokeAccess')}
                                </AlertDialogTitle>
                                <AlertDialogDescription>
                                  {t('fileManager.revokeAccessConfirm', {
                                    user:
                                      perm.target_user?.nickname ||
                                      perm.target_user?.email ||
                                      'this user',
                                  })}
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>
                                  {t('common.cancel')}
                                </AlertDialogCancel>
                                <AlertDialogAction
                                  onClick={() => handleRevoke(perm.id)}
                                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                >
                                  {t('common.confirm')}
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </div>
                      ) : (
                        <Badge variant="secondary">
                          {PermissionLevelLabels[perm.permission_level]}
                        </Badge>
                      )}
                    </div>
                  ))}

                  {/* Inherited permissions */}
                  {inheritedPermissions.length > 0 && (
                    <>
                      <Separator className="my-2" />
                      <div className="text-xs text-muted-foreground px-2">
                        {t('fileManager.inheritedPermissions')}
                      </div>
                      {inheritedPermissions.map((perm, index) => (
                        <div
                          key={index}
                          className="flex items-center gap-2 p-2 rounded-md bg-muted/50"
                        >
                          <Shield className="h-4 w-4 text-muted-foreground" />
                          <div className="flex-1 text-sm">
                            {t('fileManager.inheritedFrom', {
                              name: perm.file_name,
                            })}
                          </div>
                          <Badge variant="outline">
                            {PermissionLevelLabels[perm.permission_level]}
                          </Badge>
                        </div>
                      ))}
                    </>
                  )}
                </div>
              </ScrollArea>
            </div>

            {/* Permission level info */}
            <TooltipProvider>
              <div className="text-xs text-muted-foreground space-y-1">
                <div className="font-medium">
                  {t('fileManager.permissionLevels')}
                </div>
                {Object.entries(PermissionLevelDescriptions).map(
                  ([level, desc]) => (
                    <Tooltip key={level}>
                      <TooltipTrigger asChild>
                        <div className="flex items-center gap-2 cursor-help">
                          <Badge variant="outline" className="text-xs">
                            {PermissionLevelLabels[level]}
                          </Badge>
                          <span className="truncate">{desc}</span>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="max-w-[250px]">{desc}</p>
                      </TooltipContent>
                    </Tooltip>
                  ),
                )}
              </div>
            </TooltipProvider>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default FileShareDialog;
