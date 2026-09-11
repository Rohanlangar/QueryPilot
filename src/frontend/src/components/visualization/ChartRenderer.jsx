import React, { useState } from 'react';
import { BarChart3, LineChart as LineIcon, PieChart as PieIcon, Table } from 'lucide-react';
import { inferChartType, getColumnTypes } from '../../utils/chartInference';
import BarChartView from './BarChartView';
import LineChartView from './LineChartView';
import PieChartView from './PieChartView';
import DataTable from './DataTable';

const CHART_TYPES = [
  { key: 'bar', icon: BarChart3, label: 'Bar' },
  { key: 'line', icon: LineIcon, label: 'Line' },
  { key: 'pie', icon: PieIcon, label: 'Pie' },
  { key: 'table', icon: Table, label: 'Table' },
];

export default function ChartRenderer({ data, columns, overrideType = null }) {
  const inferred = inferChartType(columns, data);
  const [activeType, setActiveType] = useState(overrideType || inferred);

  const renderChart = () => {
    const colTypes = getColumnTypes(columns, data);

    switch (activeType) {
      case 'bar':
        return (
          <BarChartView
            data={data}
            categoryKey={colTypes.categorical[0]?.name || columns[0]?.name}
            valueKeys={colTypes.numeric.map((c) => c.name)}
          />
        );
      case 'line':
        return (
          <LineChartView
            data={data}
            xKey={colTypes.date[0]?.name || colTypes.categorical[0]?.name || columns[0]?.name}
            valueKeys={colTypes.numeric.map((c) => c.name)}
          />
        );
      case 'pie':
        return (
          <PieChartView
            data={data}
            nameKey={colTypes.categorical[0]?.name || columns[0]?.name}
            valueKey={colTypes.numeric[0]?.name || columns[1]?.name}
          />
        );
      case 'stat':
      case 'table':
      default:
        return <DataTable data={data} columns={columns} />;
    }
  };

  return (
    <div className="chart-wrapper">
      <div className="chart-header">
        <span className="text-label-sm text-muted">
          {activeType === inferred ? `Auto-detected: ${activeType}` : activeType} chart
        </span>
        <div className="chart-type-picker">
          {CHART_TYPES.map(({ key, icon: Icon, label }) => (
            <button
              key={key}
              className={`chart-type-btn ${activeType === key ? 'active' : ''}`}
              onClick={() => setActiveType(key)}
              aria-label={`Switch to ${label} view`}
              title={label}
            >
              <Icon size={16} />
            </button>
          ))}
        </div>
      </div>
      {renderChart()}
    </div>
  );
}
