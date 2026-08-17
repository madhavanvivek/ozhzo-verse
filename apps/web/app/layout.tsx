import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Ozhzo Verse',
  description: 'Where Home Comes Together.',
  icons: {
    icon: [
      {
        url: '/brand/favicon/ozhzo-primary-favicon.svg',
        type: 'image/svg+xml'
      }
    ],
    shortcut: '/brand/favicon/ozhzo-primary-favicon.svg',
    apple: [
      {
        url: '/brand/favicon/ozhzo-primary-favicon.svg',
        type: 'image/svg+xml'
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
