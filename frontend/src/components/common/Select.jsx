import React from 'react';

export default function Select({
  label,
  value,
  onChange,
  options = [],
  placeholder,
  error,
  disabled = false,
  id,
  name,
  required = false,
  className = '',
}) {
  const selectId = id || name || label?.toLowerCase().replace(/\s+/g, '-');

  return (
    <div className={`input-group ${className}`}>
      {label && (
        <label htmlFor={selectId} className="input-label">
          {label}
          {required && <span style={{ color: 'var(--color-error)', marginLeft: '4px' }}>*</span>}
        </label>
      )}
      <select
        id={selectId}
        name={name}
        value={value}
        onChange={onChange}
        disabled={disabled}
        required={required}
        className={`select-field ${error ? 'input-field-error' : ''}`}
        aria-invalid={!!error}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && (
        <span className="input-error-text" role="alert">{error}</span>
      )}
    </div>
  );
}
