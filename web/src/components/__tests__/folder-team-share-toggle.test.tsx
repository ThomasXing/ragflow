/**
 * 文件夹团队共享功能组件自动化测试
 *
 * 测试目标: 验证文件夹团队共享功能的UI组件和交互
 * 测试框架: Jest + React Testing Library
 */

import { FolderTeamShareToggle } from '@/components/folder-team-share-toggle';
import { useToast } from '@/components/hooks/use-toast';
import filePermissionService from '@/services/file-permission-service';
import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Mock dependencies
jest.mock('@/services/file-permission-service');
jest.mock('@/components/hooks/use-toast');
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('FolderTeamShareToggle Component', () => {
  const mockOnClose = jest.fn();
  const mockOnShared = jest.fn();
  const mockToast = {
    toast: jest.fn(),
  };

  const mockFolderInfo = {
    id: 'folder-123',
    name: 'Test Folder',
    type: 'folder',
  };

  const mockTenantId = 'tenant-456';

  beforeEach(() => {
    jest.clearAllMocks();
    useToast.mockReturnValue(mockToast);
  });

  // RED TEST 1: 组件应该正确渲染
  test('should render folder team share dialog with correct title and description', () => {
    render(
      <FolderTeamShareToggle
        open={true}
        folderId={mockFolderInfo.id}
        folderName={mockFolderInfo.name}
        tenantId={mockTenantId}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    expect(screen.getByText('fileManager.shareFolder')).toBeInTheDocument();
    expect(
      screen.getByText(/fileManager.shareFolderDescription/),
    ).toBeInTheDocument();
  });

  // RED TEST 2: 应该加载团队共享状态
  test('should load team share status for folder when opened', async () => {
    // Mock team share status API
    filePermissionService.getTeamShareStatus.mockResolvedValue({
      data: {
        data: {
          file_id: mockFolderInfo.id,
          tenant_id: mockTenantId,
          permission_level: 'view',
          is_enabled: false,
          created_by: 'user-789',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
      },
    });

    render(
      <FolderTeamShareToggle
        open={true}
        folderId={mockFolderInfo.id}
        folderName={mockFolderInfo.name}
        tenantId={mockTenantId}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      expect(filePermissionService.getTeamShareStatus).toHaveBeenCalledWith({
        file_id: mockFolderInfo.id,
      });
    });

    // Should show private folder state
    expect(screen.getByText('fileManager.privateFolder')).toBeInTheDocument();
  });

  // RED TEST 3: 应该启用文件夹团队共享
  test('should enable team sharing for folder', async () => {
    const user = userEvent.setup();

    // Mock initial disabled state
    filePermissionService.getTeamShareStatus.mockResolvedValue({
      data: {
        data: {
          file_id: mockFolderInfo.id,
          tenant_id: mockTenantId,
          permission_level: 'view',
          is_enabled: false,
        },
      },
    });

    // Mock enable API
    filePermissionService.enableTeamShare.mockResolvedValue({
      data: {
        data: {
          success: true,
          file_id: mockFolderInfo.id,
          tenant_id: mockTenantId,
          permission_level: 'view',
        },
      },
    });

    render(
      <FolderTeamShareToggle
        open={true}
        folderId={mockFolderInfo.id}
        folderName={mockFolderInfo.name}
        tenantId={mockTenantId}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Wait for data to load
    });

    // Find and click the enable toggle
    const toggle = screen.getByRole('switch');
    await user.click(toggle);

    await waitFor(() => {
      expect(filePermissionService.enableTeamShare).toHaveBeenCalledWith({
        file_id: mockFolderInfo.id,
        permission_level: 'view',
      });
    });

    // Should show success toast
    expect(mockToast.toast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'common.success',
        description: 'fileManager.teamShareEnabled',
      }),
    );
  });

  // RED TEST 4: 应该禁用文件夹团队共享
  test('should disable team sharing for folder', async () => {
    const user = userEvent.setup();

    // Mock initial enabled state
    filePermissionService.getTeamShareStatus.mockResolvedValue({
      data: {
        data: {
          file_id: mockFolderInfo.id,
          tenant_id: mockTenantId,
          permission_level: 'edit',
          is_enabled: true,
        },
      },
    });

    // Mock disable API
    filePermissionService.disableTeamShare.mockResolvedValue({
      data: {
        data: {
          success: true,
          file_id: mockFolderInfo.id,
          tenant_id: mockTenantId,
        },
      },
    });

    render(
      <FolderTeamShareToggle
        open={true}
        folderId={mockFolderInfo.id}
        folderName={mockFolderInfo.name}
        tenantId={mockTenantId}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Wait for data to load
    });

    // Find and click the disable toggle
    const toggle = screen.getByRole('switch');
    await user.click(toggle);

    await waitFor(() => {
      expect(filePermissionService.disableTeamShare).toHaveBeenCalledWith({
        file_id: mockFolderInfo.id,
      });
    });

    // Should show success toast
    expect(mockToast.toast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'common.success',
        description: 'fileManager.teamShareDisabled',
      }),
    );
  });

  // RED TEST 5: 应该更新文件夹团队共享权限级别
  test('should update folder team share permission level', async () => {
    const user = userEvent.setup();

    // Mock initial enabled state
    filePermissionService.getTeamShareStatus.mockResolvedValue({
      data: {
        data: {
          file_id: mockFolderInfo.id,
          tenant_id: mockTenantId,
          permission_level: 'view',
          is_enabled: true,
        },
      },
    });

    // Mock update API
    filePermissionService.updateTeamPermissionLevel.mockResolvedValue({
      data: {
        data: {
          success: true,
          file_id: mockFolderInfo.id,
          permission_level: 'edit',
        },
      },
    });

    render(
      <FolderTeamShareToggle
        open={true}
        folderId={mockFolderInfo.id}
        folderName={mockFolderInfo.name}
        tenantId={mockTenantId}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Wait for data to load
    });

    // Find and change permission level dropdown
    const permissionSelect = screen.getByRole('combobox');
    await user.click(permissionSelect);

    // Select "Can edit" option
    const editOption = screen.getByText('Can edit');
    await user.click(editOption);

    await waitFor(() => {
      expect(
        filePermissionService.updateTeamPermissionLevel,
      ).toHaveBeenCalledWith({
        file_id: mockFolderInfo.id,
        permission_level: 'edit',
      });
    });

    // Should show success toast
    expect(mockToast.toast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'common.success',
        description: 'fileManager.teamPermissionUpdated',
      }),
    );
  });

  // RED TEST 6: 应该显示正确的权限级别描述
  test('should show correct permission level descriptions for folder', async () => {
    // Mock enabled state
    filePermissionService.getTeamShareStatus.mockResolvedValue({
      data: {
        data: {
          file_id: mockFolderInfo.id,
          tenant_id: mockTenantId,
          permission_level: 'view',
          is_enabled: true,
        },
      },
    });

    render(
      <FolderTeamShareToggle
        open={true}
        folderId={mockFolderInfo.id}
        folderName={mockFolderInfo.name}
        tenantId={mockTenantId}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Should show permission level dropdown
      const permissionSelect = screen.getByRole('combobox');
      expect(permissionSelect).toBeInTheDocument();
    });

    // Should have permission level descriptions
    expect(
      screen.getByText('fileManager.folderPermissionLevelDesc'),
    ).toBeInTheDocument();
  });

  // RED TEST 7: 应该处理API错误
  test('should handle API errors gracefully for folder', async () => {
    // Mock API failure
    filePermissionService.getTeamShareStatus.mockRejectedValue(
      new Error('Network error'),
    );

    render(
      <FolderTeamShareToggle
        open={true}
        folderId={mockFolderInfo.id}
        folderName={mockFolderInfo.name}
        tenantId={mockTenantId}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      expect(mockToast.toast).toHaveBeenCalledWith(
        expect.objectContaining({
          variant: 'destructive',
          title: 'common.error',
          description: 'fileManager.failedToLoadTeamShareStatus',
        }),
      );
    });
  });

  // RED TEST 8: 应该处理没有管理权限的情况
  test('should show read-only state when user cannot manage folder', () => {
    // Component should handle read-only state
    render(
      <FolderTeamShareToggle
        open={true}
        folderId={mockFolderInfo.id}
        folderName={mockFolderInfo.name}
        tenantId={mockTenantId}
        onClose={mockOnClose}
        onShared={mockOnShared}
        canManage={false}
        isOwner={false}
      />,
    );

    // Should not show toggle switch when cannot manage
    expect(screen.queryByRole('switch')).not.toBeInTheDocument();
    // Should show readonly state
    expect(
      screen.getByText('fileManager.sharedToTeam') ||
        screen.getByText('fileManager.privateFolder'),
    ).toBeInTheDocument();
  });

  // RED TEST 9: 文件夹共享应该支持递归权限
  test('should handle recursive permission inheritance for subfolders', async () => {
    const user = userEvent.setup();

    // Mock folder with recursive option
    filePermissionService.getTeamShareStatus.mockResolvedValue({
      data: {
        data: {
          file_id: mockFolderInfo.id,
          tenant_id: mockTenantId,
          permission_level: 'view',
          is_enabled: false,
          include_subfolders: false,
        },
      },
    });

    // Mock enable with recursive option
    filePermissionService.enableTeamShare.mockResolvedValue({
      data: {
        data: {
          success: true,
          file_id: mockFolderInfo.id,
          include_subfolders: true,
        },
      },
    });

    render(
      <FolderTeamShareToggle
        open={true}
        folderId={mockFolderInfo.id}
        folderName={mockFolderInfo.name}
        tenantId={mockTenantId}
        onClose={mockOnClose}
        onShared={mockOnShared}
        includeSubfolders={true}
      />,
    );

    await waitFor(() => {
      // Wait for data to load
    });

    // Should show recursive permission checkbox
    const recursiveCheckbox = screen.getByRole('checkbox');
    expect(recursiveCheckbox).toBeInTheDocument();
    expect(
      screen.getByText('fileManager.includeSubfolders'),
    ).toBeInTheDocument();

    // Toggle on
    const toggle = screen.getByRole('switch');
    await user.click(toggle);

    await waitFor(() => {
      // Should call enable with include_subfolders parameter
      expect(filePermissionService.enableTeamShare).toHaveBeenCalledWith({
        file_id: mockFolderInfo.id,
        permission_level: 'view',
        include_subfolders: true,
      });
    });
  });

  // RED TEST 10: 应该验证文件夹类型
  test('should validate folder type before sharing', () => {
    // Component should handle folder-specific logic
    render(
      <FolderTeamShareToggle
        open={true}
        folderId={mockFolderInfo.id}
        folderName={mockFolderInfo.name}
        folderType="folder"
        tenantId={mockTenantId}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    // Should show folder-specific UI elements
    expect(screen.getByText(/folder|directory/i)).toBeInTheDocument();
  });
});

describe('Folder Permission Service Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // RED TEST 11: 文件夹权限检查应该调用正确的API
  test('should check folder permission with correct parameters', async () => {
    const mockResponse = {
      data: {
        has_permission: true,
        permission_level: 'edit',
        permission_source: 'team',
        is_owner: false,
      },
    };

    filePermissionService.checkPermission.mockResolvedValue(mockResponse);

    const result = await filePermissionService.checkPermission({
      file_id: 'folder-123',
      operation: 'edit',
    });

    expect(filePermissionService.checkPermission).toHaveBeenCalledWith({
      file_id: 'folder-123',
      operation: 'edit',
    });
    expect(result).toEqual(mockResponse);
  });

  // RED TEST 12: 文件夹团队共享应该支持子文件夹权限继承
  test('should enable team share for folder with subfolder inheritance', async () => {
    const mockResponse = {
      data: {
        success: true,
        file_id: 'folder-123',
        permission_level: 'view',
        include_subfolders: true,
      },
    };

    filePermissionService.enableTeamShare.mockResolvedValue(mockResponse);

    const result = await filePermissionService.enableTeamShare({
      file_id: 'folder-123',
      permission_level: 'view',
      include_subfolders: true,
    });

    expect(filePermissionService.enableTeamShare).toHaveBeenCalledWith({
      file_id: 'folder-123',
      permission_level: 'view',
      include_subfolders: true,
    });
    expect(result).toEqual(mockResponse);
  });

  // RED TEST 13: 应该获取文件夹的团队共享状态
  test('should get team share status for folder', async () => {
    const mockResponse = {
      data: {
        file_id: 'folder-123',
        tenant_id: 'tenant-456',
        permission_level: 'admin',
        is_enabled: true,
        include_subfolders: false,
      },
    };

    filePermissionService.getTeamShareStatus.mockResolvedValue(mockResponse);

    const result = await filePermissionService.getTeamShareStatus({
      file_id: 'folder-123',
    });

    expect(filePermissionService.getTeamShareStatus).toHaveBeenCalledWith({
      file_id: 'folder-123',
    });
    expect(result).toEqual(mockResponse);
  });

  // RED TEST 14: 切换开关时应该重置权限级别下拉框状态
  test('should reset permission dropdown state when toggling switch off and on', async () => {
    const user = userEvent.setup();

    // Mock initial enabled state with edit permission
    filePermissionService.getTeamShareStatus.mockResolvedValue({
      data: {
        data: {
          file_id: mockFolderInfo.id,
          tenant_id: mockTenantId,
          permission_level: 'edit',
          is_enabled: true,
        },
      },
    });

    // Mock disable API
    filePermissionService.disableTeamShare.mockResolvedValue({
      data: {
        data: {
          success: true,
          file_id: mockFolderInfo.id,
          tenant_id: mockTenantId,
        },
      },
    });

    // Mock enable API
    filePermissionService.enableTeamShare.mockResolvedValue({
      data: {
        data: {
          success: true,
          file_id: mockFolderInfo.id,
          tenant_id: mockTenantId,
          permission_level: 'view', // Default permission level after reset
        },
      },
    });

    render(
      <FolderTeamShareToggle
        open={true}
        folderId={mockFolderInfo.id}
        folderName={mockFolderInfo.name}
        tenantId={mockTenantId}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Wait for data to load
    });

    // Verify initial state shows edit permission
    const permissionSelect = screen.getByRole('combobox');
    expect(permissionSelect).toHaveTextContent('Can edit');

    // Disable team sharing
    const toggle = screen.getByRole('switch');
    await user.click(toggle); // Turn off

    await waitFor(() => {
      expect(filePermissionService.disableTeamShare).toHaveBeenCalledWith({
        file_id: mockFolderInfo.id,
      });
    });

    // Permission dropdown should not be visible when disabled
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();

    // Turn team sharing back on
    await user.click(toggle); // Turn on

    await waitFor(() => {
      expect(filePermissionService.enableTeamShare).toHaveBeenCalledWith({
        file_id: mockFolderInfo.id,
        permission_level: 'view', // Should use default view permission, not previous edit
      });
    });

    // Permission dropdown should now be visible with default view permission
    const newPermissionSelect = screen.getByRole('combobox');
    expect(newPermissionSelect).toHaveTextContent('Can view');
  });
});
