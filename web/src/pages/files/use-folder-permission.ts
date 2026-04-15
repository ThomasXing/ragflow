/**
 * useCurrentFolderPermission
 *
 * Checks the current user's effective permission level for the folder currently
 * being browsed (identified by the `folderId` URL query parameter).
 *
 * Rules:
 *  - Root level (no folderId)  → always allow write actions (user's own files).
 *  - folderId present           → call GET /file_permission/check?file_id=<folderId>
 *                                 and derive canUpload / canCreateFolder from the
 *                                 returned permission_level.
 *
 * Permission hierarchy (ascending write capability):
 *   none < view < edit < admin < owner
 *
 * "Can write" = permission_level is one of: edit, admin, owner.
 */

import filePermissionService, {
  FilePermissionLevel,
} from '@/services/file-permission-service';
import { useEffect, useState } from 'react';
import { useGetFolderId } from './hooks';

const WRITE_LEVELS: Set<string> = new Set([
  FilePermissionLevel.EDIT,
  FilePermissionLevel.ADMIN,
  FilePermissionLevel.OWNER,
]);

export interface FolderPermissionState {
  /** Whether the current user may upload files into the current folder. */
  canUpload: boolean;
  /** Whether the current user may create sub-folders inside the current folder. */
  canCreateFolder: boolean;
  /** True while the permission check API call is in-flight. */
  isLoading: boolean;
}

export const useCurrentFolderPermission = (): FolderPermissionState => {
  const folderId = useGetFolderId();

  const [state, setState] = useState<FolderPermissionState>({
    canUpload: true,
    canCreateFolder: true,
    isLoading: false,
  });

  useEffect(() => {
    // Root level: no permission check needed; user is browsing their own files.
    if (!folderId) {
      setState({ canUpload: true, canCreateFolder: true, isLoading: false });
      return;
    }

    let cancelled = false;

    const check = async () => {
      setState((prev) => ({ ...prev, isLoading: true }));

      try {
        const response = await filePermissionService.checkPermission({
          file_id: folderId,
        });

        if (cancelled) return;

        // The backend wraps its response in data.data
        const info = response?.data?.data as
          | { permission_level?: string; has_permission?: boolean }
          | undefined;

        const level = info?.permission_level ?? null;
        const canWrite = level !== null && WRITE_LEVELS.has(level);

        setState({
          canUpload: canWrite,
          canCreateFolder: canWrite,
          isLoading: false,
        });
      } catch {
        if (!cancelled) {
          // On error, default to allowing actions (fail-open) to avoid blocking
          // users unintentionally.
          setState({
            canUpload: true,
            canCreateFolder: true,
            isLoading: false,
          });
        }
      }
    };

    check();

    return () => {
      cancelled = true;
    };
  }, [folderId]);

  return state;
};
