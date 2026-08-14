import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Ozhzo Verse',
  description: 'Where Home Comes Together.',
  icons: {
    icon: [
      { url: '/favicon.ico' },
      { url: '/brand/favicon/ozhzo-favicon-32.png', sizes: '32x32', type: 'image/png' },
      { url: '/brand/icons/ozhzo-mark-primary.svg', type: 'image/svg+xml' },
    ],
    shortcut: '/favicon.ico',
    apple: [
      { url: '/apple-touch-icon.png', sizes: '180x180', type: 'image/png' },
    ],
  },
  manifest: '/manifest.json',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
