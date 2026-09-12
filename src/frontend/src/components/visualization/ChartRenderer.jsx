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
  const initialType = (overrideType && overrideType !== 'table') 
    ? overrideType 
    : (inferred !== 'table' ? inferred : 'bar');
  const [activeType, setActiveType] = useState(initialType);

  const colTypes = React.useMemo(() => getColumnTypes(columns, data), [columns, data]);

  // Clean numeric data for Recharts (e.g. string numbers to Number)
  const chartData = React.useMemo(() => {
    if (!data) return [];
    return data.map((row) => {
      const formatted = { ...row };
      colTypes.numeric.forEach((col) => {
        const val = row[col.name];
        if (val !== null && val !== undefined && !isNaN(Number(val))) {
          formatted[col.name] = Number(val);
        }
      });
      return formatted;
    });
  }, [data, colTypes.numeric]);

  const renderChart = () => {
    const xKey = colTypes.date[0]?.name || colTypes.categorical[0]?.name || columns[0]?.name;
    const valKeys = colTypes.numeric.map((c) => c.name);
    // If no explicit numeric columns detected, fallback to the second column
    const effectiveValKeys = valKeys.length > 0 ? valKeys : (columns[1] ? [columns[1].name] : []);

    switch (activeType) {
      case 'bar':
        return (
          <BarChartView
            data={chartData}
            categoryKey={colTypes.categorical[0]?.name || colTypes.date[0]?.name || columns[0]?.name}
            valueKeys={effectiveValKeys}
          />
        );
      case 'line':
        return (
          <LineChartView
            data={chartData}
            xKey={xKey}
            valueKeys={effectiveValKeys}
          />
        );
      case 'pie':
        return (
          <PieChartView
            data={chartData}
            nameKey={colTypes.categorical[0]?.name || colTypes.date[0]?.name || columns[0]?.name}
            valueKey={effectiveValKeys[0]}
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
