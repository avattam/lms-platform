import React from 'react';

export default function SaakarLogo({ width, height = 32, className = '', iconOnly = false, style = {} }) {
  if (iconOnly) {
    const squareWidth = width || height;
    return (
      <svg
        width={squareWidth}
        height={height}
        viewBox="0 0 120 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`saakar-logo ${className}`}
        style={{ display: 'inline-block', verticalAlign: 'middle', ...style }}
      >
        <text
          x="5"
          y="78"
          fill="#FF4D4D"
          style={{
            fontFamily: "system-ui, -apple-system, sans-serif",
            fontWeight: 800,
            fontSize: '82px',
            letterSpacing: '-2px'
          }}
        >
          SA
        </text>
      </svg>
    );
  }

  // Full Logo (horizontal layout)
  const fullWidth = width || (height * 3.2);
  return (
    <svg
      width={fullWidth}
      height={height}
      viewBox="0 0 320 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`saakar-logo ${className}`}
      style={{ display: 'inline-block', verticalAlign: 'middle', ...style }}
    >
      {/* "SA" Coral Red letters */}
      <text
        x="10"
        y="78"
        fill="#FF4D4D"
        style={{
          fontFamily: "system-ui, -apple-system, sans-serif",
          fontWeight: 800,
          fontSize: '82px',
          letterSpacing: '-2px'
        }}
      >
        SA
      </text>
      
      {/* "SAAKAR" */}
      <text
        x="135"
        y="42"
        fill="currentColor"
        style={{
          fontFamily: "system-ui, -apple-system, sans-serif",
          fontWeight: 700,
          fontSize: '32px',
          letterSpacing: '1px'
        }}
      >
        SAAKAR
      </text>
      
      {/* "ACADEMY" */}
      <text
        x="135"
        y="80"
        fill="currentColor"
        style={{
          fontFamily: "system-ui, -apple-system, sans-serif",
          fontWeight: 700,
          fontSize: '32px',
          letterSpacing: '1px'
        }}
      >
        ACADEMY
      </text>
    </svg>
  );
}
