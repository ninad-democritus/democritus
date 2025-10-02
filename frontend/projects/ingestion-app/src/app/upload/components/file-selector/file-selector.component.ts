import { Component, Output, EventEmitter, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import * as JSZip from 'jszip';

interface FileInfo {
  file: File;
  fileName: string;
  fileType: string;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  source: 'direct' | 'folder' | 'zip';
  path?: string;
}

@Component({
  selector: 'app-file-selector',template: `
    <div class="file-selection-container">
      <!-- Hidden File Input -->
      <input 
        #fileInput 
        type="file" 
        multiple
        accept=".csv,.xlsx,.xls,.zip,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,text/csv,application/zip"
        (change)="onSelectionChange($event)"
        class="hidden"
      />
      
      <!-- Drop Zone -->
      <div class="file-selection-area" 
           (dragover)="onDragOver($event)"
           (dragleave)="onDragLeave($event)"
           (drop)="onDrop($event)"
           [class.drag-active]="isDragActive">
        
        <div class="flex items-center justify-center space-x-6">
          <!-- Upload Icon -->
          <svg class="file-selection-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
          </svg>
          
          <!-- Instructions -->
          <div class="text-left">
            <h3 class="file-selection-text">Upload files, folders, or zip archives</h3>
            <p class="file-selection-subtext">Supports CSV, Excel (.xlsx, .xls) files and ZIP archives</p>
            <p class="text-xs mt-1" style="color: var(--text-quaternary);">
              Automatically processes all subfolders • Mix files and folders freely
            </p>
          </div>
          
          <!-- Selection Button -->
          <div class="relative">
            <button 
              type="button" 
              (click)="showSelectionOptions()"
              class="file-input-button"
              [class.options-open]="showOptions">
              <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
              </svg>
              Select Files & Folders
            </button>
            
            <!-- Selection Options Popup -->
            <div *ngIf="showOptions" class="selection-options-popup">
              <button 
                type="button" 
                (click)="selectFiles()"
                class="option-button">
                <svg class="w-4 h-4 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
                <span>Select Files</span>
              </button>
              <button 
                type="button" 
                (click)="selectFolder()"
                class="option-button">
                <svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
                </svg>
                <span>Select Folder</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styleUrls: ['./file-selector.component.scss']
})
export class FileSelectorComponent {
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;
  @Output() filesSelected = new EventEmitter<FileInfo[]>();

  showOptions = false;
  isDragActive = false;
  private supportedExtensions = ['.csv', '.xlsx', '.xls'];

  showSelectionOptions() {
    this.showOptions = !this.showOptions;
  }

  selectFiles() {
    this.showOptions = false;
    if (this.fileInput?.nativeElement) {
      this.fileInput.nativeElement.removeAttribute('webkitdirectory');
      this.fileInput.nativeElement.click();
    }
  }

  selectFolder() {
    this.showOptions = false;
    if (this.fileInput?.nativeElement) {
      this.fileInput.nativeElement.setAttribute('webkitdirectory', '');
      this.fileInput.nativeElement.click();
    }
  }

  async onSelectionChange(event: any) {
    const files = Array.from(event.target.files) as File[];
    await this.processSelectedFiles(files, event.target.hasAttribute('webkitdirectory'));
    
    // Reset the input for next selection
    event.target.value = '';
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
    this.isDragActive = true;
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
    this.isDragActive = false;
  }

  async onDrop(event: DragEvent) {
    event.preventDefault();
    this.isDragActive = false;
    
    const files = Array.from(event.dataTransfer?.files || []);
    await this.processSelectedFiles(files, false);
  }

  private async processSelectedFiles(files: File[], isFolder: boolean) {
    const processedFiles: FileInfo[] = [];
    
    for (const file of files) {
      if (file.name.toLowerCase().endsWith('.zip') && !isFolder) {
        // Process zip file
        const zipFiles = await this.processZipFile(file);
        processedFiles.push(...zipFiles);
      } else if (this.isSupportedFile(file.name)) {
        // Regular file or folder file
        const relativePath = isFolder ? (file as any).webkitRelativePath || file.name : undefined;
        processedFiles.push({
          file,
          fileName: file.name,
          fileType: file.type || 'application/octet-stream',
          status: 'pending',
          source: isFolder ? 'folder' : 'direct',
          path: relativePath
        });
      }
    }
    
    if (processedFiles.length > 0) {
      this.filesSelected.emit(processedFiles);
    }
  }

  private async processZipFile(zipFile: File): Promise<FileInfo[]> {
    try {
      const zip = new JSZip();
      const contents = await zip.loadAsync(zipFile);
      const processedFiles: FileInfo[] = [];

      for (const [path, zipEntry] of Object.entries(contents.files)) {
        if (!zipEntry.dir && this.isSupportedFile(zipEntry.name)) {
          const blob = await zipEntry.async('blob');
          const file = new File([blob], zipEntry.name, { 
            type: this.getFileType(zipEntry.name),
            lastModified: zipEntry.date?.getTime() || Date.now()
          });
          
          processedFiles.push({
            file,
            fileName: zipEntry.name,
            fileType: file.type,
            status: 'pending',
            source: 'zip',
            path: path
          });
        }
      }

      return processedFiles;
    } catch (error) {
      console.error('Error processing zip file:', error);
      alert(`Error processing zip file: ${zipFile.name}`);
      return [];
    }
  }

  private isSupportedFile(fileName: string): boolean {
    const lowerName = fileName.toLowerCase();
    return this.supportedExtensions.some(ext => lowerName.endsWith(ext));
  }

  private getFileType(fileName: string): string {
    const lowerName = fileName.toLowerCase();
    if (lowerName.endsWith('.csv')) return 'text/csv';
    if (lowerName.endsWith('.xlsx')) return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
    if (lowerName.endsWith('.xls')) return 'application/vnd.ms-excel';
    return 'application/octet-stream';
  }
}

