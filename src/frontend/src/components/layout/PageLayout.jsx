import React from 'react';

export default function PageLayout({ children, withSidebar = false, className = '' }) {
  return (
    <main
      className={`page-layout ${withSidebar ? 'page-layout-with-sidebar' : ''} ${className}`.trim()}
    >
      {children}
    </main>
  );
}
