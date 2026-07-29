import React from 'react';
import SaakarLogo from './SaakarLogo';

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="app-footer">
      <div className="footer-content">
        <div className="footer-brand">
          <SaakarLogo height={20} />
          <span style={{ opacity: 0.4, margin: '0 0.4rem', fontWeight: 300 }}>|</span>
          <span className="footer-title">LMS Platform</span>
        </div>
        <div className="footer-copyright">
          © {currentYear} <strong>Saakar Academy</strong>. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
