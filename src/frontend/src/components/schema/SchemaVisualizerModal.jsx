import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import {
  Database, X, Search, ZoomIn, ZoomOut, Maximize2, Minimize2,
  RotateCcw, Key, Link2, Circle, Eye, EyeOff, LayoutGrid, Download,
  Layers, Move
} from 'lucide-react';
import { getConnectionERD } from '../../api/connectionsApi';
import '../../styles/schema-visualizer.css';

const CARD_WIDTH = 270;
const ROW_HEIGHT = 26;
const HEADER_HEIGHT = 38;
const FOOTER_HEIGHT = 26;

// Predefined smart layout positions (column & row flow)
function computeInitialPositions(tables) {
  const positions = {};
  const COLS = 4;
  const SPACING_X = 330;
  const SPACING_Y = 320;
  const START_X = 60;
  const START_Y = 60;

  // Topological sorting priority: tables with no FKs first (root), then dependents
  const sorted = [...tables].sort((a, b) => {
    const aFkCount = a.foreign_keys?.length || 0;
    const bFkCount = b.foreign_keys?.length || 0;
    return aFkCount - bFkCount;
  });

  sorted.forEach((table, index) => {
    const col = index % COLS;
    const row = Math.floor(index / COLS);
    positions[table.name] = {
      x: START_X + col * SPACING_X,
      y: START_Y + row * SPACING_Y,
    };
  });

  return positions;
}

export default function SchemaVisualizerModal({ isOpen, onClose, connection }) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [tablePositions, setTablePositions] = useState({});
  const [collapsedTables, setCollapsedTables] = useState({});
  const [hiddenTables, setHiddenTables] = useState({});
  const [searchTerm, setSearchTerm] = useState('');
  const [zoom, setZoom] = useState(0.85);
  const [pan, setPan] = useState({ x: 40, y: 30 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [fullscreen, setFullscreen] = useState(false);
  const [hoveredTable, setHoveredTable] = useState(null);
  const [hoveredEdge, setHoveredEdge] = useState(null);

  // Dragging single table state
  const [draggedTable, setDraggedTable] = useState(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });

  const viewportRef = useRef(null);

  // Fetch ERD data on mount or connection change
  useEffect(() => {
    if (!isOpen || !connection?.id) return;

    let mounted = true;
    setLoading(true);

    getConnectionERD(connection.id)
      .then((res) => {
        if (!mounted) return;
        setData(res);
        if (res.tables && res.tables.length > 0) {
          setTablePositions(computeInitialPositions(res.tables));
        }
      })
      .catch((err) => {
        console.warn('Could not fetch live ERD, loading sample:', err);
        // Fallback sample will be returned by backend endpoint anyway
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [isOpen, connection?.id]);

  // Handle Canvas Pan (Mouse drag on background)
  const handleMouseDown = (e) => {
    if (e.target.closest('.schema-table-card') || e.target.closest('.schema-visualizer-header')) return;
    setIsPanning(true);
    setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e) => {
    if (isPanning) {
      setPan({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y,
      });
    } else if (draggedTable) {
      // Dragging a table card
      setTablePositions((prev) => ({
        ...prev,
        [draggedTable]: {
          x: Math.max(0, (e.clientX - dragOffset.x - pan.x) / zoom),
          y: Math.max(0, (e.clientY - dragOffset.y - pan.y) / zoom),
        },
      }));
    }
  };

  const handleMouseUp = () => {
    setIsPanning(false);
    setDraggedTable(null);
  };

  // Wheel Zoom
  const handleWheel = (e) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.08 : 0.92;
    setZoom((prevZoom) => Math.min(Math.max(prevZoom * zoomFactor, 0.35), 2.0));
  };

  // Start dragging a table
  const handleTableDragStart = (e, tableName) => {
    e.stopPropagation();
    const currentPos = tablePositions[tableName] || { x: 0, y: 0 };
    setDraggedTable(tableName);
    setDragOffset({
      x: e.clientX - (currentPos.x * zoom + pan.x),
      y: e.clientY - (currentPos.y * zoom + pan.y),
    });
  };

  // Fit to screen
  const handleFitView = useCallback(() => {
    if (!data?.tables || data.tables.length === 0) return;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

    data.tables.forEach((t) => {
      const pos = tablePositions[t.name] || { x: 0, y: 0 };
      minX = Math.min(minX, pos.x);
      minY = Math.min(minY, pos.y);
      maxX = Math.max(maxX, pos.x + CARD_WIDTH);
      maxY = Math.max(maxY, pos.y + 300);
    });

    if (minX !== Infinity && viewportRef.current) {
      const vWidth = viewportRef.current.clientWidth || 1000;
      const vHeight = viewportRef.current.clientHeight || 700;
      const bWidth = maxX - minX + 100;
      const bHeight = maxY - minY + 100;
      const scaleX = vWidth / bWidth;
      const scaleY = vHeight / bHeight;
      const newZoom = Math.min(Math.max(Math.min(scaleX, scaleY), 0.4), 1.1);

      setZoom(newZoom);
      setPan({
        x: Math.max(20, (vWidth - bWidth * newZoom) / 2),
        y: Math.max(20, (vHeight - bHeight * newZoom) / 2),
      });
    }
  }, [data?.tables, tablePositions]);

  // Auto-align tables in nice grid
  const handleAutoAlign = () => {
    if (data?.tables) {
      setTablePositions(computeInitialPositions(data.tables));
      setTimeout(handleFitView, 50);
    }
  };

  // Toggle table collapsed
  const toggleCollapse = (tableName) => {
    setCollapsedTables((prev) => ({
      ...prev,
      [tableName]: !prev[tableName],
    }));
  };

  // Calculate SVG lines connecting foreign keys to primary keys
  const renderedEdges = useMemo(() => {
    if (!data?.relationships || !data?.tables) return [];

    return data.relationships
      .map((rel) => {
        const fromPos = tablePositions[rel.from_table];
        const toPos = tablePositions[rel.to_table];

        if (!fromPos || !toPos || hiddenTables[rel.from_table] || hiddenTables[rel.to_table]) {
          return null;
        }

        const fromTable = data.tables.find((t) => t.name === rel.from_table);
        const toTable = data.tables.find((t) => t.name === rel.to_table);

        const fromColIdx = fromTable?.columns?.findIndex((c) => c.name === rel.from_column) ?? 0;
        const toColIdx = toTable?.columns?.findIndex((c) => c.name === rel.to_column) ?? 0;

        const isFromCollapsed = collapsedTables[rel.from_table];
        const isToCollapsed = collapsedTables[rel.to_table];

        const fromY = isFromCollapsed
          ? fromPos.y + HEADER_HEIGHT / 2
          : fromPos.y + HEADER_HEIGHT + fromColIdx * ROW_HEIGHT + ROW_HEIGHT / 2;

        const toY = isToCollapsed
          ? toPos.y + HEADER_HEIGHT / 2
          : toPos.y + HEADER_HEIGHT + toColIdx * ROW_HEIGHT + ROW_HEIGHT / 2;

        let startX, endX;
        if (fromPos.x < toPos.x) {
          startX = fromPos.x + CARD_WIDTH;
          endX = toPos.x;
        } else {
          startX = fromPos.x;
          endX = toPos.x + CARD_WIDTH;
        }

        // Orthogonal or S-curve bezier path
        const midX = (startX + endX) / 2;
        const path = `M ${startX} ${fromY} C ${midX} ${fromY}, ${midX} ${toY}, ${endX} ${toY}`;

        const isHighlighted =
          hoveredEdge === rel.id ||
          hoveredTable === rel.from_table ||
          hoveredTable === rel.to_table;

        return {
          id: rel.id,
          path,
          fromTable: rel.from_table,
          toTable: rel.to_table,
          fromColumn: rel.from_column,
          toColumn: rel.to_column,
          isHighlighted,
        };
      })
      .filter(Boolean);
  }, [data?.relationships, data?.tables, tablePositions, collapsedTables, hiddenTables, hoveredEdge, hoveredTable]);

  if (!isOpen) return null;

  const filteredTables = (data?.tables || []).filter((t) =>
    !searchTerm || t.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="schema-modal-overlay" onClick={onClose}>
      <div
        className={`schema-visualizer-container ${fullscreen ? 'fullscreen' : ''}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Toolbar */}
        <div className="schema-visualizer-header">
          <div className="schema-header-left">
            <div className="schema-db-icon">
              <Database size={20} />
            </div>
            <div className="schema-title-wrap">
              <div className="schema-db-name">
                {connection?.database || data?.database_name || 'Database Schema'}
                <span className="schema-db-badge">{connection?.dbType || data?.db_type || 'PostgreSQL'}</span>
                {data?.is_sample && (
                  <span className="schema-db-badge" style={{ backgroundColor: 'rgba(234, 179, 8, 0.2)', color: '#eab308', borderColor: 'rgba(234, 179, 8, 0.4)' }}>
                    DEMO ERD
                  </span>
                )}
              </div>
              <span className="schema-db-stats">
                {data?.tables?.length || 0} tables • {data?.relationships?.length || 0} relationships
              </span>
            </div>
          </div>

          <div className="schema-header-center">
            <div className="schema-search-bar">
              <Search size={15} className="schema-search-icon" />
              <input
                type="text"
                className="schema-search-input"
                placeholder="Filter tables (e.g. users, rooms, auth)..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>

          <div className="schema-header-right">
            <button className="schema-btn" onClick={handleAutoAlign} title="Auto-align table layout">
              <LayoutGrid size={15} />
              <span>Align</span>
            </button>
            <button className="schema-btn" onClick={handleFitView} title="Fit all tables to screen">
              <Maximize2 size={15} />
              <span>Fit View</span>
            </button>
            <button
              className="schema-btn schema-btn-icon-only"
              onClick={() => setZoom((z) => Math.max(z - 0.15, 0.35))}
              title="Zoom Out"
            >
              <ZoomOut size={16} />
            </button>
            <span className="schema-zoom-indicator">{Math.round(zoom * 100)}%</span>
            <button
              className="schema-btn schema-btn-icon-only"
              onClick={() => setZoom((z) => Math.min(z + 0.15, 2.0))}
              title="Zoom In"
            >
              <ZoomIn size={16} />
            </button>
            <button
              className="schema-btn schema-btn-icon-only"
              onClick={() => { setZoom(1); setPan({ x: 50, y: 50 }); }}
              title="Reset Zoom"
            >
              <RotateCcw size={15} />
            </button>
            <button
              className="schema-btn schema-btn-icon-only"
              onClick={() => setFullscreen((prev) => !prev)}
              title="Toggle Fullscreen"
            >
              {fullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
            </button>
            <button
              className="schema-btn schema-btn-icon-only"
              onClick={onClose}
              title="Close Visualizer"
              style={{ backgroundColor: 'rgba(239, 68, 68, 0.15)', borderColor: 'rgba(239, 68, 68, 0.3)', color: '#f87171' }}
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Viewport & Canvas */}
        <div
          ref={viewportRef}
          className={`schema-canvas-viewport ${isPanning ? 'panning' : ''}`}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onWheel={handleWheel}
        >
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '12px' }}>
              <div style={{ width: '36px', height: '36px', border: '3px solid #333c52', borderTopColor: '#10b981', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
              <span style={{ fontSize: '14px', color: '#94a3b8' }}>Introspecting database schema & relationships...</span>
            </div>
          ) : (
            <div
              className="schema-canvas-plane"
              style={{
                transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              }}
            >
              {/* SVG Edge Connectors */}
              <svg className="schema-svg-overlay">
                <defs>
                  <marker
                    id="erd-arrow"
                    viewBox="0 0 10 10"
                    refX="7"
                    refY="5"
                    markerWidth="6"
                    markerHeight="6"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 1 L 9 5 L 0 9 z" fill="#475569" />
                  </marker>
                  <marker
                    id="erd-arrow-highlight"
                    viewBox="0 0 10 10"
                    refX="7"
                    refY="5"
                    markerWidth="7"
                    markerHeight="7"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 1 L 9 5 L 0 9 z" fill="#10b981" />
                  </marker>
                </defs>

                {renderedEdges.map((edge) => (
                  <path
                    key={edge.id}
                    d={edge.path}
                    className={`schema-edge-line ${edge.isHighlighted ? 'highlighted' : ''} ${
                      hoveredTable && !edge.isHighlighted ? 'dimmed' : ''
                    }`}
                    markerEnd={edge.isHighlighted ? 'url(#erd-arrow-highlight)' : 'url(#erd-arrow)'}
                    onMouseEnter={() => setHoveredEdge(edge.id)}
                    onMouseLeave={() => setHoveredEdge(null)}
                  />
                ))}
              </svg>

              {/* Table Cards */}
              {filteredTables.map((table) => {
                const pos = tablePositions[table.name] || { x: 50, y: 50 };
                const isCollapsed = collapsedTables[table.name];
                const isConnected =
                  hoveredTable &&
                  (renderedEdges.some(
                    (e) => (e.fromTable === hoveredTable && e.toTable === table.name) ||
                           (e.toTable === hoveredTable && e.fromTable === table.name)
                  ) || hoveredTable === table.name);

                return (
                  <div
                    key={table.name}
                    className={`schema-table-card ${
                      hoveredTable === table.name ? 'connected-highlight' : isConnected ? 'connected-highlight' : ''
                    } ${hoveredTable && !isConnected ? 'dimmed' : ''}`}
                    style={{
                      transform: `translate(${pos.x}px, ${pos.y}px)`,
                    }}
                    onMouseEnter={() => setHoveredTable(table.name)}
                    onMouseLeave={() => setHoveredTable(null)}
                  >
                    {/* Header */}
                    <div
                      className="schema-table-header"
                      onMouseDown={(e) => handleTableDragStart(e, table.name)}
                    >
                      <div className="schema-table-title-area">
                        <span className="schema-table-schema-badge">{table.schema || 'public'}</span>
                        <span className="schema-table-name" title={table.name}>
                          {table.name}
                        </span>
                      </div>
                      <div className="schema-table-header-actions">
                        <button
                          className="schema-table-eye-btn"
                          onClick={() => toggleCollapse(table.name)}
                          title={isCollapsed ? 'Expand columns' : 'Collapse columns'}
                        >
                          {isCollapsed ? <EyeOff size={14} /> : <Eye size={14} />}
                        </button>
                      </div>
                    </div>

                    {/* Columns List */}
                    {!isCollapsed && (
                      <div className="schema-table-columns">
                        {table.columns?.map((col) => (
                          <div
                            key={col.name}
                            className={`schema-col-row ${col.is_primary_key ? 'pk' : ''} ${
                              col.is_foreign_key ? 'fk' : ''
                            }`}
                            title={`${col.name} (${col.type})${col.is_primary_key ? ' [Primary Key]' : ''}${col.is_foreign_key ? ' [Foreign Key]' : ''}`}
                          >
                            <div className="schema-col-left">
                              {col.is_primary_key ? (
                                <span className="schema-col-icon pk">
                                  <Key size={12} />
                                </span>
                              ) : col.is_foreign_key ? (
                                <span className="schema-col-icon fk">
                                  <Link2 size={12} />
                                </span>
                              ) : (
                                <span className="schema-col-icon normal">
                                  <Circle size={6} fill="currentColor" />
                                </span>
                              )}
                              <span className="schema-col-name">{col.name}</span>
                            </div>
                            <span className="schema-col-type">{col.type}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Footer */}
                    <div className="schema-table-footer">
                      <span>{table.columns?.length || 0} columns</span>
                      {table.row_count != null && (
                        <span>~{Number(table.row_count).toLocaleString()} rows</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Floating Canvas Legend */}
          <div className="schema-canvas-legend">
            <div className="schema-legend-item">
              <span className="schema-legend-dot pk" />
              <span>Primary Key</span>
            </div>
            <div className="schema-legend-item">
              <span className="schema-legend-dot fk" />
              <span>Foreign Key</span>
            </div>
            <div className="schema-legend-item">
              <span className="schema-legend-dot relation" />
              <span>Relationship</span>
            </div>
          </div>

          {/* Instructions Floating Pill */}
          <div className="schema-instructions-pill">
            <Move size={12} />
            <span>Drag table header to move • Drag canvas to pan • Scroll to zoom</span>
          </div>
        </div>
      </div>
    </div>
  );
}
