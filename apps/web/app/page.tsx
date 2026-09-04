import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { Logo } from '@/components/brand/Logo';
import { 
  CheckCircle2, 
  Calendar, 
  ShoppingCart, 
  Receipt, 
  Boxes, 
  Sparkles, 
  Zap, 
  Brain, 
  ShieldCheck, 
  ArrowRight, 
  Star, 
  Clock
} from 'lucide-react';


export default function HomePage() {
  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#FAFAFA', color: '#1E293B', fontFamily: 'inherit' }}>
      {/* -------------------------------------------------------------------------- */}
      {/* NAVIGATION BAR */}
      {/* -------------------------------------------------------------------------- */}
      <header style={{ borderBottom: '1px solid #E2E8F0', backgroundColor: '#FFFFFF', position: 'sticky', top: 0, zIndex: 50 }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '16px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '8px', textDecoration: 'none' }}>
            <Logo variant="mark" width={36} height={36} />
            <span style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0F172A', letterSpacing: '-0.02em' }}>Ozhzo Verse</span>
          </Link>

          <nav style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
            <a href="#modules" style={{ fontSize: '0.875rem', fontWeight: 500, color: '#64748B', textDecoration: 'none' }}>Features</a>
            <a href="#how-it-works" style={{ fontSize: '0.875rem', fontWeight: 500, color: '#64748B', textDecoration: 'none' }}>How it Works</a>
            <a href="#pricing" style={{ fontSize: '0.875rem', fontWeight: 500, color: '#64748B', textDecoration: 'none' }}>Pricing</a>
            <a href="#faq" style={{ fontSize: '0.875rem', fontWeight: 500, color: '#64748B', textDecoration: 'none' }}>FAQ</a>
          </nav>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Link href="/login">
              <Button variant="ghost" size="sm">Sign In</Button>
            </Link>
            <Link href="/register">
              <Button size="sm" style={{ backgroundColor: '#0284C7', color: '#FFFFFF', fontWeight: 600 }}>Create Your Home</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* -------------------------------------------------------------------------- */}
      {/* 1. HERO SECTION */}
      {/* -------------------------------------------------------------------------- */}
      <section style={{ padding: '80px 24px 60px', textAlign: 'center', maxWidth: '900px', margin: '0 auto' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '6px 16px', backgroundColor: '#E0F2FE', color: '#0369A1', borderRadius: '9999px', fontSize: '0.875rem', fontWeight: 600, marginBottom: '24px' }}>
          <Sparkles size={16} /> Where Home Comes Together
        </div>
        <h1 style={{ fontSize: '3.5rem', fontWeight: 800, letterSpacing: '-0.03em', lineHeight: 1.15, color: '#0F172A', marginBottom: '20px' }}>
          One place to run your household.
        </h1>
        <p style={{ fontSize: '1.25rem', color: '#475569', lineHeight: 1.6, maxWidth: '720px', margin: '0 auto 36px' }}>
          Organize everyday life in one connected workspace. Chores, family calendars, pantry inventory, shopping lists, bills, automations, and AI memory — all under one Home.
        </p>

        <div style={{ display: 'flex', gap: '16px', justifyContent: 'center', flexWrap: 'wrap' }}>
          <Link href="/register">
            <Button size="lg" style={{ backgroundColor: '#0284C7', color: '#FFFFFF', fontSize: '1.05rem', fontWeight: 700, padding: '14px 28px' }}>
              CREATE YOUR HOME <ArrowRight size={18} style={{ marginLeft: '8px', display: 'inline' }} />
            </Button>
          </Link>
          <a href="#how-it-works">
            <Button variant="secondary" size="lg" style={{ fontSize: '1.05rem', fontWeight: 600, padding: '14px 28px' }}>
              SEE HOW IT WORKS
            </Button>
          </a>
        </div>

        <p style={{ fontSize: '0.875rem', color: '#94A3B8', marginTop: '16px' }}>
          ✨ Free for your first year • No credit card required to get started • Invite your whole family
        </p>
      </section>

      {/* -------------------------------------------------------------------------- */}
      {/* 2. THE PROBLEM SECTION */}
      {/* -------------------------------------------------------------------------- */}
      <section style={{ backgroundColor: '#FFFFFF', borderTop: '1px solid #E2E8F0', borderBottom: '1px solid #E2E8F0', padding: '60px 24px' }}>
        <div style={{ maxWidth: '1100px', margin: '0 auto', textAlign: 'center' }}>
          <span style={{ fontSize: '0.875rem', fontWeight: 700, color: '#EF4444', textTransform: 'uppercase', letterSpacing: '0.05em' }}>The Household Chaos Reality</span>
          <h2 style={{ fontSize: '2.25rem', fontWeight: 800, color: '#0F172A', margin: '12px 0 36px' }}>
            Why managing a modern household feels exhausting.
          </h2>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px', textAlign: 'left' }}>
            <div style={{ padding: '24px', backgroundColor: '#FEF2F2', borderRadius: '12px', border: '1px solid #FEE2E2' }}>
              <div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>📱</div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#991B1B', marginBottom: '8px' }}>Fragmented Chat Threads</h3>
              <p style={{ fontSize: '0.925rem', color: '#7F1D1D', lineHeight: 1.5 }}>
                Chore assignments and shopping items get buried in endless WhatsApp messages and text chains.
              </p>
            </div>

            <div style={{ padding: '24px', backgroundColor: '#FEF2F2', borderRadius: '12px', border: '1px solid #FEE2E2' }}>
              <div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>🧾</div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#991B1B', marginBottom: '8px' }}>Missed Bills & Duplicates</h3>
              <p style={{ fontSize: '0.925rem', color: '#7F1D1D', lineHeight: 1.5 }}>
                Nobody knows who paid the electric bill or who bought the extra milk that’s now spoiling in the fridge.
              </p>
            </div>

            <div style={{ padding: '24px', backgroundColor: '#FEF2F2', borderRadius: '12px', border: '1px solid #FEE2E2' }}>
              <div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>🧠</div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#991B1B', marginBottom: '8px' }}>Invisible Mental Load</h3>
              <p style={{ fontSize: '0.925rem', color: '#7F1D1D', lineHeight: 1.5 }}>
                One person ends up carrying the entire mental burden of remembering filter changes, doctor appointments, and groceries.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* -------------------------------------------------------------------------- */}
      {/* 3. THE OZHZO SOLUTION & 4. CORE MODULES */}
      {/* -------------------------------------------------------------------------- */}
      <section id="modules" style={{ padding: '80px 24px', maxWidth: '1200px', margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: '56px' }}>
          <span style={{ fontSize: '0.875rem', fontWeight: 700, color: '#0284C7', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Complete Household Suite</span>
          <h2 style={{ fontSize: '2.5rem', fontWeight: 800, color: '#0F172A', margin: '12px 0 16px' }}>
            Everything your home needs. All in one place.
          </h2>
          <p style={{ fontSize: '1.125rem', color: '#64748B', maxWidth: '680px', margin: '0 auto' }}>
            Replace 6 separate apps with one unified, privacy-first household operating system.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '28px' }}>
          {/* Module 1: Tasks */}
          <div style={{ backgroundColor: '#FFFFFF', padding: '32px', borderRadius: '16px', border: '1px solid #E2E8F0', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)' }}>
            <div style={{ width: '48px', height: '48px', backgroundColor: '#E0F2FE', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#0284C7', marginBottom: '20px' }}>
              <CheckCircle2 size={24} />
            </div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0F172A', marginBottom: '10px' }}>Chores & Task Management</h3>
            <p style={{ fontSize: '0.95rem', color: '#64748B', lineHeight: 1.6 }}>
              Assign chores to family members with recurring intervals, rotation schedules, and optimistic completion check-offs.
            </p>
          </div>

          {/* Module 2: Shopping & Restock */}
          <div style={{ backgroundColor: '#FFFFFF', padding: '32px', borderRadius: '16px', border: '1px solid #E2E8F0', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)' }}>
            <div style={{ width: '48px', height: '48px', backgroundColor: '#DCFCE7', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#16A34A', marginBottom: '20px' }}>
              <ShoppingCart size={24} />
            </div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0F172A', marginBottom: '10px' }}>Smart Shopping & Restock</h3>
            <p style={{ fontSize: '0.95rem', color: '#64748B', lineHeight: 1.6 }}>
              Real-time synchronized lists organized by store aisle. Checking off groceries automatically updates your pantry inventory.
            </p>
          </div>

          {/* Module 3: Calendar */}
          <div style={{ backgroundColor: '#FFFFFF', padding: '32px', borderRadius: '16px', border: '1px solid #E2E8F0', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)' }}>
            <div style={{ width: '48px', height: '48px', backgroundColor: '#F3E8FF', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9333EA', marginBottom: '20px' }}>
              <Calendar size={24} />
            </div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0F172A', marginBottom: '10px' }}>Unified Family Calendar</h3>
            <p style={{ fontSize: '0.95rem', color: '#64748B', lineHeight: 1.6 }}>
              One timeline that projects events, school appointments, chore deadlines, and bill due dates in a unified view.
            </p>
          </div>

          {/* Module 4: Bills */}
          <div style={{ backgroundColor: '#FFFFFF', padding: '32px', borderRadius: '16px', border: '1px solid #E2E8F0', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)' }}>
            <div style={{ width: '48px', height: '48px', backgroundColor: '#FEF3C7', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#D97706', marginBottom: '20px' }}>
              <Receipt size={24} />
            </div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0F172A', marginBottom: '10px' }}>Household Bills & Expense Split</h3>
            <p style={{ fontSize: '0.95rem', color: '#64748B', lineHeight: 1.6 }}>
              Track recurring utility payments, split rent among roommates, and receive priority alert banners 3 days before due dates.
            </p>
          </div>

          {/* Module 5: Inventory */}
          <div style={{ backgroundColor: '#FFFFFF', padding: '32px', borderRadius: '16px', border: '1px solid #E2E8F0', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)' }}>
            <div style={{ width: '48px', height: '48px', backgroundColor: '#FFE4E6', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#E11D48', marginBottom: '20px' }}>
              <Boxes size={24} />
            </div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0F172A', marginBottom: '10px' }}>Pantry & Asset Inventory</h3>
            <p style={{ fontSize: '0.95rem', color: '#64748B', lineHeight: 1.6 }}>
              Differentiate consumables (milk, detergent) from durable assets (appliances, warranties) with automatic low-stock triggers.
            </p>
          </div>

          {/* Module 6: Today View */}
          <div style={{ backgroundColor: '#FFFFFF', padding: '32px', borderRadius: '16px', border: '1px solid #E2E8F0', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)' }}>
            <div style={{ width: '48px', height: '48px', backgroundColor: '#CCFBF1', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#0D9488', marginBottom: '20px' }}>
              <Clock size={24} />
            </div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0F172A', marginBottom: '10px' }}>The "Today" Command Center</h3>
            <p style={{ fontSize: '0.95rem', color: '#64748B', lineHeight: 1.6 }}>
              Wake up to a single clear briefing: what chores are due today, what needs buying, and which bills need settling.
            </p>
          </div>
        </div>
      </section>

      {/* -------------------------------------------------------------------------- */}
      {/* 5. AI ASSISTANT, 6. AUTOMATIONS & 7. HOUSEHOLD MEMORY */}
      {/* -------------------------------------------------------------------------- */}
      <section style={{ backgroundColor: '#0F172A', color: '#FFFFFF', padding: '80px 24px' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '56px' }}>
            <span style={{ fontSize: '0.875rem', fontWeight: 700, color: '#38BDF8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Household Intelligence</span>
            <h2 style={{ fontSize: '2.5rem', fontWeight: 800, color: '#FFFFFF', margin: '12px 0 16px' }}>
              Your home runs on autopilot.
            </h2>
            <p style={{ fontSize: '1.125rem', color: '#94A3B8', maxWidth: '680px', margin: '0 auto' }}>
              AI designed specifically for domestic harmony — always with your explicit confirmation before taking action.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '32px' }}>
            {/* AI Assistant */}
            <div style={{ backgroundColor: '#1E293B', padding: '36px', borderRadius: '16px', border: '1px solid #334155' }}>
              <div style={{ color: '#38BDF8', marginBottom: '16px' }}><Sparkles size={32} /></div>
              <h3 style={{ fontSize: '1.35rem', fontWeight: 700, marginBottom: '12px' }}>Contextual AI Assistant</h3>
              <p style={{ color: '#94A3B8', fontSize: '0.95rem', lineHeight: 1.6, marginBottom: '16px' }}>
                Ask *"What chores are left today?"* or *"Add olive oil to groceries"*. The assistant crafts structured Action Proposals that you confirm with one tap.
              </p>
              <div style={{ padding: '12px 16px', backgroundColor: '#0F172A', borderRadius: '8px', borderLeft: '3px solid #38BDF8', fontSize: '0.85rem', color: '#CBD5E1' }}>
                💬 "I've drafted a proposal to add Whole Milk to your shopping list. Confirm?"
              </div>
            </div>

            {/* Smart Automations */}
            <div style={{ backgroundColor: '#1E293B', padding: '36px', borderRadius: '16px', border: '1px solid #334155' }}>
              <div style={{ color: '#FBBF24', marginBottom: '16px' }}><Zap size={32} /></div>
              <h3 style={{ fontSize: '1.35rem', fontWeight: 700, marginBottom: '12px' }}>Event-Driven Automations</h3>
              <p style={{ color: '#94A3B8', fontSize: '0.95rem', lineHeight: 1.6, marginBottom: '16px' }}>
                Set up effortless rules: when dish soap drops below 2 units $\to$ automatically add to shopping list. When trash day arrives $\to$ alert the assigned member.
              </p>
              <div style={{ padding: '12px 16px', backgroundColor: '#0F172A', borderRadius: '8px', borderLeft: '3px solid #FBBF24', fontSize: '0.85rem', color: '#CBD5E1' }}>
                ⚡ Automation: "Low Pantry Soap $\to$ Auto-Add to Groceries" executed.
              </div>
            </div>

            {/* Household Memory */}
            <div style={{ backgroundColor: '#1E293B', padding: '36px', borderRadius: '16px', border: '1px solid #334155' }}>
              <div style={{ color: '#A855F7', marginBottom: '16px' }}><Brain size={32} /></div>
              <h3 style={{ fontSize: '1.35rem', fontWeight: 700, marginBottom: '12px' }}>Household Memory Vault</h3>
              <p style={{ color: '#94A3B8', fontSize: '0.95rem', lineHeight: 1.6, marginBottom: '16px' }}>
                Store essential family preferences, dietary habits, Wi-Fi passwords, and appliance maintenance schedules securely in your private home vault.
              </p>
              <div style={{ padding: '12px 16px', backgroundColor: '#0F172A', borderRadius: '8px', borderLeft: '3px solid #A855F7', fontSize: '0.85rem', color: '#CBD5E1' }}>
                🧠 Memory: "Leo is allergic to peanuts. Organic whole milk preferred."
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* -------------------------------------------------------------------------- */}
      {/* 8. HOW IT WORKS (3 SIMPLE STEPS) */}
      {/* -------------------------------------------------------------------------- */}
      <section id="how-it-works" style={{ padding: '80px 24px', maxWidth: '1000px', margin: '0 auto', textAlign: 'center' }}>
        <span style={{ fontSize: '0.875rem', fontWeight: 700, color: '#0284C7', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Simple Onboarding</span>
        <h2 style={{ fontSize: '2.5rem', fontWeight: 800, color: '#0F172A', margin: '12px 0 48px' }}>
          Up and running in less than 3 minutes.
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '32px', textAlign: 'left' }}>
          <div style={{ padding: '28px', backgroundColor: '#FFFFFF', borderRadius: '16px', border: '1px solid #E2E8F0' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#0284C7', marginBottom: '12px' }}>01</div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#0F172A', marginBottom: '8px' }}>Create Your Home</h3>
            <p style={{ fontSize: '0.925rem', color: '#64748B', lineHeight: 1.5 }}>
              Choose a name and currency. Your dedicated workspace is created instantly with private encryption.
            </p>
          </div>

          <div style={{ padding: '28px', backgroundColor: '#FFFFFF', borderRadius: '16px', border: '1px solid #E2E8F0' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#0284C7', marginBottom: '12px' }}>02</div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#0F172A', marginBottom: '8px' }}>Invite Family Members</h3>
            <p style={{ fontSize: '0.925rem', color: '#64748B', lineHeight: 1.5 }}>
              Share a secure link, invite code, or QR code. Assign permissions (Admin, Member, Child, Guest).
            </p>
          </div>

          <div style={{ padding: '28px', backgroundColor: '#FFFFFF', borderRadius: '16px', border: '1px solid #E2E8F0' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#0284C7', marginBottom: '12px' }}>03</div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#0F172A', marginBottom: '8px' }}>Experience Harmony</h3>
            <p style={{ fontSize: '0.925rem', color: '#64748B', lineHeight: 1.5 }}>
              Start checking off tasks, sharing grocery lists, and letting automations handle the daily reminders.
            </p>
          </div>
        </div>
      </section>

      {/* -------------------------------------------------------------------------- */}
      {/* 9. WHO IT IS FOR (PERSONAS) */}
      {/* -------------------------------------------------------------------------- */}
      <section style={{ backgroundColor: '#F1F5F9', padding: '80px 24px' }}>
        <div style={{ maxWidth: '1100px', margin: '0 auto', textAlign: 'center' }}>
          <span style={{ fontSize: '0.875rem', fontWeight: 700, color: '#0284C7', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Tailored for Every Home</span>
          <h2 style={{ fontSize: '2.5rem', fontWeight: 800, color: '#0F172A', margin: '12px 0 48px' }}>
            Built for how real households live.
          </h2>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '24px', textAlign: 'left' }}>
            <div style={{ backgroundColor: '#FFFFFF', padding: '24px', borderRadius: '12px', border: '1px solid #E2E8F0' }}>
              <div style={{ fontSize: '1.8rem', marginBottom: '10px' }}>👨‍👩‍👧‍👦</div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>Busy Families</h3>
              <p style={{ fontSize: '0.9rem', color: '#64748B', lineHeight: 1.5 }}>
                Coordinate school events, assign chores to kids with Child-safe limits, and restock family groceries without stress.
              </p>
            </div>

            <div style={{ backgroundColor: '#FFFFFF', padding: '24px', borderRadius: '12px', border: '1px solid #E2E8F0' }}>
              <div style={{ fontSize: '1.8rem', marginBottom: '10px' }}>💑</div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>Couples</h3>
              <p style={{ fontSize: '0.9rem', color: '#64748B', lineHeight: 1.5 }}>
                Split shared bills, coordinate weekend meal planning, and keep household maintenance records in one synchronized space.
              </p>
            </div>

            <div style={{ backgroundColor: '#FFFFFF', padding: '24px', borderRadius: '12px', border: '1px solid #E2E8F0' }}>
              <div style={{ fontSize: '1.8rem', marginBottom: '10px' }}>🏡</div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>Shared Living & Roommates</h3>
              <p style={{ fontSize: '0.9rem', color: '#64748B', lineHeight: 1.5 }}>
                Fair chore rotations, shared consumable supplies tracking, and transparent expense splitting without awkward texts.
              </p>
            </div>

            <div style={{ backgroundColor: '#FFFFFF', padding: '24px', borderRadius: '12px', border: '1px solid #E2E8F0' }}>
              <div style={{ fontSize: '1.8rem', marginBottom: '10px' }}>🧑‍💻</div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0F172A', marginBottom: '6px' }}>Solo Power Users</h3>
              <p style={{ fontSize: '0.9rem', color: '#64748B', lineHeight: 1.5 }}>
                Automate personal routines, maintain asset warranties, and use AI assistance to streamline life admin.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* -------------------------------------------------------------------------- */}
      {/* 10. PRICING SECTION */}
      {/* -------------------------------------------------------------------------- */}
      <section id="pricing" style={{ padding: '80px 24px', maxWidth: '1000px', margin: '0 auto', textAlign: 'center' }}>
        <span style={{ fontSize: '0.875rem', fontWeight: 700, color: '#0284C7', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Simple, Honest Pricing</span>
        <h2 style={{ fontSize: '2.5rem', fontWeight: 800, color: '#0F172A', margin: '12px 0 16px' }}>
          Free for your first year.
        </h2>
        <p style={{ fontSize: '1.125rem', color: '#64748B', maxWidth: '600px', margin: '0 auto 48px' }}>
          No credit card required. Experience complete household harmony before paying a single cent.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '32px', textAlign: 'left', maxWidth: '800px', margin: '0 auto' }}>
          {/* Free Tier */}
          <div style={{ backgroundColor: '#FFFFFF', padding: '36px', borderRadius: '20px', border: '2px solid #0284C7', position: 'relative', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.05)' }}>
            <div style={{ position: 'absolute', top: '-14px', right: '24px', backgroundColor: '#0284C7', color: '#FFFFFF', padding: '4px 12px', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase' }}>
              Special Launch Offer
            </div>
            <h3 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#0F172A', marginBottom: '8px' }}>First Household</h3>
            <div style={{ fontSize: '2.5rem', fontWeight: 800, color: '#0F172A', marginBottom: '16px' }}>
              $0 <span style={{ fontSize: '1rem', fontWeight: 500, color: '#64748B' }}>/ first year</span>
            </div>
            <p style={{ fontSize: '0.9rem', color: '#64748B', marginBottom: '24px' }}>
              Full access to all household modules and AI intelligence for your primary home.
            </p>
            <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 32px', display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.925rem', color: '#334155' }}>
              <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><CheckCircle2 size={16} color="#0284C7" /> Unlimited family members & roles</li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><CheckCircle2 size={16} color="#0284C7" /> Tasks, Shopping, Calendar, Bills, Inventory</li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><CheckCircle2 size={16} color="#0284C7" /> AI Assistant & confirmed Action Proposals</li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><CheckCircle2 size={16} color="#0284C7" /> Smart event-driven automations</li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><CheckCircle2 size={16} color="#0284C7" /> AES-GCM encrypted household memory</li>
            </ul>
            <Link href="/register">
              <Button size="lg" style={{ width: '100%', backgroundColor: '#0284C7', color: '#FFFFFF', fontWeight: 700 }}>
                CREATE YOUR HOME FREE
              </Button>
            </Link>
          </div>

          {/* Pro Tier */}
          <div style={{ backgroundColor: '#FFFFFF', padding: '36px', borderRadius: '20px', border: '1px solid #E2E8F0', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <h3 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#0F172A', marginBottom: '8px' }}>Household Pro</h3>
              <div style={{ fontSize: '2.5rem', fontWeight: 800, color: '#0F172A', marginBottom: '16px' }}>
                $4.99 <span style={{ fontSize: '1rem', fontWeight: 500, color: '#64748B' }}>/ month</span>
              </div>
              <p style={{ fontSize: '0.9rem', color: '#64748B', marginBottom: '24px' }}>
                For multiple properties, vacation homes, or extended multi-year family management.
              </p>
              <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 32px', display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.925rem', color: '#334155' }}>
                <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><CheckCircle2 size={16} color="#16A34A" /> Multiple Home workspaces (up to 5)</li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><CheckCircle2 size={16} color="#16A34A" /> Higher AI token quota limits</li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><CheckCircle2 size={16} color="#16A34A" /> Priority backup retention & export</li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><CheckCircle2 size={16} color="#16A34A" /> Early access to new automation recipes</li>
              </ul>
            </div>
            <Link href="/register">
              <Button variant="secondary" size="lg" style={{ width: '100%', fontWeight: 600 }}>
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* -------------------------------------------------------------------------- */}
      {/* 11. SECURITY & PRIVACY SECTION */}
      {/* -------------------------------------------------------------------------- */}
      <section style={{ backgroundColor: '#FFFFFF', borderTop: '1px solid #E2E8F0', borderBottom: '1px solid #E2E8F0', padding: '60px 24px' }}>
        <div style={{ maxWidth: '1000px', margin: '0 auto', display: 'flex', alignItems: 'center', gap: '48px', flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 400px' }}>
            <div style={{ width: '48px', height: '48px', backgroundColor: '#E0F2FE', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#0284C7', marginBottom: '16px' }}>
              <ShieldCheck size={28} />
            </div>
            <h2 style={{ fontSize: '2rem', fontWeight: 800, color: '#0F172A', marginBottom: '16px' }}>
              Your household data is private. Period.
            </h2>
            <p style={{ fontSize: '1rem', color: '#64748B', lineHeight: 1.6, marginBottom: '20px' }}>
              We never sell your data, we never serve advertisements, and we never use your personal household notes to train public AI models.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.925rem', color: '#334155' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>🔒 Strict multi-tenant Home data isolation</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>🛡️ AES-GCM encrypted database snapshots</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>🇪🇺 Full GDPR data portability & one-click export</div>
            </div>
          </div>
          <div style={{ flex: '1 1 320px', backgroundColor: '#F8FAFC', padding: '32px', borderRadius: '16px', border: '1px solid #E2E8F0' }}>
            <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#0F172A', marginBottom: '8px' }}>Our Privacy Commitment:</div>
            <p style={{ fontSize: '0.875rem', color: '#64748B', lineHeight: 1.6 }}>
              Household data belongs exclusively to your family. You can export your complete household archive or permanently delete your account at any time with cryptographic audit confirmation.
            </p>
          </div>
        </div>
      </section>

      {/* -------------------------------------------------------------------------- */}
      {/* 12. TESTIMONIALS & PILOT EVIDENCE */}
      {/* -------------------------------------------------------------------------- */}
      <section style={{ padding: '80px 24px', maxWidth: '1100px', margin: '0 auto', textAlign: 'center' }}>
        <span style={{ fontSize: '0.875rem', fontWeight: 700, color: '#0284C7', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Validated by Real Homes</span>
        <h2 style={{ fontSize: '2.5rem', fontWeight: 800, color: '#0F172A', margin: '12px 0 48px' }}>
          Loved by 50+ pilot households.
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px', textAlign: 'left' }}>
          <div style={{ backgroundColor: '#FFFFFF', padding: '28px', borderRadius: '16px', border: '1px solid #E2E8F0', boxShadow: '0 2px 4px rgba(0,0,0,0.04)' }}>
            <div style={{ display: 'flex', gap: '4px', color: '#F59E0B', marginBottom: '12px' }}>
              {[...Array(5)].map((_, i) => <Star key={i} size={16} fill="#F59E0B" />)}
            </div>
            <p style={{ fontSize: '0.95rem', color: '#334155', lineHeight: 1.6, marginBottom: '16px' }}>
              "The automatic restock from our shopping list to our pantry inventory changed everything. We stopped buying duplicate milk and pasta."
            </p>
            <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#0F172A' }}>Sarah & David M.</div>
            <div style={{ fontSize: '0.8rem', color: '#94A3B8' }}>Family of 4 • Pilot Member</div>
          </div>

          <div style={{ backgroundColor: '#FFFFFF', padding: '28px', borderRadius: '16px', border: '1px solid #E2E8F0', boxShadow: '0 2px 4px rgba(0,0,0,0.04)' }}>
            <div style={{ display: 'flex', gap: '4px', color: '#F59E0B', marginBottom: '12px' }}>
              {[...Array(5)].map((_, i) => <Star key={i} size={16} fill="#F59E0B" />)}
            </div>
            <p style={{ fontSize: '0.95rem', color: '#334155', lineHeight: 1.6, marginBottom: '16px' }}>
              "My roommates and I used to argue constantly over chores and splitting utility bills. Ozhzo solved that in the first weekend."
            </p>
            <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#0F172A' }}>Marcus T.</div>
            <div style={{ fontSize: '0.8rem', color: '#94A3B8' }}>Shared Apartment • 3 Roommates</div>
          </div>

          <div style={{ backgroundColor: '#FFFFFF', padding: '28px', borderRadius: '16px', border: '1px solid #E2E8F0', boxShadow: '0 2px 4px rgba(0,0,0,0.04)' }}>
            <div style={{ display: 'flex', gap: '4px', color: '#F59E0B', marginBottom: '12px' }}>
              {[...Array(5)].map((_, i) => <Star key={i} size={16} fill="#F59E0B" />)}
            </div>
            <p style={{ fontSize: '0.95rem', color: '#334155', lineHeight: 1.6, marginBottom: '16px' }}>
              "The AI assistant actually asks for my confirmation before creating tasks. It feels trustworthy, fast, and remarkably helpful."
            </p>
            <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#0F172A' }}>Elena R.</div>
            <div style={{ fontSize: '0.8rem', color: '#94A3B8' }}>Working Parent • Pilot Member</div>
          </div>
        </div>
      </section>

      {/* -------------------------------------------------------------------------- */}
      {/* 13. FREQUENTLY ASKED QUESTIONS (FAQ) */}
      {/* -------------------------------------------------------------------------- */}
      <section id="faq" style={{ backgroundColor: '#F8FAFC', padding: '80px 24px', borderTop: '1px solid #E2E8F0' }}>
        <div style={{ maxWidth: '800px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '48px' }}>
            <span style={{ fontSize: '0.875rem', fontWeight: 700, color: '#0284C7', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Got Questions?</span>
            <h2 style={{ fontSize: '2.5rem', fontWeight: 800, color: '#0F172A', margin: '12px 0 16px' }}>
              Frequently Asked Questions
            </h2>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ backgroundColor: '#FFFFFF', padding: '24px', borderRadius: '12px', border: '1px solid #E2E8F0' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#0F172A', marginBottom: '8px' }}>Is it really free for the first year?</h3>
              <p style={{ fontSize: '0.925rem', color: '#64748B', lineHeight: 1.6 }}>
                Yes! Your primary Home is completely free for 1 full year with all core modules, family member invitations, and AI assistant capabilities. No credit card is required to sign up.
              </p>
            </div>

            <div style={{ backgroundColor: '#FFFFFF', padding: '24px', borderRadius: '12px', border: '1px solid #E2E8F0' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#0F172A', marginBottom: '8px' }}>How do family members join my Home?</h3>
              <p style={{ fontSize: '0.925rem', color: '#64748B', lineHeight: 1.6 }}>
                As the Home Owner, you can generate a private invite link, a 6-character code, or a printable QR code from the Members tab. Family members join instantly from their phones or browsers.
              </p>
            </div>

            <div style={{ backgroundColor: '#FFFFFF', padding: '24px', borderRadius: '12px', border: '1px solid #E2E8F0' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#0F172A', marginBottom: '8px' }}>Can my kids use Ozhzo without seeing our bills?</h3>
              <p style={{ fontSize: '0.925rem', color: '#64748B', lineHeight: 1.6 }}>
                Yes. Ozhzo includes Role-Based Access Control. You can assign the "Child" role so kids only see their assigned chores and family calendar events without access to billing or home settings.
              </p>
            </div>

            <div style={{ backgroundColor: '#FFFFFF', padding: '24px', borderRadius: '12px', border: '1px solid #E2E8F0' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#0F172A', marginBottom: '8px' }}>Does Ozhzo work on mobile devices?</h3>
              <p style={{ fontSize: '0.925rem', color: '#64748B', lineHeight: 1.6 }}>
                Yes! Ozhzo Verse is fully responsive and optimized for mobile touchscreens with bottom bar navigation, quick-add menus, and offline-capable data caching.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* -------------------------------------------------------------------------- */}
      {/* 14. FINAL CONVERSION BANNER */}
      {/* -------------------------------------------------------------------------- */}
      <section style={{ backgroundColor: '#0284C7', color: '#FFFFFF', padding: '80px 24px', textAlign: 'center' }}>
        <div style={{ maxWidth: '800px', margin: '0 auto' }}>
          <h2 style={{ fontSize: '2.75rem', fontWeight: 800, letterSpacing: '-0.02em', marginBottom: '16px' }}>
            Bring harmony to your home today.
          </h2>
          <p style={{ fontSize: '1.2rem', color: '#E0F2FE', lineHeight: 1.6, marginBottom: '36px' }}>
            Join thousands of busy households who organize chores, groceries, calendars, and bills in one connected place.
          </p>
          <Link href="/register">
            <Button size="lg" style={{ backgroundColor: '#FFFFFF', color: '#0284C7', fontSize: '1.1rem', fontWeight: 800, padding: '16px 36px', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.2)' }}>
              CREATE YOUR HOME FREE <ArrowRight size={20} style={{ marginLeft: '8px', display: 'inline' }} />
            </Button>
          </Link>
          <p style={{ fontSize: '0.85rem', color: '#BAE6FD', marginTop: '16px' }}>
            Instant setup • 1 year free • Cancel anytime
          </p>
        </div>
      </section>

      {/* -------------------------------------------------------------------------- */}
      {/* FOOTER */}
      {/* -------------------------------------------------------------------------- */}
      <footer style={{ backgroundColor: '#0F172A', color: '#64748B', padding: '48px 24px 32px', borderTop: '1px solid #1E293B', fontSize: '0.875rem' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Logo variant="mark" width={28} height={28} />
            <span style={{ fontWeight: 700, color: '#F8FAFC' }}>Ozhzo Verse</span>
            <span>— The Digital Operating System for Homes</span>
          </div>

          <div style={{ display: 'flex', gap: '24px' }}>
            <a href="#modules" style={{ color: '#94A3B8', textDecoration: 'none' }}>Features</a>
            <a href="#pricing" style={{ color: '#94A3B8', textDecoration: 'none' }}>Pricing</a>
            <Link href="/login" style={{ color: '#94A3B8', textDecoration: 'none' }}>Sign In</Link>
            <Link href="/register" style={{ color: '#94A3B8', textDecoration: 'none' }}>Register</Link>
          </div>
        </div>
        <div style={{ maxWidth: '1200px', margin: '24px auto 0', textAlign: 'center', fontSize: '0.8rem', color: '#475569' }}>
          © {new Date().getFullYear()} Ozhzo Verse Inc. All rights reserved. Privacy-First Household Technology.
        </div>
      </footer>
    </div>
  );
}
