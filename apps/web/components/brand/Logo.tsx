import React from 'react';
import Image from 'next/image';
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
  theme = 'light',
  height,
  width,
  className = '',
  href = '/',
  alt = 'Ozhzo Verse — Where Home Comes Together.'
}) => {
  let src = '/brand/logo/ozhzo-verse-logo-primary.svg';
  let defaultWidth = 180;
  let defaultHeight = 45;

  if (variant === 'full') {
    src = theme === 'dark' 
      ? '/brand/logo/ozhzo-verse-logo-primary-dark.svg' 
      : '/brand/logo/ozhzo-verse-logo-primary.svg';
    defaultWidth = 180;
    defaultHeight = 45;
  } else if (variant === 'mark' || variant === 'compact') {
    src = theme === 'dark' 
      ? '/brand/icons/ozhzo-mark-dark.svg' 
      : '/brand/icons/ozhzo-mark-primary.svg';
    defaultWidth = 36;
    defaultHeight = 36;
  }

  const finalWidth = width || defaultWidth;
  const finalHeight = height || defaultHeight;

  const content = (
    <div 
      className={`ozhzo-brand-logo ${className}`}
      style={{ display: 'inline-flex', alignItems: 'center', lineHeight: 0 }}
    >
      <img
        src={src}
        alt={alt}
        width={finalWidth}
        height={finalHeight}
        style={{
          display: 'block',
          height: `${finalHeight}px`,
          width: finalWidth ? `${finalWidth}px` : 'auto',
          objectFit: 'contain'
        }}
      />
    </div>
  );

  if (href) {
    return (
      <Link href={href} style={{ textDecoration: 'none', display: 'inline-flex' }}>
        {content}
      </Link>
    );
  }

  return content;
};
