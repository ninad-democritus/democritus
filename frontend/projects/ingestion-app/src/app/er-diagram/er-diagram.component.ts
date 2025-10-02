import { Component, OnInit, OnChanges, SimpleChanges, ViewChild, ElementRef, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';

// Import modular components
import { ZoomControlsComponent } from './components/zoom-controls/zoom-controls.component';

interface Column {
  name: string;
  data_type: string;
  nullable: boolean;
  primary_key: boolean;
  unique: boolean;
  description?: string;
  business_context?: string;
  tags?: string[];
}

interface Entity {
  name: string;
  table_name: string;
  description?: string;
  business_description?: string;
  business_purpose?: string;
  domain_classification?: string;
  key_business_attributes?: string[];
  suggested_use_cases?: string[];
  columns: Column[];
  column_details: Column[];
  // Layout properties
  x: number;
  y: number;
  width: number;
  height: number;
}

interface Relationship {
  from: string;
  to: string;
  from_column: string;
  to_column: string;
  relationship_type: string;
  confidence: number;
  // Layout properties
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  // Drag target properties
  target_entity?: number;
  target_column?: number;
}

interface SchemaData {
  entities: any[];
  relationships: any[];
}

@Component({
  selector: 'app-er-diagram',templateUrl: './er-diagram.component.html',
  styleUrls: ['./er-diagram.component.scss']
})
export class ErDiagramComponent implements OnInit, OnChanges {
  @ViewChild('diagramContainer', { static: true }) diagramContainer!: ElementRef;
  @Input() schemaData: SchemaData | null = null;
  @Output() schemaChanged = new EventEmitter<SchemaData>();

  // SVG dimensions
  svgWidth = 1200;
  svgHeight = 800;

  // Zoom and Pan state
  zoom = 1;
  panX = 0;
  panY = 0;
  minZoom = 0.25;
  maxZoom = 4;
  
  // Touch and interaction state
  private isDragging = false;
  private isDraggingRelationship = false;
  private dragStartX = 0;
  private dragStartY = 0;
  private lastTouchDistance = 0;
  private touchStartZoom = 1;
  private draggedRelationshipIndex = -1;

  // Data
  entities: Entity[] = [];
  relationships: Relationship[] = [];
  localSchema: SchemaData = { entities: [], relationships: [] };
  hasChanges = false;

  // Selection and editing state
  selectedEntityIndex = -1;
  selectedRelationship: Relationship | null = null;
  editingColumn = { entityIndex: -1, columnIndex: -1 };
  editingColumnName = '';
  editingColumnType = '';
  
  // Data types for dropdown
  dataTypes = [
    'VARCHAR(50)', 'VARCHAR(255)', 'VARCHAR(1000)',
    'INTEGER', 'BIGINT', 'DECIMAL', 'FLOAT',
    'BOOLEAN', 'TIMESTAMP', 'DATETIME', 'DATE',
    'TEXT', 'JSON', 'UUID'
  ];

  constructor(private router: Router, private http: HttpClient) {}

  ngOnInit() {
    if (this.schemaData) {
      this.loadSchema(this.schemaData);
    }
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['schemaData'] && this.schemaData) {
      this.loadSchema(this.schemaData);
    }
  }

  loadSchema(schema: SchemaData) {
    this.localSchema = JSON.parse(JSON.stringify(schema));
    this.entities = this.processEntities(schema.entities || []);
    this.relationships = this.processRelationships(schema.relationships || []);
    this.layoutEntities();
    this.layoutRelationships();
    
    // Debug log
    console.log('Loaded entities:', this.entities.length);
    console.log('Loaded relationships:', this.relationships.length);
    this.relationships.forEach(rel => {
      console.log(`Relationship: ${rel.from}.${rel.from_column} -> ${rel.to}.${rel.to_column}`);
    });
  }

  private processEntities(rawEntities: any[]): Entity[] {
    if (!rawEntities || rawEntities.length === 0) {
      return [];
    }
    
    return rawEntities.map((entity, index) => {
      const columns = this.processColumns(entity);
      const entityHeight = Math.max(120, 70 + (columns.length * 32) + 20);
      
      return {
        name: entity.name || entity.table_name || `Entity_${index}`,
        table_name: entity.table_name || entity.name || `Entity_${index}`,
        description: entity.description || entity.business_description || '',
        business_description: entity.business_description || entity.description || '',
        business_purpose: entity.business_purpose || '',
        domain_classification: entity.domain_classification || '',
        key_business_attributes: entity.key_business_attributes || [],
        suggested_use_cases: entity.suggested_use_cases || [],
        columns: columns,
        column_details: columns,
        x: 0,
        y: 0,
        width: 320,
        height: entityHeight
      };
    });
  }

  private processColumns(entity: any): Column[] {
    let columns: Column[] = [];
    
    // Check for column_details first (this has the full column objects)
    if (entity.column_details && Array.isArray(entity.column_details)) {
      columns = entity.column_details.map((col: any) => ({
        name: col.name,
        data_type: this.mapDataType(col.data_type),
        nullable: col.null_percentage > 0,
        primary_key: col.name === entity.primary_key,
        unique: col.distinct_count === col.total_count && col.total_count > 0,
        description: col.description || '',
        business_context: col.business_context || '',
        tags: col.tags || []
      }));
    } else if (entity.columns && Array.isArray(entity.columns)) {
      // If columns is an array of objects with name/data_type
      if (entity.columns.length > 0 && typeof entity.columns[0] === 'object') {
        columns = entity.columns;
      } else {
        // If columns is an array of strings, create column objects
        columns = entity.columns.map((name: string) => ({
          name: name,
          data_type: 'VARCHAR(255)',
          nullable: true,
          primary_key: name === entity.primary_key,
          unique: false
        }));
      }
    } else if (typeof entity.columns === 'string') {
      // Parse string format columns
      const columnNames = entity.columns.split(' ').filter((name: string) => name.trim());
      columns = columnNames.map((name: string) => ({
        name: name.trim(),
        data_type: 'VARCHAR(255)',
        nullable: true,
        primary_key: name === entity.primary_key,
        unique: false
      }));
    } else {
      // Create a default column if none found
      columns = [{
        name: 'id',
        data_type: 'INTEGER',
        nullable: false,
        primary_key: true,
        unique: true
      }];
    }

    return columns;
  }
  
  private mapDataType(backendType: string): string {
    // Map backend data types to SQL-like types
    const typeMap: { [key: string]: string } = {
      'integer': 'INTEGER',
      'float': 'FLOAT',
      'numeric': 'DECIMAL',
      'string': 'VARCHAR(255)',
      'text': 'TEXT',
      'boolean': 'BOOLEAN',
      'datetime': 'DATETIME',
      'date': 'DATE',
      'timestamp': 'TIMESTAMP'
    };
    
    return typeMap[backendType?.toLowerCase()] || backendType?.toUpperCase() || 'VARCHAR(255)';
  }

  private processRelationships(rawRelationships: any[]): Relationship[] {
    return rawRelationships.map(rel => ({
      ...rel,
      x1: 0,
      y1: 0,
      x2: 0,
      y2: 0
    }));
  }

  private layoutEntities() {
    const entitiesPerRow = Math.ceil(Math.sqrt(this.entities.length));
    const entitySpacing = 360;
    const rowHeight = 400;
    const padding = 50;

    this.entities.forEach((entity, index) => {
      const row = Math.floor(index / entitiesPerRow);
      const col = index % entitiesPerRow;
      
      entity.x = padding + (col * entitySpacing);
      entity.y = padding + (row * rowHeight);
    });

    // Update SVG dimensions
    const maxRow = Math.ceil(this.entities.length / entitiesPerRow);
    this.svgWidth = Math.max(1200, (entitiesPerRow * entitySpacing) + (padding * 2));
    this.svgHeight = Math.max(800, (maxRow * rowHeight) + (padding * 2));
  }

  private layoutRelationships() {
    this.relationships.forEach(relationship => {
      const fromEntity = this.entities.find(e => e.name === relationship.from);
      const toEntity = this.entities.find(e => e.name === relationship.to);
      
      if (fromEntity && toEntity) {
        // Find column positions
        const fromColumns = fromEntity.columns || fromEntity.column_details || [];
        const toColumns = toEntity.columns || toEntity.column_details || [];
        
        const fromColumnIndex = fromColumns.findIndex(col => col.name === relationship.from_column);
        const toColumnIndex = toColumns.findIndex(col => col.name === relationship.to_column);
        
        // Use valid indices or default to first column
        const validFromIndex = fromColumnIndex >= 0 ? fromColumnIndex : 0;
        const validToIndex = toColumnIndex >= 0 ? toColumnIndex : 0;
        
        // Calculate exact column row positions
        const fromColumnY = fromEntity.y + 70 + (validFromIndex * 32) + 16; // Center of column row
        const toColumnY = toEntity.y + 70 + (validToIndex * 32) + 16; // Center of column row
        
        // Calculate connection points at column level
        const fromColumnX = fromEntity.x + 270; // Right edge of column area (before action buttons)
        const toColumnX = toEntity.x + 50; // Start of column area (after icons)
        
        // Set precise connection points
        relationship.x1 = fromColumnX;
        relationship.y1 = fromColumnY;
        relationship.x2 = toColumnX;
        relationship.y2 = toColumnY;
        
        console.log(`Relationship: ${relationship.from}.${relationship.from_column} -> ${relationship.to}.${relationship.to_column}`);
        console.log(`From column index: ${validFromIndex}, To column index: ${validToIndex}`);
        console.log(`Line coordinates: (${relationship.x1}, ${relationship.y1}) -> (${relationship.x2}, ${relationship.y2})`);
      }
    });
  }

  // Event Handlers for Entity Component
  onEntityClick(entityIndex: number) {
    this.selectedEntityIndex = entityIndex;
    this.selectedRelationship = null;
    this.clearSelection();
  }

  onAddColumn(entityIndex: number) {
    const entity = this.entities[entityIndex];
    if (entity) {
      const newColumn: Column = {
        name: 'new_column',
        data_type: 'VARCHAR(255)',
        nullable: true,
        primary_key: false,
        unique: false
      };
      
      entity.columns.push(newColumn);
      entity.column_details = entity.columns;
      this.hasChanges = true;
      this.updateEntityHeight(entityIndex);
      this.layoutRelationships(); // Recalculate relationships after adding column
      
      // Start editing the new column
      this.startEditingColumn(entityIndex, entity.columns.length - 1);
    }
  }



  // Event Handlers for Relationship Component
  onRelationshipClick(relationship: Relationship) {
    this.selectedRelationship = relationship;
    this.selectedEntityIndex = -1;
  }

  onRelationshipDragStart(event: { event: MouseEvent, relationship: Relationship, index: number }) {
    this.isDraggingRelationship = true;
    this.draggedRelationshipIndex = event.index;
    this.dragStartX = event.event.clientX;
    this.dragStartY = event.event.clientY;
  }

  onDeleteRelationship(relationship: Relationship) {
    const index = this.relationships.indexOf(relationship);
    if (index > -1) {
      this.relationships.splice(index, 1);
      this.selectedRelationship = null;
      this.hasChanges = true;
    }
  }

  // Zoom Control Event Handlers
  onZoomIn() {
    this.zoomIn();
  }

  onZoomOut() {
    this.zoomOut();
  }

  onResetZoom() {
    this.resetZoom();
  }

  onFitToScreen() {
    this.fitToScreen();
  }

  // Helper Methods
  startEditingColumn(entityIndex: number, columnIndex: number) {
    this.editingColumn = { entityIndex, columnIndex };
    const entity = this.entities[entityIndex];
    if (entity && entity.columns[columnIndex]) {
      this.editingColumnName = entity.columns[columnIndex].name;
      this.editingColumnType = entity.columns[columnIndex].data_type;
    }
  }

  saveColumnEdit(entityIndex: number, columnIndex: number) {
    const entity = this.entities[entityIndex];
    if (entity && entity.columns[columnIndex]) {
      entity.columns[columnIndex].name = this.editingColumnName.trim() || entity.columns[columnIndex].name;
      entity.columns[columnIndex].data_type = this.editingColumnType;
      entity.column_details = entity.columns;
      this.hasChanges = true;
      this.layoutRelationships(); // Recalculate relationships after column edit
    }
    this.stopColumnEdit();
  }

  cancelColumnEdit() {
    this.stopColumnEdit();
  }

  private stopColumnEdit() {
    this.editingColumn = { entityIndex: -1, columnIndex: -1 };
  }

  private deleteColumn(entityIndex: number, columnIndex: number) {
    const entity = this.entities[entityIndex];
    if (entity && entity.columns.length > 1) {
      entity.columns.splice(columnIndex, 1);
      entity.column_details = entity.columns;
      this.hasChanges = true;
      this.updateEntityHeight(entityIndex);
    }
  }

  private updateEntityHeight(entityIndex: number) {
    const entity = this.entities[entityIndex];
    if (entity) {
      entity.height = Math.max(120, 70 + (entity.columns.length * 32) + 20);
    }
  }

  private clearSelection() {
    this.selectedEntityIndex = -1;
    this.selectedRelationship = null;
  }

  // Zoom and Pan Methods
  zoomIn() {
    const newZoom = Math.min(this.maxZoom, this.zoom * 1.2);
    if (newZoom !== this.zoom) {
      this.zoom = newZoom;
      this.updateSvgTransform();
    }
  }

  zoomOut() {
    const newZoom = Math.max(this.minZoom, this.zoom / 1.2);
    if (newZoom !== this.zoom) {
      this.zoom = newZoom;
      this.updateSvgTransform();
    }
  }

  resetZoom() {
    this.zoom = 1;
    this.panX = 0;
    this.panY = 0;
    this.updateSvgTransform();
  }

  fitToScreen() {
    // Simple fit to screen - center the content
    this.zoom = 0.8;
    this.panX = 0;
    this.panY = 0;
    this.updateSvgTransform();
  }

  private updateSvgTransform() {
    const svg = this.diagramContainer?.nativeElement?.querySelector('.er-svg');
    if (svg) {
      svg.style.transform = `translate(${this.panX}px, ${this.panY}px) scale(${this.zoom})`;
    }
  }

  // Save Changes
  async submitChanges() {
    if (!this.hasChanges) return;

    const updatedSchema = {
      entities: this.entities.map(entity => ({
        ...entity,
        columns: entity.columns.filter(col => col.name !== 'new_column' && col.name.trim() !== '')
      })),
      relationships: this.relationships
    };

    this.schemaChanged.emit(updatedSchema);
    this.hasChanges = false;
  }

  resetChanges() {
    if (this.schemaData) {
      this.loadSchema(this.schemaData);
      this.hasChanges = false;
    }
  }
}