import React from 'react';

export default function Button({
  variant = 'primary',
  children,
  onClick,
  disabled = false,
  icon: Icon,
  fullWidth = false,
  loading = false,
  size,
  type = 'button',
  className = '',
  ...props
}) {
  const variantClass = `btn-${variant}`;
  const sizeClass = size === 'sm' ? 'btn-sm' : size === 'icon' ? 'btn-icon' : '';
  const widthClass = fullWidth ? 'btn-full-width' : '';

  return (
    <button
      type={type}
      className={`btn ${variantClass} ${sizeClass} ${widthClass} ${className}`.trim()}
      onClick={onClick}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <span className="btn-spinner" aria-label="Loading" />
      ) : (
        <>
          {Icon && <Icon size={size === 'sm' ? 16 : 18} />}
          {children}
        </>
      )}
    </button>
  );
}
