import { Component, EventEmitter, Input, Output } from '@angular/core';

export interface SaveDashboardForm {
  name: string;
  visibility: 'private' | 'public';
  dashboardType: 'static' | 'dynamic';
}

@Component({
  selector: 'app-save-dashboard-modal',
  templateUrl: './save-dashboard-modal.component.html',
  styleUrls: ['./save-dashboard-modal.component.scss']
})
export class SaveDashboardModalComponent {
  @Input() isOpen = false;
  @Output() save = new EventEmitter<SaveDashboardForm>();
  @Output() cancel = new EventEmitter<void>();

  formData: SaveDashboardForm = {
    name: '',
    visibility: 'private',
    dashboardType: 'dynamic'
  };

  get isFormValid(): boolean {
    return this.formData.name.trim().length >= 3;
  }

  onSave() {
    if (this.isFormValid) {
      this.save.emit(this.formData);
      this.resetForm();
    }
  }

  onCancel() {
    this.cancel.emit();
    this.resetForm();
  }

  private resetForm() {
    this.formData = {
      name: '',
      visibility: 'private',
      dashboardType: 'dynamic'
    };
  }
}

