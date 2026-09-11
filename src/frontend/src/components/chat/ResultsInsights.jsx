import React, { useState, useMemo } from 'react';
import { Table, BarChart2, TrendingUp, Hash, Clock, Layers, Sparkles } from 'lucide-react';
import DataTable from '../visualization/DataTable';
import ChartRenderer from '../visualization/ChartRenderer';
import Button from '../common/Button';

export default function ResultsInsights({
  results,
  executionTimeMs,
  rowCount,
  chartSuggestion,
}) {
  const [viewMode, setViewMode] = useState('table'); // 'table' | 'chart'

  const data = results?.data || [];
  const columns = results?.columns || [];
  const actualRowCount = rowCount != null ? rowCount : data.length;

  // Auto-generate statistical summary insights from the data
  const insights = useMemo(() => {
    if (!data || data.length === 0 || !columns || columns.length === 0) {
      return [];
    }

    const takeaways = [];
    const numRows = data.length;

    // Detect numeric, categorical, and date columns
    const numericCols = [];
    const textCols = [];

    columns.forEach((col) => {
      const colName = col.name;
      let hasNumeric = false;
      let hasString = false;

      for (let i = 0; i < Math.min(20, numRows); i++) {
        const val = data[i]?.[colName];
        if (val !== null && val !== undefined && val !== '') {
          if (typeof val === 'number' || (!isNaN(Number(val)) && typeof val !== 'boolean')) {
            hasNumeric = true;
          } else {
            hasString = true;
          }
        }
      }

      if (hasNumeric && !hasString && !colName.toLowerCase().includes('id')) {
        numericCols.push(colName);
      } else if (hasString || colName.toLowerCase().includes('name') || colName.toLowerCase().includes('status') || colName.toLowerCase().includes('type') || colName.toLowerCase().includes('category')) {
        textCols.push(colName);
      }
    });

    // Generate insights for top numeric columns (up to 3)
    numericCols.slice(0, 3).forEach((colName) => {
      const values = data
        .map((row) => Number(row[colName]))
        .filter((val) => !isNaN(val) && val !== null);

      if (values.length > 0) {
        const min = Math.min(...values);
        const max = Math.max(...values);
        const sum = values.reduce((acc, v) => acc + v, 0);
        const avg = sum / values.length;

        takeaways.push({
          type: 'metric',
          label: colName,
          detail: `Average: ${formatNumber(avg)} • Min: ${formatNumber(min)} • Max: ${formatNumber(max)} • Total: ${formatNumber(sum)}`,
        });
      }
    });

    // Generate insights for categorical columns (up to 2)
    textCols.slice(0, 2).forEach((colName) => {
      const counts = {};
      data.forEach((row) => {
        const val = row[colName];
        if (val !== null && val !== undefined) {
          const str = String(val);
          counts[str] = (counts[str] || 0) + 1;
        }
      });

      const uniqueCount = Object.keys(counts).length;
      const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
      if (sorted.length > 0) {
        const topItem = sorted[0];
        takeaways.push({
          type: 'category',
          label: colName,
          detail: `${uniqueCount} distinct values. Most frequent: "${topItem[0]}" (${topItem[1]} occurrences, ${Math.round((topItem[1] / numRows) * 100)}%)`,
        });
      }
    });

    return takeaways;
  }, [data, columns]);

  const hasChart = chartSuggestion && chartSuggestion.chart_type && chartSuggestion.chart_type !== 'table';

  return (
    <div className="results-insights-container">
      {/* Header bar with stats & view switcher */}
      <div className="results-insights-header">
        <div className="results-stats-bar">
          <div className="results-stat-item">
            <Hash size={14} className="results-stat-icon" />
            <span className="results-stat-val">{actualRowCount.toLocaleString()}</span>
            <span className="results-stat-label">rows</span>
          </div>

          <div className="results-stat-item">
            <Layers size={14} className="results-stat-icon" />
            <span className="results-stat-val">{columns.length}</span>
            <span className="results-stat-label">columns</span>
          </div>

          {executionTimeMs != null && executionTimeMs > 0 && (
            <div className="results-stat-item">
              <Clock size={14} className="results-stat-icon" />
              <span className="results-stat-val">{Math.round(executionTimeMs)}ms</span>
              <span className="results-stat-label">exec time</span>
            </div>
          )}
        </div>

        {hasChart && (
          <div className="results-view-tabs">
            <Button
              variant={viewMode === 'table' ? 'secondary' : 'ghost'}
              size="sm"
              icon={Table}
              onClick={() => setViewMode('table')}
            >
              Table
            </Button>
            <Button
              variant={viewMode === 'chart' ? 'secondary' : 'ghost'}
              size="sm"
              icon={BarChart2}
              onClick={() => setViewMode('chart')}
            >
              Chart
            </Button>
          </div>
        )}
      </div>

      {/* Auto-generated Summary Insights Card */}
      {insights.length > 0 && (
        <div className="results-insights-card">
          <div className="results-insights-card-title">
            <Sparkles size={14} className="insights-sparkle-icon" />
            <span>Key Data Insights</span>
          </div>
          <div className="results-insights-list">
            {insights.map((item, idx) => (
              <div key={idx} className="results-insight-row">
                <span className="insight-badge">{item.label}</span>
                <span className="insight-text">{item.detail}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* View Content */}
      <div className="results-content-wrapper">
        {viewMode === 'chart' && hasChart ? (
          <div className="results-chart-box">
            <ChartRenderer data={data} columns={columns} />
          </div>
        ) : (
          <div className="results-table-scroll-container">
            <DataTable data={data} columns={columns} />
          </div>
        )}
      </div>
    </div>
  );
}

function formatNumber(val) {
  if (val == null || isNaN(val)) return '—';
  if (Math.abs(val) >= 1_000_000) {
    return (val / 1_000_000).toFixed(2) + 'M';
  }
  if (Math.abs(val) >= 1_000) {
    return (val / 1_000).toFixed(1) + 'k';
  }
  if (Number.isInteger(val)) {
    return val.toLocaleString();
  }
  return val.toFixed(2);
}
