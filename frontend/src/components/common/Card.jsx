import React from 'react';

export default function Card({
  children,
  padding = 'md',
  bordered = false,
  hoverable = false,
  surface = false,
  className = '',
  onClick,
  ...props
}) {
  const paddingClass = padding !== 'md' ? `card-p-${padding}` : '';
  const borderedClass = bordered ? 'card-bordered' : '';
  const hoverableClass = hoverable ? 'card-hoverable' : '';
  const surfaceClass = surface ? 'card-surface' : '';
  const clickableStyle = onClick ? 'cursor-pointer' : '';

  return (
    <div
      className={`card ${paddingClass} ${borderedClass} ${hoverableClass} ${surfaceClass} ${clickableStyle} ${className}`.trim()}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => { if (e.key === 'Enter') onClick(e); } : undefined}
      {...props}
    >
      {children}
    </div>
  );
}
