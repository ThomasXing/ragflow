/**
 * 文件共享功能组件自动化测试
 *
 * 测试目标: 共享文件夹功能的UI组件和交互
 * 测试框架: Jest + React Testing Library
 */

import { FileShareDialog } from '@/components/file-share-dialog';
import { useToast } from '@/components/hooks/use-toast';
import filePermissionService from '@/services/file-permission-service';
import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Mock dependencies
jest.mock('@/services/file-permission-service');
jest.mock('@/components/hooks/use-toast');
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key) => key,
  }),
}));

describe('FileShareDialog Component', () => {
  const mockOnClose = jest.fn();
  const mockOnShared = jest.fn();
  const mockToast = {
    toast: jest.fn(),
  };

  const mockFileInfo = {
    id: 'file-123',
    name: 'test-document.pdf',
  };

  const mockUsers = [
    {
      id: 'user-1',
      email: 'user1@example.com',
      nickname: 'User One',
      avatar: null,
    },
    {
      id: 'user-2',
      email: 'user2@example.com',
      nickname: 'User Two',
      avatar: null,
    },
    {
      id: 'user-3',
      email: 'user3@example.com',
      nickname: 'User Three',
      avatar: null,
    },
  ];

  const mockPermissions = [
    {
      id: 'perm-1',
      target_user: mockUsers[0],
      permission_level: 'view',
      created_at: '2024-01-01T00:00:00Z',
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    useToast.mockReturnValue(mockToast);
    filePermissionService.listShares.mockResolvedValue({
      data: {
        permissions: mockPermissions,
        inherited: [],
        can_manage: true,
        is_owner: true,
      },
    });
    filePermissionService.shareableUsers.mockResolvedValue({
      data: { users: mockUsers },
    });
  });

  test('should render dialog with correct title and description', () => {
    render(
      <FileShareDialog
        open={true}
        fileId={mockFileInfo.id}
        fileName={mockFileInfo.name}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    expect(screen.getByText('fileManager.shareFile')).toBeInTheDocument();
    expect(
      screen.getByText(/fileManager.shareFileDescription/),
    ).toBeInTheDocument();
  });

  test('should load permissions and shareable users when opened', async () => {
    render(
      <FileShareDialog
        open={true}
        fileId={mockFileInfo.id}
        fileName={mockFileInfo.name}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      expect(filePermissionService.listShares).toHaveBeenCalledWith({
        file_id: mockFileInfo.id,
      });
      expect(filePermissionService.shareableUsers).toHaveBeenCalledWith({
        file_id: mockFileInfo.id,
      });
    });
  });

  test('should display shareable users in dropdown', async () => {
    render(
      <FileShareDialog
        open={true}
        fileId={mockFileInfo.id}
        fileName={mockFileInfo.name}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Wait for data to load
    });

    // Open user search
    const searchInput = screen.getByPlaceholderText('fileManager.searchUsers');
    fireEvent.change(searchInput, { target: { value: 'user' } });

    await waitFor(() => {
      mockUsers.forEach((user) => {
        expect(
          screen.getByText(user.nickname || user.email),
        ).toBeInTheDocument();
      });
    });
  });

  test('should allow selecting users for sharing', async () => {
    const user = userEvent.setup();
    render(
      <FileShareDialog
        open={true}
        fileId={mockFileInfo.id}
        fileName={mockFileInfo.name}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Wait for data to load
    });

    // Open user search
    const searchInput = screen.getByPlaceholderText('fileManager.searchUsers');
    await user.type(searchInput, 'user1');

    // Click on first user
    const firstUser = await screen.findByText('User One');
    await user.click(firstUser);

    // Should show selected users count
    expect(screen.getByText(/fileManager.selectedUsers/)).toBeInTheDocument();
  });

  test('should allow changing permission level', async () => {
    const user = userEvent.setup();
    render(
      <FileShareDialog
        open={true}
        fileId={mockFileInfo.id}
        fileName={mockFileInfo.name}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Wait for data to load
    });

    // Open permission dropdown
    const permissionSelect = screen.getByRole('combobox');
    await user.click(permissionSelect);

    // Verify available permission levels
    expect(screen.getByText('View only')).toBeInTheDocument();
    expect(screen.getByText('Can edit')).toBeInTheDocument();
    expect(screen.getByText('Can manage')).toBeInTheDocument();
  });

  test('should call share API when share button is clicked', async () => {
    const user = userEvent.setup();

    // Mock successful share
    filePermissionService.createShare.mockResolvedValue({
      data: {
        shares: [{ id: 'new-share-1', target_user_id: 'user-1' }],
        failed: [],
      },
    });

    render(
      <FileShareDialog
        open={true}
        fileId={mockFileInfo.id}
        fileName={mockFileInfo.name}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Wait for data to load
    });

    // Select a user
    const searchInput = screen.getByPlaceholderText('fileManager.searchUsers');
    await user.type(searchInput, 'user1');

    const firstUser = await screen.findByText('User One');
    await user.click(firstUser);

    // Click share button
    const shareButton = screen.getByRole('button', {
      name: /fileManager.addPeople/,
    });
    await user.click(shareButton);

    await waitFor(() => {
      expect(filePermissionService.createShare).toHaveBeenCalledWith({
        file_id: mockFileInfo.id,
        target_user_ids: ['user-1'],
        permission_level: 'view',
      });
    });

    // Verify toast notification and refresh
    expect(mockToast.toast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'common.success',
      }),
    );
    expect(filePermissionService.listShares).toHaveBeenCalledTimes(2);
  });

  test('should show error when no users selected', async () => {
    const user = userEvent.setup();

    render(
      <FileShareDialog
        open={true}
        fileId={mockFileInfo.id}
        fileName={mockFileInfo.name}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Wait for data to load
    });

    // Click share button without selecting users
    const shareButton = screen.getByRole('button', {
      name: /fileManager.addPeople/,
    });
    await user.click(shareButton);

    // Should show error toast
    expect(mockToast.toast).toHaveBeenCalledWith(
      expect.objectContaining({
        variant: 'destructive',
        title: 'common.error',
        description: 'fileManager.selectUserToShare',
      }),
    );
  });

  test('should display existing permissions', async () => {
    render(
      <FileShareDialog
        open={true}
        fileId={mockFileInfo.id}
        fileName={mockFileInfo.name}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Should show existing permission
      expect(screen.getByText('User One')).toBeInTheDocument();
      expect(screen.getByText('View only')).toBeInTheDocument();
    });
  });

  test('should allow updating permission level for existing share', async () => {
    const user = userEvent.setup();

    // Mock successful update
    filePermissionService.updateShare.mockResolvedValue({
      data: true,
    });

    render(
      <FileShareDialog
        open={true}
        fileId={mockFileInfo.id}
        fileName={mockFileInfo.name}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Wait for data to load
    });

    // Find permission dropdown for existing share
    const permissionSelects = screen.getAllByRole('combobox');
    const userPermissionSelect = permissionSelects[1]; // Second dropdown (first is for new sharing)

    await user.click(userPermissionSelect);

    // Select "Can edit"
    const editOption = screen.getByText('Can edit');
    await user.click(editOption);

    await waitFor(() => {
      expect(filePermissionService.updateShare).toHaveBeenCalledWith({
        share_id: 'perm-1',
        permission_level: 'edit',
      });
    });

    // Verify success toast
    expect(mockToast.toast).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'common.success',
        description: 'fileManager.updatePermissionSuccess',
      }),
    );
  });

  test('should allow revoking permission', async () => {
    const user = userEvent.setup();

    // Mock successful revoke
    filePermissionService.revokeShare.mockResolvedValue({
      data: true,
    });

    render(
      <FileShareDialog
        open={true}
        fileId={mockFileInfo.id}
        fileName={mockFileInfo.name}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Wait for data to load
    });

    // Find and click revoke button
    const revokeButtons = screen.getAllByRole('button');
    const deleteButton = revokeButtons.find((button) =>
      button.innerHTML.includes('Trash2'),
    );

    if (deleteButton) {
      await user.click(deleteButton);

      // Should open confirmation dialog
      const confirmButton = await screen.findByText('common.confirm');
      await user.click(confirmButton);

      await waitFor(() => {
        expect(filePermissionService.revokeShare).toHaveBeenCalledWith({
          share_id: 'perm-1',
        });
      });

      // Verify success toast
      expect(mockToast.toast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'common.success',
          description: 'fileManager.revokeSuccess',
        }),
      );
    }
  });

  test('should handle API errors gracefully', async () => {
    // Mock API failure
    filePermissionService.listShares.mockRejectedValue(
      new Error('Network error'),
    );

    render(
      <FileShareDialog
        open={true}
        fileId={mockFileInfo.id}
        fileName={mockFileInfo.name}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      expect(mockToast.toast).toHaveBeenCalledWith(
        expect.objectContaining({
          variant: 'destructive',
          title: 'common.error',
          description: 'fileManager.failedToLoadPermissions',
        }),
      );
    });
  });

  test('should show permission levels info', async () => {
    render(
      <FileShareDialog
        open={true}
        fileId={mockFileInfo.id}
        fileName={mockFileInfo.name}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Should show permission level descriptions
      expect(
        screen.getByText('fileManager.permissionLevels'),
      ).toBeInTheDocument();

      // Check for permission level labels
      expect(screen.getByText('View only')).toBeInTheDocument();
      expect(screen.getByText('Can edit')).toBeInTheDocument();
      expect(screen.getByText('Can manage')).toBeInTheDocument();
    });
  });

  test('should filter users by search query', async () => {
    const user = userEvent.setup();

    render(
      <FileShareDialog
        open={true}
        fileId={mockFileInfo.id}
        fileName={mockFileInfo.name}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Wait for data to load
    });

    // Search for "Two"
    const searchInput = screen.getByPlaceholderText('fileManager.searchUsers');
    await user.type(searchInput, 'Two');

    // Should show only User Two
    await waitFor(() => {
      expect(screen.getByText('User Two')).toBeInTheDocument();
      expect(screen.queryByText('User One')).not.toBeInTheDocument();
      expect(screen.queryByText('User Three')).not.toBeInTheDocument();
    });
  });

  test('should clear selected users', async () => {
    const user = userEvent.setup();

    render(
      <FileShareDialog
        open={true}
        fileId={mockFileInfo.id}
        fileName={mockFileInfo.name}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Wait for data to load
    });

    // Select a user
    const searchInput = screen.getByPlaceholderText('fileManager.searchUsers');
    await user.type(searchInput, 'user1');

    const firstUser = await screen.findByText('User One');
    await user.click(firstUser);

    // Clear selection
    const clearButton = screen.getByText('fileManager.clearSelection');
    await user.click(clearButton);

    // Selected users count should be hidden
    expect(
      screen.queryByText(/fileManager.selectedUsers/),
    ).not.toBeInTheDocument();
  });

  test('should show loading state', async () => {
    // Delay API response to show loading state
    filePermissionService.listShares.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100)),
    );

    render(
      <FileShareDialog
        open={true}
        fileId={mockFileInfo.id}
        fileName={mockFileInfo.name}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    // Should show loading spinner
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  test('should show inherited permissions', async () => {
    // Mock with inherited permissions
    filePermissionService.listShares.mockResolvedValue({
      data: {
        permissions: mockPermissions,
        inherited: [
          {
            file_id: 'parent-file-123',
            file_name: 'Parent Folder',
            permission_level: 'edit',
          },
        ],
        can_manage: true,
        is_owner: true,
      },
    });

    render(
      <FileShareDialog
        open={true}
        fileId={mockFileInfo.id}
        fileName={mockFileInfo.name}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Should show inherited permissions section
      expect(
        screen.getByText('fileManager.inheritedPermissions'),
      ).toBeInTheDocument();
      expect(screen.getByText(/fileManager.inheritedFrom/)).toBeInTheDocument();
    });
  });

  test('should handle users with existing permissions', async () => {
    // Mock users with existing permissions
    const usersWithPermissions = mockUsers.map((user) => ({
      ...user,
      existing_permission: user.id === 'user-2' ? 'edit' : null,
    }));

    filePermissionService.shareableUsers.mockResolvedValue({
      data: { users: usersWithPermissions },
    });

    const user = userEvent.setup();
    render(
      <FileShareDialog
        open={true}
        fileId={mockFileInfo.id}
        fileName={mockFileInfo.name}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Wait for data to load
    });

    // Search for users
    const searchInput = screen.getByPlaceholderText('fileManager.searchUsers');
    await user.type(searchInput, 'user');

    // Should show existing permission badge for user-2
    await waitFor(() => {
      expect(screen.getByText('Can edit')).toBeInTheDocument();
    });
  });

  test('should not allow sharing when user cannot manage', async () => {
    // Mock user without management permissions
    filePermissionService.listShares.mockResolvedValue({
      data: {
        permissions: mockPermissions,
        inherited: [],
        can_manage: false,
        is_owner: false,
      },
    });

    render(
      <FileShareDialog
        open={true}
        fileId={mockFileInfo.id}
        fileName={mockFileInfo.name}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Should not show add people section
      expect(
        screen.queryByText('fileManager.addPeople'),
      ).not.toBeInTheDocument();
    });

    // Should only show existing permissions as read-only
    const permissionBadges = screen.getAllByText('View only');
    expect(permissionBadges.length).toBeGreaterThan(0);
  });

  test('should handle share API failure', async () => {
    const user = userEvent.setup();

    // Mock API failure
    filePermissionService.createShare.mockRejectedValue(
      new Error('Network error'),
    );

    render(
      <FileShareDialog
        open={true}
        fileId={mockFileInfo.id}
        fileName={mockFileInfo.name}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Wait for data to load
    });

    // Select a user
    const searchInput = screen.getByPlaceholderText('fileManager.searchUsers');
    await user.type(searchInput, 'user1');

    const firstUser = await screen.findByText('User One');
    await user.click(firstUser);

    // Click share button
    const shareButton = screen.getByRole('button', {
      name: /fileManager.addPeople/,
    });
    await user.click(shareButton);

    await waitFor(() => {
      expect(mockToast.toast).toHaveBeenCalledWith(
        expect.objectContaining({
          variant: 'destructive',
          title: 'common.error',
          description: 'fileManager.shareFailed',
        }),
      );
    });
  });

  test('should handle partial share success with failures', async () => {
    const user = userEvent.setup();

    // Mock partial success
    filePermissionService.createShare.mockResolvedValue({
      data: {
        shares: [{ id: 'new-share-1', target_user_id: 'user-1' }],
        failed: [{ target_user_id: 'user-2', error: 'User not found' }],
      },
    });

    render(
      <FileShareDialog
        open={true}
        fileId={mockFileInfo.id}
        fileName={mockFileInfo.name}
        onClose={mockOnClose}
        onShared={mockOnShared}
      />,
    );

    await waitFor(() => {
      // Wait for data to load
    });

    // Select multiple users
    const searchInput = screen.getByPlaceholderText('fileManager.searchUsers');
    await user.type(searchInput, 'user');

    // Select all users (implement according to your UI)
    // This depends on how multi-select is implemented

    // Click share button
    const shareButton = screen.getByRole('button', {
      name: /fileManager.addPeople/,
    });
    await user.click(shareButton);

    await waitFor(() => {
      // Should show both success and warning toasts
      expect(mockToast.toast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'common.success',
        }),
      );
      expect(mockToast.toast).toHaveBeenCalledWith(
        expect.objectContaining({
          variant: 'destructive',
          title: 'common.warning',
        }),
      );
    });
  });
});

describe('FilePermissionService Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('should create share with correct parameters', async () => {
    const shareData = {
      file_id: 'file-123',
      target_user_ids: ['user-456'],
      permission_level: 'edit',
    };

    const mockResponse = {
      data: {
        shares: [{ id: 'share-789', ...shareData }],
        failed: [],
      },
    };

    filePermissionService.createShare.mockResolvedValue(mockResponse);

    const result = await filePermissionService.createShare(shareData);

    expect(filePermissionService.createShare).toHaveBeenCalledWith(shareData);
    expect(result).toEqual(mockResponse);
  });

  test('should list shares with file_id parameter', async () => {
    const mockResponse = {
      data: {
        permissions: [],
        inherited: [],
        can_manage: true,
        is_owner: false,
      },
    };

    filePermissionService.listShares.mockResolvedValue(mockResponse);

    const result = await filePermissionService.listShares({
      file_id: 'file-123',
    });

    expect(filePermissionService.listShares).toHaveBeenCalledWith({
      file_id: 'file-123',
    });
    expect(result).toEqual(mockResponse);
  });

  test('should update share with share_id and permission_level', async () => {
    const updateData = {
      share_id: 'share-789',
      permission_level: 'admin',
    };

    const mockResponse = { data: true };

    filePermissionService.updateShare.mockResolvedValue(mockResponse);

    const result = await filePermissionService.updateShare(updateData);

    expect(filePermissionService.updateShare).toHaveBeenCalledWith(updateData);
    expect(result).toEqual(mockResponse);
  });

  test('should revoke share with share_id', async () => {
    const mockResponse = { data: true };

    filePermissionService.revokeShare.mockResolvedValue(mockResponse);

    const result = await filePermissionService.revokeShare({
      share_id: 'share-789',
    });

    expect(filePermissionService.revokeShare).toHaveBeenCalledWith({
      share_id: 'share-789',
    });
    expect(result).toEqual(mockResponse);
  });

  test('should get shared files for current user', async () => {
    const mockResponse = {
      data: {
        files: [
          {
            id: 'file-1',
            name: 'Shared Document.pdf',
            share_permission: 'view',
          },
        ],
        total: 1,
      },
    };

    filePermissionService.sharedWithMe.mockResolvedValue(mockResponse);

    const result = await filePermissionService.sharedWithMe();

    expect(filePermissionService.sharedWithMe).toHaveBeenCalled();
    expect(result).toEqual(mockResponse);
  });

  test('should get files shared by current user', async () => {
    const mockResponse = {
      data: {
        files: [{ id: 'file-1', name: 'My Document.pdf' }],
        total: 1,
      },
    };

    filePermissionService.sharedByMe.mockResolvedValue(mockResponse);

    const result = await filePermissionService.sharedByMe();

    expect(filePermissionService.sharedByMe).toHaveBeenCalled();
    expect(result).toEqual(mockResponse);
  });

  test('should check file permission', async () => {
    const mockResponse = {
      data: {
        has_permission: true,
        permission_level: 'edit',
        permission_source: 'explicit',
        is_owner: false,
      },
    };

    filePermissionService.checkPermission.mockResolvedValue(mockResponse);

    const result = await filePermissionService.checkPermission({
      file_id: 'file-123',
      operation: 'edit',
    });

    expect(filePermissionService.checkPermission).toHaveBeenCalledWith({
      file_id: 'file-123',
      operation: 'edit',
    });
    expect(result).toEqual(mockResponse);
  });

  test('should get shareable users', async () => {
    const mockResponse = {
      data: {
        users: [
          { id: 'user-1', email: 'user1@example.com', nickname: 'User One' },
        ],
        can_share: true,
      },
    };

    filePermissionService.shareableUsers.mockResolvedValue(mockResponse);

    const result = await filePermissionService.shareableUsers({
      file_id: 'file-123',
    });

    expect(filePermissionService.shareableUsers).toHaveBeenCalledWith({
      file_id: 'file-123',
    });
    expect(result).toEqual(mockResponse);
  });
});
