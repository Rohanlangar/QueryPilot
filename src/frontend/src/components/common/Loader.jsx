import React from 'react';

export function Loader({ size = 'md' }) {
  const dotSize = size === 'sm' ? '6px' : size === 'lg' ? '10px' : '8px';

  return (
    <div className="loader" role="status" aria-label="Loading">
      <span className="loader-dot" style={{ width: dotSize, height: dotSize }} />
      <span className="loader-dot" style={{ width: dotSize, height: dotSize }} />
      <span className="loader-dot" style={{ width: dotSize, height: dotSize }} />
    </div>
  );
}

export function FullPageLoader() {
  return (
    <div className="loader-fullpage">
      <Loader size="lg" />
    </div>
  );
}

export default Loader;
