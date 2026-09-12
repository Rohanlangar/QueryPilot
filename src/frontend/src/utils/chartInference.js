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

  const dateKeywords = ['date', 'datetime', 'timestamp', 'time', 'month', 'year', 'day', 'week', 'quarter', 'period', 'created', 'updated'];

  const dateColumns = columns.filter((c) => {
    const typeLower = c.type?.toLowerCase() || '';
    const nameLower = c.name?.toLowerCase() || '';
    return (
      ['date', 'datetime', 'timestamp', 'time'].includes(typeLower) ||
      dateKeywords.some((k) => nameLower.includes(k))
    );
  });

  const numericColumns = columns.filter((c) => {
    const typeLower = c.type?.toLowerCase() || '';
    if (['number', 'integer', 'float', 'decimal', 'numeric', 'bigint', 'int'].includes(typeLower)) {
      return true;
    }
    return data.some((row) => {
      const val = row?.[c.name];
      return val !== null && val !== undefined && val !== '' && !isNaN(Number(val)) && typeof val !== 'boolean';
    });
  });

  const categoricalColumns = columns.filter(
    (c) => !dateColumns.some((d) => d.name === c.name) && !numericColumns.some((n) => n.name === c.name)
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

  // If we have at least 1 numeric column and rows > 1, bar chart is a good visualization
  if (numericColumns.length >= 1 && data.length > 1) {
    return 'bar';
  }

  // Multiple numeric, no clear pattern → table
  return 'table';
}

export function getColumnTypes(columns, data) {
  if (!columns) return { date: [], numeric: [], categorical: [] };

  const dateKeywords = ['date', 'datetime', 'timestamp', 'time', 'month', 'year', 'day', 'week', 'quarter', 'period', 'created', 'updated'];

  const date = columns.filter((c) => {
    const typeLower = c.type?.toLowerCase() || '';
    const nameLower = c.name?.toLowerCase() || '';
    return (
      ['date', 'datetime', 'timestamp', 'time'].includes(typeLower) ||
      dateKeywords.some((k) => nameLower.includes(k))
    );
  });

  const numeric = columns.filter((c) => {
    const typeLower = c.type?.toLowerCase() || '';
    if (['number', 'integer', 'float', 'decimal', 'numeric', 'bigint', 'int'].includes(typeLower)) {
      return true;
    }
    return data && data.some((row) => {
      const val = row?.[c.name];
      return val !== null && val !== undefined && val !== '' && !isNaN(Number(val)) && typeof val !== 'boolean';
    });
  });

  const categorical = columns.filter(
    (c) => !date.some((d) => d.name === c.name) && !numeric.some((n) => n.name === c.name)
  );

  return { date, numeric, categorical };
}
