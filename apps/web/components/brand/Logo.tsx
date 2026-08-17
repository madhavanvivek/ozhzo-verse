'use client';

import React from 'react';
import Link from 'next/link';

export interface LogoProps {
  variant?: 'full' | 'mark' | 'compact';
  theme?: 'light' | 'dark' | 'auto';
  height?: number;
  width?: number;
  className?: string;
  href?: string;
  alt?: string;
}

export const Logo: React.FC<LogoProps> = ({
  variant = 'full',
  height,
  width,
  className = '',
  href = '/',
  alt = 'Ozhzo Verse — Where Home Comes Together.'
}) => {
  const isFull = variant === 'full';

  const src = isFull
    ? '/images/ozhzo-logo.png'
    : '/brand/favicon/ozhzo-primary-favicon.svg';

  const defaultWidth = isFull ? 180 : 36;
  const defaultHeight = isFull ? 48 : 36;

  const finalWidth = width ?? defaultWidth;
  const finalHeight = height ?? defaultHeight;

  const content = (
    <div
      className={`ozhzo-brand-logo ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        lineHeight: 0
      }}
    >
      <img
        src={src}
        alt={alt}
        width={finalWidth}
        height={finalHeight}
        style={{
          display: 'block',
          width: `${finalWidth}px`,
          height: `${finalHeight}px`,
          objectFit: 'contain'
        }}
      />
    </div>
  );

  if (!href) {
    return content;
  }

  return (
    <Link
      href={href}
      className="ozhzo-brand-link"
      style={{
        display: 'inline-flex',
        textDecoration: 'none'
      }}
    >
      {content}
    </Link>
  );
};
