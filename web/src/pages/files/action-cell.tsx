import {
  ConfirmDeleteDialog,
  ConfirmDeleteDialogNode,
} from '@/components/confirm-delete-dialog';
import { FileTeamShareToggle } from '@/components/file-team-share-toggle';
import { FolderTeamShareToggle } from '@/components/folder-team-share-toggle';
import { FileIcon } from '@/components/icon-font';
import NewDocumentLink from '@/components/new-document-link';
import { Button } from '@/components/ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { useDownloadFile } from '@/hooks/use-file-request';
import { IFile } from '@/interfaces/database/file-manager';
import { cn } from '@/lib/utils';
import {
  getExtension,
  isSupportedPreviewDocumentType,
} from '@/utils/document-util';
import { CellContext } from '@tanstack/react-table';
import { t } from 'i18next';
import {
  ArrowDownToLine,
  Eye,
  FolderInput,
  FolderPen,
  Link2,
  Share2,
  Trash2,
} from 'lucide-react';
import { useCallback, useState } from 'react';
import {
  UseHandleConnectToKnowledgeReturnType,
  UseRenameCurrentFileReturnType,
} from './hooks';
import { useHandleDeleteFile } from './use-delete-file';
import { UseMoveDocumentShowType } from './use-move-file';
import { isFolderType, isKnowledgeBaseType } from './util';

type IProps = Pick<CellContext<IFile, unknown>, 'row'> &
  Pick<UseHandleConnectToKnowledgeReturnType, 'showConnectToKnowledgeModal'> &
  Pick<UseRenameCurrentFileReturnType, 'showFileRenameModal'> &
  UseMoveDocumentShowType;

export function ActionCell({
  row,
  showConnectToKnowledgeModal,
  showFileRenameModal,
  showMoveFileModal,
}: IProps) {
  const record = row.original;
  const documentId = record.id;
  const name: string = row.getValue('name');
  const type = record.type;

  const { downloadFile } = useDownloadFile();
  const isFolder = isFolderType(record.type);
  const extension = getExtension(record.name);
  const isKnowledgeBase = isKnowledgeBaseType(record.source_type);

  // Share popover state
  const [sharePopoverOpen, setSharePopoverOpen] = useState(false);

  const handleShowConnectToKnowledgeModal = useCallback(() => {
    showConnectToKnowledgeModal(record);
  }, [record, showConnectToKnowledgeModal]);

  const onDownloadDocument = useCallback(() => {
    downloadFile({
      id: documentId,
      filename: record.name,
    });
  }, [documentId, downloadFile, record.name]);

  const handleShowFileRenameModal = useCallback(() => {
    showFileRenameModal(record);
  }, [record, showFileRenameModal]);

  const handleShowMoveFileModal = useCallback(() => {
    showMoveFileModal([record.id]);
  }, [record, showMoveFileModal]);

  const { handleRemoveFile } = useHandleDeleteFile();

  const onRemoveFile = useCallback(() => {
    handleRemoveFile([documentId]);
  }, [handleRemoveFile, documentId]);

  return (
    <>
      <section className="flex gap-2 items-center text-text-sub-title-invert opacity-0 group-hover:opacity-100 transition-opacity">
        {isKnowledgeBase || (
          <Popover open={sharePopoverOpen} onOpenChange={setSharePopoverOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="transparent"
                className="border-none hover:bg-bg-card text-text-primary"
                size="icon-sm"
                title={t('fileManager.share')}
              >
                <Share2 />
              </Button>
            </PopoverTrigger>
            <PopoverContent
              className="w-80"
              align="start"
              side="bottom"
              sideOffset={4}
              onClick={(e) => e.stopPropagation()}
            >
              {isFolder ? (
                <FolderTeamShareToggle
                  folderId={documentId}
                  folderName={name}
                  isOwner={record.tenant_id === record.created_by}
                  canManage={true}
                  tenantId={record.tenant_id || ''}
                  onStatusChange={() => {
                    // Optionally refresh the file list after sharing status changes
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
                    // Optionally refresh the file list after sharing status changes
                  }}
                />
              )}
            </PopoverContent>
          </Popover>
        )}
        {isKnowledgeBase || (
          <Button
            variant="transparent"
            className="border-none hover:bg-bg-card text-text-primary"
            size="icon-sm"
            onClick={handleShowConnectToKnowledgeModal}
          >
            <Link2 />
          </Button>
        )}
        {isKnowledgeBase || (
          <Button
            variant="transparent"
            className="border-none hover:bg-bg-card text-text-primary"
            size="icon-sm"
            onClick={handleShowMoveFileModal}
          >
            <FolderInput />
          </Button>
        )}
        {isKnowledgeBase || (
          <Button
            variant="transparent"
            className="border-none hover:bg-bg-card text-text-primary"
            size="icon-sm"
            onClick={handleShowFileRenameModal}
          >
            <FolderPen />
          </Button>
        )}
        {isFolder || (
          <Button
            variant="transparent"
            className="border-none hover:bg-bg-card text-text-primary"
            size="icon-sm"
            onClick={onDownloadDocument}
          >
            <ArrowDownToLine />
          </Button>
        )}

        {isSupportedPreviewDocumentType(extension) && (
          <NewDocumentLink
            documentId={documentId}
            documentName={record.name}
            resource="files"
            className="text-text-sub-title-invert"
          >
            <Button
              variant="transparent"
              className="border-none hover:bg-bg-card text-text-primary"
              size="icon-sm"
            >
              <Eye />
            </Button>
          </NewDocumentLink>
        )}

        {isKnowledgeBase || (
          <ConfirmDeleteDialog
            onOk={onRemoveFile}
            title={t('deleteModal.delFile')}
            content={{
              node: (
                <ConfirmDeleteDialogNode>
                  <div className="flex items-center gap-2 text-text-secondary">
                    <span className="size-4">
                      <FileIcon name={name} type={type}></FileIcon>
                    </span>
                    <span
                      className={cn('truncate text-xs', {
                        ['cursor-pointer']: isFolder,
                      })}
                    >
                      {name}
                    </span>
                  </div>
                </ConfirmDeleteDialogNode>
              ),
            }}
          >
            <Button
              variant="transparent"
              className="border-none hover:bg-bg-card text-text-primary"
              size="icon-sm"
            >
              <Trash2 />
            </Button>
          </ConfirmDeleteDialog>
        )}
      </section>
    </>
  );
}
