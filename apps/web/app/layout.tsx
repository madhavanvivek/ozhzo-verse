import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Ozhzo Verse',
  description: 'Where Home Comes Together.',
  icons: {
    icon: [
      {
        url: '/brand/favicon/favicon.ico'
      },
      {
        url: '/brand/favicon/ozhzo-favicon-32.png',
        sizes: '32x32',
        type: 'image/png'
      },
      {
        url: '/brand/favicon/ozhzo-verse-favicon.svg',
        type: 'image/svg+xml'
      }
    ],
    shortcut: '/brand/favicon/favicon.ico',
    apple: [
      {
        url: '/brand/icons/apple-touch-icon.png',
        sizes: '180x180',
        type: 'image/png'
      }
    ]
  },
  manifest: '/manifest.json'
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
