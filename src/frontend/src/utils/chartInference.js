/**
 * Chart type inference engine.
 * Examines column metadata and data shape to determine the best visualization.
 */

/**
 * @param {Array<{name: string, type: string}>} columns
 * @param {Array<Object>} data
 * @returns {'bar' | 'line' | 'pie' | 'stat' | 'table'}
 */
export function inferChartType(columns, data) {
  if (!columns || !data || data.length === 0) return 'table';

  const dateColumns = columns.filter((c) =>
    ['date', 'datetime', 'timestamp', 'time'].includes(c.type?.toLowerCase()) ||
    c.name.toLowerCase().includes('date') ||
    c.name.toLowerCase().includes('time') ||
    c.name.toLowerCase().includes('created') ||
    c.name.toLowerCase().includes('updated')
  );

  const numericColumns = columns.filter((c) =>
    ['number', 'integer', 'float', 'decimal', 'numeric', 'bigint', 'int'].includes(c.type?.toLowerCase()) ||
    (data.length > 0 && typeof data[0][c.name] === 'number')
  );

  const categoricalColumns = columns.filter(
    (c) => !dateColumns.includes(c) && !numericColumns.includes(c)
  );

  // Single row → stat/KPI card
  if (data.length === 1 && numericColumns.length >= 1) {
    return 'stat';
  }

  // Date + numeric → line chart
  if (dateColumns.length >= 1 && numericColumns.length >= 1) {
    return 'line';
  }

  // 1 categorical + 1 numeric → bar chart
  if (categoricalColumns.length === 1 && numericColumns.length >= 1) {
    // Check if values sum to ~100 → pie
    if (numericColumns.length === 1 && data.length <= 8) {
      const sum = data.reduce((s, row) => s + (Number(row[numericColumns[0].name]) || 0), 0);
      if (sum >= 95 && sum <= 105) return 'pie';
    }
    return 'bar';
  }

  // Multiple numeric, no clear pattern → table
  return 'table';
}

export function getColumnTypes(columns, data) {
  return {
    date: columns.filter((c) =>
      ['date', 'datetime', 'timestamp'].includes(c.type?.toLowerCase()) ||
      c.name.toLowerCase().includes('date')
    ),
    numeric: columns.filter((c) =>
      ['number', 'integer', 'float', 'decimal', 'numeric'].includes(c.type?.toLowerCase()) ||
      (data.length > 0 && typeof data[0][c.name] === 'number')
    ),
    categorical: columns.filter((c) =>
      !['number', 'integer', 'float', 'decimal', 'numeric', 'date', 'datetime', 'timestamp'].includes(c.type?.toLowerCase())
    ),
  };
}
