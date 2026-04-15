import api from '@/utils/api';
import registerServer from '@/utils/register-server';
import request from '@/utils/request';

const methods = {
  createShare: {
    url: api.createFileShare,
    method: 'post',
  },
  listShares: {
    url: api.listFileShares,
    method: 'get',
  },
  updateShare: {
    url: api.updateFileShare,
    method: 'put',
  },
  revokeShare: {
    url: api.revokeFileShare,
    method: 'delete',
  },
  sharedWithMe: {
    url: api.sharedWithMe,
    method: 'get',
  },
  sharedByMe: {
    url: api.sharedByMe,
    method: 'get',
  },
  batchShare: {
    url: api.batchFileShare,
    method: 'post',
  },
  checkPermission: {
    url: api.checkFilePermission,
    method: 'get',
  },
  shareableUsers: {
    url: api.shareableUsers,
    method: 'get',
  },
  // Team share methods
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

const filePermissionService = registerServer<keyof typeof methods>(
  methods,
  request,
);

export default filePermissionService;

// Permission levels
export enum FilePermissionLevel {
  VIEW = 'view',
  EDIT = 'edit',
  ADMIN = 'admin',
  OWNER = 'owner',
}

// Permission level labels for display
export const PermissionLevelLabels: Record<string, string> = {
  [FilePermissionLevel.VIEW]: 'View only',
  [FilePermissionLevel.EDIT]: 'Can edit',
  [FilePermissionLevel.ADMIN]: 'Can manage',
  [FilePermissionLevel.OWNER]: 'Owner',
};

// Permission level descriptions
export const PermissionLevelDescriptions: Record<string, string> = {
  [FilePermissionLevel.VIEW]: 'Can view and download files',
  [FilePermissionLevel.EDIT]:
    'Can view, download, edit, upload, and create folders',
  [FilePermissionLevel.ADMIN]:
    'Can view, download, edit, upload, create folders, delete, rename, move, and share',
  [FilePermissionLevel.OWNER]: 'Full control including transfer ownership',
};

// Types
export interface IFileShare {
  id: string;
  file_id: string;
  target_user_id: string;
  sharer_id: string;
  permission_level: string;
  tenant_id: string;
  created_at: string;
  expires_at?: string;
  status: string;
  target_user?: {
    id: string;
    nickname?: string;
    email?: string;
    avatar?: string;
  };
  sharer?: {
    id: string;
    nickname?: string;
    email?: string;
    avatar?: string;
  };
}

export interface ISharedFile {
  id: string;
  name: string;
  type: string;
  size: number;
  parent_id: string;
  created_by: string;
  create_time: number;
  share_permission: string;
  share_expires_at?: string;
  share_id: string;
}

export interface IShareRequest {
  file_id: string;
  target_user_ids: string[];
  permission_level: string;
  expires_at?: string;
}

export interface IPermissionInfo {
  has_permission: boolean;
  permission_level?: string;
  permission_source:
    | 'owner'
    | 'explicit'
    | 'inherited'
    | 'team'
    | 'tenant'
    | 'none';
  is_owner: boolean;
  error_message?: string;
}

export interface ITeamShareStatus {
  file_id: string;
  tenant_id: string;
  permission_level?: string;
  is_enabled: boolean;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
}
