import React from 'react';

export default function Toggle({ checked, onChange, label, id, disabled = false }) {
  const toggleId = id || label?.toLowerCase().replace(/\s+/g, '-');

  return (
    <div className="flex items-center gap-sm">
      <button
        id={toggleId}
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        className={`toggle ${checked ? 'toggle-active' : ''}`}
        onClick={() => !disabled && onChange(!checked)}
        disabled={disabled}
      >
        <span className="toggle-knob" />
      </button>
      {label && (
        <label htmlFor={toggleId} className="text-body-sm cursor-pointer" onClick={() => !disabled && onChange(!checked)}>
          {label}
        </label>
      )}
    </div>
  );
}
