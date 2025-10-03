/**
 * Chart Type Model
 * Defines the structure for different chart types available in the library
 */

export interface ChartType {
  id: string;
  name: string;
  icon: string; // SVG icon or icon class
  category: 'basic' | 'advanced' | 'statistical';
  description: string;
  defaultSize: { cols: number; rows: number };
}

/**
 * Predefined chart types available in the system
 */
export const CHART_TYPES: ChartType[] = [
  {
    id: 'bar',
    name: 'Bar Chart',
    icon: 'chart-bar',
    category: 'basic',
    description: 'Compare values across categories',
    defaultSize: { cols: 4, rows: 3 }
  },
  {
    id: 'line',
    name: 'Line Chart',
    icon: 'chart-line',
    category: 'basic',
    description: 'Show trends over time',
    defaultSize: { cols: 6, rows: 3 }
  },
  {
    id: 'pie',
    name: 'Pie Chart',
    icon: 'chart-pie',
    category: 'basic',
    description: 'Display proportions and percentages',
    defaultSize: { cols: 4, rows: 3 }
  },
  {
    id: 'area',
    name: 'Area Chart',
    icon: 'chart-area',
    category: 'basic',
    description: 'Show trends with filled areas',
    defaultSize: { cols: 6, rows: 3 }
  },
  {
    id: 'scatter',
    name: 'Scatter Plot',
    icon: 'chart-scatter',
    category: 'advanced',
    description: 'Show correlation between variables',
    defaultSize: { cols: 6, rows: 4 }
  },
  {
    id: 'table',
    name: 'Data Table',
    icon: 'table',
    category: 'basic',
    description: 'Display raw data in tabular format',
    defaultSize: { cols: 6, rows: 4 }
  },
  {
    id: 'kpi',
    name: 'KPI Card',
    icon: 'chart-kpi',
    category: 'basic',
    description: 'Display single key metric',
    defaultSize: { cols: 3, rows: 2 }
  },
  {
    id: 'heatmap',
    name: 'Heatmap',
    icon: 'chart-heatmap',
    category: 'advanced',
    description: 'Visualize data density and patterns',
    defaultSize: { cols: 8, rows: 4 }
  }
];

