import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Ozhzo Verse — The Digital Operating System for Homes',
  description: 'One place to run your household. Coordinate chores, family calendars, pantry inventory, shopping lists, bills, automations, and AI memory.',
  openGraph: {
    title: 'Ozhzo Verse — One place to run your household',
    description: 'The complete household operating system for busy families, couples, and shared living.',
    url: 'https://app.ozhzo.com',
    siteName: 'Ozhzo Verse',
    locale: 'en_US',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Ozhzo Verse — The Digital Operating System for Homes',
    description: 'One place to run your household. Coordinate chores, groceries, calendars, and bills in one connected workspace.',
  },
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
