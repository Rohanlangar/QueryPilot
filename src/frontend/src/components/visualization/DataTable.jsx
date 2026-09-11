import React, { useState, useMemo } from 'react';
import { ArrowUp, ArrowDown, Download, Lock } from 'lucide-react';
import Button from '../common/Button';

export default function DataTable({ data, columns, pageSize = 25 }) {
  const [sortKey, setSortKey] = useState(null);
  const [sortDir, setSortDir] = useState('asc');
  const [page, setPage] = useState(0);

  const handleSort = (colName) => {
    if (sortKey === colName) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(colName);
      setSortDir('asc');
    }
    setPage(0);
  };

  const sortedData = useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
      }
      const cmp = String(aVal).localeCompare(String(bVal));
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir]);

  const totalPages = Math.ceil(sortedData.length / pageSize);
  const pagedData = sortedData.slice(page * pageSize, (page + 1) * pageSize);
  const startRow = page * pageSize + 1;
  const endRow = Math.min((page + 1) * pageSize, sortedData.length);

  const handleExportCSV = () => {
    const header = columns.map((c) => c.name).join(',');
    const rows = data.map((row) =>
      columns.map((c) => {
        const val = row[c.name];
        return typeof val === 'string' && val.includes(',') ? `"${val}"` : val;
      }).join(',')
    );
    const csv = [header, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'query-results.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!data || data.length === 0) {
    return (
      <div style={{ padding: '32px', textAlign: 'center', color: 'var(--color-muted)' }}>
        No results found.
      </div>
    );
  }

  return (
    <div>
      <div className="data-table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th
                  key={col.name}
                  onClick={() => handleSort(col.name)}
                  className={sortKey === col.name ? 'sorted' : ''}
                >
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    {col.isPII && <Lock size={11} style={{ color: 'var(--color-error)' }} />}
                    {col.name}
                    <span className="sort-icon">
                      {sortKey === col.name ? (
                        sortDir === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />
                      ) : (
                        <ArrowUp size={12} />
                      )}
                    </span>
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pagedData.map((row, rowIdx) => (
              <tr key={rowIdx}>
                {columns.map((col) => (
                  <td key={col.name} className={col.isPII ? 'data-table-pii' : ''}>
                    {col.isPII ? maskValue(row[col.name]) : formatCellValue(row[col.name])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="data-table-footer">
        <span>
          Showing {startRow}–{endRow} of {sortedData.length} results
        </span>
        <div className="data-table-pagination">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
          >
            Previous
          </Button>
          <span className="text-label-sm">
            Page {page + 1} of {totalPages}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
          >
            Next
          </Button>
          <Button
            variant="ghost"
            size="sm"
            icon={Download}
            onClick={handleExportCSV}
          >
            CSV
          </Button>
        </div>
      </div>
    </div>
  );
}

function formatCellValue(val) {
  if (val === null || val === undefined) return '—';
  if (typeof val === 'number') return val.toLocaleString();
  return String(val);
}

function maskValue(val) {
  if (!val) return '—';
  const s = String(val);
  if (s.includes('@')) {
    const [name, domain] = s.split('@');
    return `${name.slice(0, 2)}***@${domain}`;
  }
  if (s.length > 4) {
    return `${s.slice(0, 2)}${'*'.repeat(s.length - 4)}${s.slice(-2)}`;
  }
  return '***';
}
