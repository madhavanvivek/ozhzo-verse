import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { Logo } from '@/components/brand/Logo';

export default function HomePage() {
  return (
    <main style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 'var(--space-6)', textAlign: 'center' }}>
      <div style={{ maxWidth: '640px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <div style={{ marginBottom: 'var(--space-6)' }}>
          <Logo variant="full" width={260} height={180} />
        </div>
        <div style={{ display: 'inline-block', padding: '4px 12px', backgroundColor: 'var(--color-primary-100)', color: 'var(--color-primary-900)', borderRadius: 'var(--radius-full)', fontSize: '13px', fontWeight: 600, marginBottom: 'var(--space-4)' }}>
          Where Home Comes Together.
        </div>
        <h1 style={{ fontSize: '2.25rem', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: 'var(--space-4)', color: 'var(--color-primary-900)' }}>
          The Digital Operating System for Homes
        </h1>
        <p style={{ fontSize: '1.125rem', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-8)', lineHeight: 1.6 }}>
          Coordinate chores, pantry inventory, shopping lists, bills, and family calendars in one unified workspace.
        </p>
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
          <Link href="/login">
            <Button size="lg">Sign In</Button>
          </Link>
          <Link href="/register">
            <Button variant="secondary" size="lg">Get Started</Button>
          </Link>
        </div>
      </div>
    </main>
  );
}
