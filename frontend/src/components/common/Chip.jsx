import React from 'react';

export default function Chip({
  children,
  variant = 'default',
  icon: Icon,
  onClick,
  className = '',
  ...props
}) {
  const variantClass = variant !== 'default' ? `chip-${variant}` : '';
  const clickableClass = onClick ? 'chip-clickable' : '';

  return (
    <span
      className={`chip ${variantClass} ${clickableClass} ${className}`.trim()}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => { if (e.key === 'Enter') onClick(e); } : undefined}
      {...props}
    >
      {Icon && <Icon size={12} />}
      {children}
    </span>
  );
}
