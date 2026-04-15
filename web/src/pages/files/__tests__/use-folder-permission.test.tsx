/**
 * TDD Tests for useCurrentFolderPermission hook and Files page upload button visibility.
 *
 * Red Phase: These tests are written BEFORE the implementation.
 * They describe the expected behavior once the fix is in place.
 *
 * Core bug: VIEW-only team members can see and click "Upload File" / "New Folder"
 * buttons in shared folders, which leads to a backend permission error.
 *
 * Fix: When a folderId is present in the URL, query the current user's permission
 * level for that folder and hide write-action buttons if they lack EDIT permission.
 */

import { render, renderHook, screen, waitFor } from '@testing-library/react';

// ---------- Mocks ----------

// react-router: simulate URL with ?folderId=shared-001
jest.mock('react-router', () => ({
  ...jest.requireActual('react-router'),
  useSearchParams: jest.fn(),
  useNavigate: jest.fn(() => jest.fn()),
}));

// i18n
jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

// All services / hooks that index.tsx and hooks.ts import
jest.mock('@/services/file-permission-service', () => ({
  __esModule: true,
  default: {
    checkPermission: jest.fn(),
  },
  FilePermissionLevel: {
    VIEW: 'view',
    EDIT: 'edit',
    ADMIN: 'admin',
    OWNER: 'owner',
  },
}));

jest.mock('@/hooks/use-file-request', () => ({
  useUploadFile: () => ({ uploadFile: jest.fn(), loading: false }),
  useCreateFolder: () => ({ createFolder: jest.fn(), loading: false }),
  useRenameFile: () => ({ renameFile: jest.fn(), loading: false }),
  useConnectToKnowledge: () => ({
    connectFileToKnowledge: jest.fn(),
    loading: false,
  }),
  useFetchFileList: () => ({
    pagination: { current: 1, pageSize: 10 },
    files: [],
    total: 0,
    loading: false,
    setPagination: jest.fn(),
    searchString: '',
    handleInputChange: jest.fn(),
  }),
  useMoveFile: () => ({ moveFile: jest.fn(), loading: false }),
  useRemoveFile: () => ({ removeDocument: jest.fn(), loading: false }),
}));

jest.mock('@/hooks/common-hooks', () => ({
  useSetModalState: () => ({
    visible: false,
    hideModal: jest.fn(),
    showModal: jest.fn(),
  }),
  useTranslate: () => ({ t: (k: string) => k }),
}));

jest.mock('../hooks', () => ({
  useGetFolderId: jest.fn(),
  useHandleBreadcrumbClick: () => ({ handleBreadcrumbClick: jest.fn() }),
  useRenameCurrentFile: () => ({
    fileRenameLoading: false,
    initialFileName: '',
    onFileRenameOk: jest.fn(),
    fileRenameVisible: false,
    hideFileRenameModal: jest.fn(),
    showFileRenameModal: jest.fn(),
  }),
  useHandleConnectToKnowledge: () => ({
    connectToKnowledgeLoading: false,
    onConnectToKnowledgeOk: jest.fn(),
    connectToKnowledgeVisible: false,
    hideConnectToKnowledgeModal: jest.fn(),
    showConnectToKnowledgeModal: jest.fn(),
    initialConnectedIds: [],
  }),
}));

// ---------- Imports (after mocks) ----------

import filePermissionService, {
  FilePermissionLevel,
} from '@/services/file-permission-service';
import { useSearchParams } from 'react-router';
import { useGetFolderId } from '../hooks';

// ---------- Helper ----------

const mockSearchParamsWith = (folderId: string | null) => {
  const get = jest
    .fn()
    .mockImplementation((key: string) =>
      key === 'folderId' ? folderId : null,
    );
  (useSearchParams as jest.Mock).mockReturnValue([{ get }]);
  (useGetFolderId as jest.Mock).mockReturnValue(folderId ?? '');
};

// =========================================================
// Suite 1: useCurrentFolderPermission hook
// =========================================================
describe('useCurrentFolderPermission', () => {
  // Import lazily so each test uses the current mock state
  const getHook = () =>
    require('../use-folder-permission').useCurrentFolderPermission;

  beforeEach(() => {
    jest.resetModules();
    jest.clearAllMocks();
  });

  it('returns canUpload=true when user is the folder owner', async () => {
    mockSearchParamsWith('shared-001');
    (filePermissionService.checkPermission as jest.Mock).mockResolvedValue({
      data: {
        data: {
          permission_level: FilePermissionLevel.OWNER,
          has_permission: true,
        },
      },
    });

    const { useCurrentFolderPermission } = require('../use-folder-permission');
    const { result } = renderHook(() => useCurrentFolderPermission());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.canUpload).toBe(true);
    expect(result.current.canCreateFolder).toBe(true);
  });

  it('returns canUpload=true when user has EDIT permission', async () => {
    mockSearchParamsWith('shared-001');
    (filePermissionService.checkPermission as jest.Mock).mockResolvedValue({
      data: {
        data: {
          permission_level: FilePermissionLevel.EDIT,
          has_permission: true,
        },
      },
    });

    const { useCurrentFolderPermission } = require('../use-folder-permission');
    const { result } = renderHook(() => useCurrentFolderPermission());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.canUpload).toBe(true);
    expect(result.current.canCreateFolder).toBe(true);
  });

  it('returns canUpload=false when user has VIEW-only permission', async () => {
    mockSearchParamsWith('shared-001');
    (filePermissionService.checkPermission as jest.Mock).mockResolvedValue({
      data: {
        data: {
          permission_level: FilePermissionLevel.VIEW,
          has_permission: true,
        },
      },
    });

    const { useCurrentFolderPermission } = require('../use-folder-permission');
    const { result } = renderHook(() => useCurrentFolderPermission());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.canUpload).toBe(false);
    expect(result.current.canCreateFolder).toBe(false);
  });

  it('returns canUpload=true when no folderId (root level — own files)', async () => {
    mockSearchParamsWith(null);

    const { useCurrentFolderPermission } = require('../use-folder-permission');
    const { result } = renderHook(() => useCurrentFolderPermission());

    // No API call should be made for root
    expect(filePermissionService.checkPermission).not.toHaveBeenCalled();
    expect(result.current.canUpload).toBe(true);
    expect(result.current.canCreateFolder).toBe(true);
  });

  it('does not call checkPermission when folderId is empty string', async () => {
    mockSearchParamsWith('');

    const { useCurrentFolderPermission } = require('../use-folder-permission');
    renderHook(() => useCurrentFolderPermission());

    expect(filePermissionService.checkPermission).not.toHaveBeenCalled();
  });

  it('calls checkPermission with correct file_id query param', async () => {
    mockSearchParamsWith('folder-xyz');
    (filePermissionService.checkPermission as jest.Mock).mockResolvedValue({
      data: { data: { permission_level: FilePermissionLevel.EDIT } },
    });

    const { useCurrentFolderPermission } = require('../use-folder-permission');
    renderHook(() => useCurrentFolderPermission());

    await waitFor(() => {
      expect(filePermissionService.checkPermission).toHaveBeenCalledWith(
        expect.objectContaining({ file_id: 'folder-xyz' }),
      );
    });
  });
});

// =========================================================
// Suite 2: Files page — upload/create buttons visibility
// =========================================================
describe('Files page — add-file button visibility', () => {
  beforeEach(() => {
    jest.resetModules();
    jest.clearAllMocks();
  });

  it('hides the add-file button when user has VIEW-only permission', async () => {
    mockSearchParamsWith('shared-001');
    (filePermissionService.checkPermission as jest.Mock).mockResolvedValue({
      data: {
        data: {
          permission_level: FilePermissionLevel.VIEW,
          has_permission: true,
        },
      },
    });

    // Dynamically import page after mocks are set
    const { default: FilesPage } = require('../index');
    render(<FilesPage />);

    // Button text comes from t('knowledgeDetails.addFile') which returns the key
    await waitFor(() => {
      expect(
        screen.queryByText('knowledgeDetails.addFile'),
      ).not.toBeInTheDocument();
    });
  });

  it('shows the add-file button when user has EDIT permission', async () => {
    mockSearchParamsWith('shared-001');
    (filePermissionService.checkPermission as jest.Mock).mockResolvedValue({
      data: {
        data: {
          permission_level: FilePermissionLevel.EDIT,
          has_permission: true,
        },
      },
    });

    const { default: FilesPage } = require('../index');
    render(<FilesPage />);

    await waitFor(() => {
      expect(screen.getByText('knowledgeDetails.addFile')).toBeInTheDocument();
    });
  });

  it('shows the add-file button when at root level (no folderId)', async () => {
    mockSearchParamsWith(null);

    const { default: FilesPage } = require('../index');
    render(<FilesPage />);

    // Root level: always show button (user's own files)
    expect(screen.getByText('knowledgeDetails.addFile')).toBeInTheDocument();
  });
});
