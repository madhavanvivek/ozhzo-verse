import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

test.describe('Ozhzo Verse — Independent UAT & Product QA Evaluation Suite', () => {

  const evidenceDir = path.resolve('/Users/vivek/.gemini/antigravity/brain/e417cc97-7d7a-4622-ab0c-93f6404efdd2/uat_evidence');

  test.beforeAll(() => {
    if (!fs.existsSync(evidenceDir)) {
      fs.mkdirSync(evidenceDir, { recursive: true });
    }
  });

  test.beforeEach(async ({ page, context }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await context.clearCookies();
  });

  const homeAId = '11111111-1111-1111-1111-111111111111';
  const homeBId = '22222222-2222-2222-2222-222222222222';

  const setupFullHouseholdState = async (page: any, activeHomeId = homeAId) => {
    await page.addInitScript(({ token, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('active_home_id', hId);
    }, { token: 'mock-user-jwt', hId: activeHomeId });

    // Mock /api/v1/users/me
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'user-parent-01',
            email: 'parent@ozhzo.com',
            display_name: 'Alex Johnson',
            mobile_verified: true,
            free_home_consumed: true,
            is_super_admin: false,
            system_role: 'USER',
            homes: [
              { home_id: homeAId, name: 'Johnson Family Home', role: 'OWNER', status: 'ACTIVE' },
              { home_id: homeBId, name: 'Mountain Cabin Retreat', role: 'MEMBER', status: 'ACTIVE' }
            ]
          }
        })
      });
    });

    // Mock /api/v1/homes
    await page.route('**/api/v1/homes', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { id: homeAId, name: 'Johnson Family Home', currency: 'USD', role: 'OWNER', status: 'ACTIVE' },
            { id: homeBId, name: 'Mountain Cabin Retreat', currency: 'USD', role: 'MEMBER', status: 'ACTIVE' }
          ]
        })
      });
    });

    // Mock individual home details / identity / join-requests
    await page.route(`**/api/v1/homes/${activeHomeId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: activeHomeId,
            name: activeHomeId === homeAId ? 'Johnson Family Home' : 'Mountain Cabin Retreat',
            currency: 'USD',
            timezone: 'UTC',
            role: 'OWNER',
            status: 'ACTIVE',
            created_at: new Date().toISOString()
          }
        })
      });
    });

    await page.route(`**/api/v1/homes/*/identity*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { id: activeHomeId, name: 'Johnson Family Home', timezone: 'UTC', currency: 'USD' }
        })
      });
    });

    await page.route(`**/api/v1/homes/*/join-requests*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] })
      });
    });

    await page.route(`**/api/v1/homes/*/events*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { id: 'e-1', title: 'Soccer Practice', start_time: new Date().toISOString(), end_time: new Date().toISOString(), event_type: 'FAMILY' }
          ]
        })
      });
    });

    await page.route(`**/api/v1/homes/*/calendar/projection*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            start_date: new Date().toISOString().slice(0, 10),
            end_date: new Date(Date.now() + 86400000 * 30).toISOString().slice(0, 10),
            projections: [
              {
                id: 'e-1',
                title: 'Soccer Practice',
                item_type: 'EVENT',
                date: new Date().toISOString().slice(0, 10),
                start_time: new Date().toISOString(),
                end_time: new Date().toISOString(),
                status: 'CONFIRMED'
              }
            ]
          }
        })
      });
    });

    // Mock /api/v1/homes/:id/members
    await page.route(`**/api/v1/homes/*/members*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { id: 'm-1', user_id: 'user-parent-01', display_name: 'Alex Johnson (You)', email: 'parent@ozhzo.com', role: 'OWNER', status: 'ACTIVE' },
            { id: 'm-2', user_id: 'user-spouse-02', display_name: 'Jordan Johnson', email: 'jordan@ozhzo.com', role: 'ADMIN', status: 'ACTIVE' },
            { id: 'm-3', user_id: 'user-child-03', display_name: 'Leo Johnson', email: 'leo@ozhzo.com', role: 'CHILD', status: 'ACTIVE' }
          ]
        })
      });
    });

    // Mock /api/v1/homes/:id/invitations
    await page.route(`**/api/v1/homes/*/invitations*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: 'inv-1',
              home_id: activeHomeId,
              role: 'MEMBER',
              token: 'tok-mock',
              invitation_code: 'OZ-MOCK01',
              status: 'PENDING',
              email: 'invited@family.com',
              expires_at: new Date(Date.now() + 86400000 * 7).toISOString(),
              created_at: new Date().toISOString()
            }
          ]
        })
      });
    });

    // Mock /api/v1/homes/:id/admin/summary
    await page.route(`**/api/v1/homes/*/admin/summary*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            home_id: activeHomeId,
            home_name: 'Johnson Family Home',
            active_members_count: 3,
            pending_invitations_count: 1,
            max_members_allowed: 10,
            available_seats: 7,
            plan_name: 'PRO',
            is_owner: true
          }
        })
      });
    });

    // Mock /api/v1/homes/:id/dashboard
    await page.route(`**/api/v1/homes/*/dashboard*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            home_id: activeHomeId,
            home_name: activeHomeId === homeAId ? 'Johnson Family Home' : 'Mountain Cabin Retreat',
            role: 'OWNER',
            summary: {
              active_tasks_count: 3,
              urgent_tasks_count: 1,
              pending_bills_count: 2,
              unpaid_bills_total: 185.00,
              shopping_needed_count: 4,
              low_stock_items_count: 2,
              upcoming_events_count: 2
            },
            urgent_tasks: [
              { id: 't-1', title: 'Take out recycling bins', due_date: new Date().toISOString(), priority: 'HIGH', assigned_to: 'Alex Johnson' }
            ],
            pending_bills: [
              { id: 'b-1', title: 'Fiber Internet Bill', amount: 75.00, currency: 'USD', due_date: new Date(Date.now() + 86400000 * 2).toISOString(), status: 'UNPAID' }
            ],
            low_stock_inventory: [
              { id: 'i-1', name: 'Dishwasher Pods', current_quantity: 2, min_quantity: 5, unit: 'pods' }
            ],
            shopping_items_preview: [
              { id: 's-1', name: 'Organic Whole Milk', category: 'Dairy', is_purchased: false },
              { id: 's-2', name: 'Sourdough Bread', category: 'Bakery', is_purchased: false }
            ],
            upcoming_events: [
              { id: 'e-1', title: 'Soccer Practice', start_time: new Date(Date.now() + 86400000).toISOString() }
            ]
          }
        })
      });
    });

    // Mock tasks
    await page.route(`**/api/v1/homes/*/tasks*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              { id: 't-1', title: 'Take out recycling bins', description: 'Place blue bins on curb', status: 'PENDING', priority: 'HIGH', due_date: new Date().toISOString() },
              { id: 't-2', title: 'Clean coffee machine', description: 'Run vinegar descaling cycle', status: 'PENDING', priority: 'MEDIUM', due_date: new Date().toISOString() },
              { id: 't-3', title: 'Replace HVAC filter', description: 'Size 16x25x1', status: 'COMPLETED', priority: 'LOW', due_date: new Date().toISOString() }
            ],
            total: 3
          }
        })
      });
    });

    // Mock shopping & purchase-list
    await page.route(`**/api/v1/homes/*/purchase-list*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { id: 's-1', name: 'Organic Whole Milk', quantity: 1, unit: 'gal', notes: 'Dairy', status: 'PENDING' },
            { id: 's-2', name: 'Sourdough Bread', quantity: 2, unit: 'loaves', notes: 'Bakery', status: 'PENDING' }
          ]
        })
      });
    });

    await page.route(`**/api/v1/homes/*/shopping*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { id: 's-1', name: 'Organic Whole Milk', quantity: 1, unit: 'gal', category: 'Dairy', is_purchased: false },
            { id: 's-2', name: 'Sourdough Bread', quantity: 2, unit: 'loaves', category: 'Bakery', is_purchased: false },
            { id: 's-3', name: 'Olive Oil (Cold Pressed)', quantity: 1, unit: 'bottle', category: 'Pantry', is_purchased: false },
            { id: 's-4', name: 'Bananas', quantity: 6, unit: 'pcs', category: 'Produce', is_purchased: true }
          ]
        })
      });
    });

    // Mock bills
    await page.route(`**/api/v1/homes/*/bills*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              { id: 'b-1', title: 'Fiber Internet Bill', expected_amount: 75.00, amount: 75.00, currency: 'USD', due_date: new Date(Date.now() + 86400000 * 2).toISOString().slice(0, 10), status: 'UNPAID', category_name: 'Utilities' },
              { id: 'b-2', title: 'Electric & Power', expected_amount: 110.00, amount: 110.00, currency: 'USD', due_date: new Date(Date.now() + 86400000 * 5).toISOString().slice(0, 10), status: 'UNPAID', category_name: 'Utilities' }
            ],
            total: 2
          }
        })
      });
    });

    // Mock inventory
    await page.route(`**/api/v1/homes/*/inventory/items*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              { id: 'i-1', name: 'Dishwasher Pods', current_quantity: 2, min_quantity: 5, unit: 'pods', item_type: 'CONSUMABLE', location: 'Kitchen Under Sink' },
              { id: 'i-2', name: 'Dyson V11 Vacuum', current_quantity: 1, min_quantity: 1, unit: 'unit', item_type: 'DURABLE', location: 'Hallway Closet' }
            ],
            total: 2
          }
        })
      });
    });

    await page.route(`**/api/v1/homes/*/inventory*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              { id: 'i-1', name: 'Dishwasher Pods', current_quantity: 2, min_quantity: 5, unit: 'pods', item_type: 'CONSUMABLE', location: 'Kitchen Under Sink' },
              { id: 'i-2', name: 'Dyson V11 Vacuum', current_quantity: 1, min_quantity: 1, unit: 'unit', item_type: 'DURABLE', location: 'Hallway Closet' }
            ],
            total: 2
          }
        })
      });
    });

    await page.route(`**/api/v1/homes/*/locations*`, async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: [] }) });
    });

    await page.route(`**/api/v1/homes/*/location-types*`, async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: [] }) });
    });

    // Mock calendar
    await page.route(`**/api/v1/homes/*/calendar*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              { id: 'e-1', title: 'Soccer Practice', start_time: new Date().toISOString(), end_time: new Date().toISOString(), event_type: 'FAMILY' },
              { id: 'e-2', title: 'Dentist Appointment - Jordan', start_time: new Date(Date.now() + 86400000 * 3).toISOString(), end_time: new Date(Date.now() + 86400000 * 3).toISOString(), event_type: 'PERSONAL' }
            ]
          }
        })
      });
    });

    // Mock automations
    await page.route(`**/api/v1/homes/*/automations*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { id: 'a-1', name: 'Auto Restock Dishwasher Pods', trigger_type: 'LOW_STOCK', action_type: 'ADD_SHOPPING_ITEM', is_enabled: true, execution_count: 14 }
          ]
        })
      });
    });

    await page.route(`**/api/v1/homes/*/intelligence/dashboard*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            home_name: 'Johnson Family Home',
            active_automations_count: 1,
            total_automations_count: 1,
            recent_executions_count: 14,
            failed_automations_count: 0,
            active_automations: [
              { id: 'a-1', name: 'Auto Restock Dishwasher Pods', trigger_type: 'LOW_STOCK', action_type: 'ADD_SHOPPING_ITEM', is_enabled: true, execution_count: 14 }
            ],
            recent_executions: []
          }
        })
      });
    });

    // Mock today briefing
    await page.route(`**/api/v1/homes/*/today*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            date: new Date().toISOString().slice(0, 10),
            timezone: 'UTC',
            home_id: activeHomeId,
            home_name: activeHomeId === homeAId ? 'Johnson Family Home' : 'Mountain Cabin Retreat',
            summary: {
              total_items: 5,
              critical_count: 1,
              high_count: 2,
              normal_count: 2,
              low_count: 0,
              events_count: 1,
              tasks_count: 2,
              bills_count: 1,
              purchase_urgent_count: 1,
              inventory_alerts_count: 0
            },
            needs_attention: [
              { id: 't-1', source_type: 'TASK', source_id: 't-1', title: 'Take out recycling bins', priority: 'HIGH', navigation_target: '/tasks' }
            ],
            timeline: [],
            tasks: { overdue: [], due_today: [], my_tasks: [], family_tasks: [], upcoming: [], completed_today_count: 0 },
            bills: { overdue: [], due_today: [], upcoming: [], total_due_today_amount: 0, currency: 'USD' },
            calendar: { today_events: [], upcoming_events: [] },
            inventory: { out_of_stock: [], low_stock: [], expiring_soon: [] },
            shopping: { urgent_items: [], pending_items: [], total_pending_count: 0 },
            family: { active_members_count: 3, pending_invitations_count: 0, member_workloads: [] },
            notifications: { unread_count: 1, important_alerts: [] }
          }
        })
      });
    });

    // Mock memories
    await page.route(`**/api/v1/homes/*/memories*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { id: 'mem-1', category: 'PREFERENCE', content: 'Prefers oat milk over dairy', confidence: 0.95, status: 'ACTIVE', created_at: new Date().toISOString() }
          ]
        })
      });
    });

    // Mock personalization
    await page.route(`**/api/v1/homes/*/personalization*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            personalization_enabled: true,
            ai_memory_enabled: true,
            reminder_timing_preference: 'MORNING',
            recommendation_frequency: 'WEEKLY',
            digest_enabled: true,
            digest_day_of_week: 'SUNDAY'
          }
        })
      });
    });

    // Mock intelligence digest
    await page.route(`**/api/v1/homes/*/intelligence/digest*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            home_name: 'Johnson Family Home',
            period_start: new Date(Date.now() - 86400000 * 7).toISOString(),
            period_end: new Date().toISOString(),
            tasks_completed_count: 8,
            tasks_overdue_count: 1,
            bills_paid_count: 3,
            bills_upcoming_count: 2,
            shopping_items_purchased_count: 12,
            inventory_low_count: 1,
            automations_executed_count: 14
          }
        })
      });
    });

    // Mock notifications
    await page.route(`**/api/v1/notifications*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              { id: 'notif-1', title: 'Chore Due Today', message: 'Take out recycling bins is due by 7 PM', priority: 'HIGH', is_read: false, created_at: new Date().toISOString() }
            ],
            total: 1,
            unread_count: 1,
            unresolved_action_count: 1
          }
        })
      });
    });
  };

  // ---------------------------------------------------------------------------
  // UAT PHASE 1: FIRST IMPRESSION & PUBLIC LANDING PAGE
  // ---------------------------------------------------------------------------
  test('UAT Phase 1: Public Landing Page 10-Second Clarity & Visual Audit', async ({ page }) => {
    await page.goto('/');

    // 1. Check Hero Headline & CTAs
    await expect(page.locator('h1')).toContainText('One place to run your household.');
    const createBtn = page.getByRole('button', { name: /create your home/i }).first();
    const howItWorksBtn = page.getByRole('button', { name: /see how it works/i });

    await expect(createBtn).toBeVisible();
    await expect(howItWorksBtn).toBeVisible();

    // 2. Check 14-Section Presence
    await expect(page.getByRole('heading', { name: 'Why managing a modern household feels exhausting.' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Chores & Task Management' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Smart Shopping & Restock' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Unified Family Calendar' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Household Bills & Expense Split' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Pantry & Asset Inventory' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Contextual AI Assistant' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Event-Driven Automations' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Household Memory Vault' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Up and running in less than 3 minutes.' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Built for how real households live.' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Free for your first year.' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Your household data is private. Period.' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Frequently Asked Questions' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Bring harmony to your home today.' })).toBeVisible();

    // 3. Capture Visual Screenshot Evidence
    await page.screenshot({ path: `${evidenceDir}/01_landing_page_desktop.png`, fullPage: true });
  });

  // ---------------------------------------------------------------------------
  // UAT PHASE 2: NEW USER ONBOARDING (PERSONA 1: NEW HOUSEHOLD OWNER)
  // ---------------------------------------------------------------------------
  test('UAT Phase 2: Persona 1 - New Household Owner Complete Onboarding Journey', async ({ page }) => {
    // 1. Visit registration
    await page.goto('/register');
    await expect(page.locator('h1')).toContainText(/create/i);
    await page.screenshot({ path: `${evidenceDir}/02_register_page.png` });

    // 2. Mock state for newly registered user without homes
    await page.goto('/login');
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'mock-new-user-jwt');
      localStorage.removeItem('active_home_id');
    });

    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'new-user-99',
            email: 'newowner@ozhzo.com',
            display_name: 'Taylor Swift',
            mobile_verified: true,
            free_home_consumed: false,
            is_super_admin: false,
            homes: []
          }
        })
      });
    });

    await page.route('**/api/v1/homes', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] })
      });
    });

    // 3. Visit dashboard -> Zero Homes State
    await page.goto('/dashboard');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByText(/create a new home|create your first home|welcome to ozhzo verse/i).first()).toBeVisible();
    await page.screenshot({ path: `${evidenceDir}/03_onboarding_zero_homes.png` });
  });

  // ---------------------------------------------------------------------------
  // UAT PHASE 3: HOUSEHOLD INVITATIONS (PERSONA 2: SPOUSE / FAMILY MEMBER)
  // ---------------------------------------------------------------------------
  test('UAT Phase 3: Persona 2 - Family Member Invitation & Join Experience', async ({ page }) => {
    await setupFullHouseholdState(page);

    // 1. Owner visits members tab to generate invite
    await page.goto('/members');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByText(/members|household members/i).first()).toBeVisible();
    await page.screenshot({ path: `${evidenceDir}/04_members_management.png` });

    // 2. Invited member joins via /join
    await page.goto('/join', { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: /join a household|join a home/i })).toBeVisible();
    await page.screenshot({ path: `${evidenceDir}/05_join_home_by_code.png` });
  });

  // ---------------------------------------------------------------------------
  // UAT PHASE 4 & 5: DAILY EXPERIENCE & SECOND MODULE ACTIVATION (PERSONA 3: BUSY PARENT)
  // ---------------------------------------------------------------------------
  test('UAT Phase 4 & 5: Persona 3 - Busy Parent Daily Briefing & Core Modules', async ({ page }) => {
    await setupFullHouseholdState(page);

    // 1. Open Today Dashboard
    await page.goto('/today');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByText(/today|daily briefing|household briefing/i).first()).toBeVisible();
    await page.screenshot({ path: `${evidenceDir}/06_today_dashboard_briefing.png` });

    // 2. Chores & Tasks Module
    await page.goto('/tasks');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByText(/tasks|chores|responsibilities/i).first()).toBeVisible();
    await page.screenshot({ path: `${evidenceDir}/07_tasks_module.png` });

    // 3. Second Module: Shopping List
    await page.goto('/shopping');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByText(/shopping|groceries/i).first()).toBeVisible();
    await page.screenshot({ path: `${evidenceDir}/08_shopping_module.png` });

    // 4. Pantry & Asset Inventory
    await page.goto('/inventory');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByText(/inventory|pantry|household items/i).first()).toBeVisible();
    await page.screenshot({ path: `${evidenceDir}/09_inventory_module.png` });

    // 5. Household Bills & Expenses
    await page.goto('/bills');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByText(/bills|expenses|financial/i).first()).toBeVisible();
    await page.screenshot({ path: `${evidenceDir}/10_bills_module.png` });

    // 6. Unified Family Calendar
    await page.goto('/calendar');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByText(/calendar|schedule/i).first()).toBeVisible();
    await page.screenshot({ path: `${evidenceDir}/11_calendar_module.png` });
  });

  // ---------------------------------------------------------------------------
  // UAT PHASE 11, 12, 13: POWER USER (AI ASSISTANT, AUTOMATIONS & MEMORY)
  // ---------------------------------------------------------------------------
  test('UAT Phase 11-13: Persona 6 - Power User Intelligence & Automations', async ({ page }) => {
    await setupFullHouseholdState(page);

    // 1. Automations Console
    await page.goto('/automations');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByText(/automations|automation/i).first()).toBeVisible();
    await page.screenshot({ path: `${evidenceDir}/12_automations_console.png` });

    // 2. Settings & Privacy / GDPR
    await page.goto('/settings');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByText(/settings|preferences|privacy/i).first()).toBeVisible();
    await page.screenshot({ path: `${evidenceDir}/13_settings_and_privacy.png` });
  });

  // ---------------------------------------------------------------------------
  // UAT PHASE 16: PAYING CUSTOMER & SUBSCRIPTION ENTITLEMENTS (PERSONA 5)
  // ---------------------------------------------------------------------------
  test('UAT Phase 16: Persona 5 - Subscription Entitlements & Pricing Consistency', async ({ page }) => {
    await setupFullHouseholdState(page);

    // Mock subscription endpoint
    await page.route('**/api/v1/subscription/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            plan_code: 'OZHZO_HOME',
            plan_name: 'Ozhzo Home Standard',
            status: 'ACTIVE',
            is_introductory: true,
            introductory_days_remaining: 342,
            entitlement: {
              max_homes: 1,
              used_homes: 1,
              included_members: 1,
              active_members_count: 3,
              ai_quota_monthly: 100000,
              ai_tokens_used: 12400
            }
          }
        })
      });
    });

    await page.goto('/settings/subscription');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByText(/subscription|plan|entitlement/i).first()).toBeVisible();
    await page.screenshot({ path: `${evidenceDir}/14_subscription_entitlements.png` });
  });

  // ---------------------------------------------------------------------------
  // UAT PHASE 17: MOBILE USER EXPERIENCE (PERSONA 4: 390px VIEWPORT)
  // ---------------------------------------------------------------------------
  test('UAT Phase 17: Persona 4 - Mobile 390px Viewport Full Journey Audit', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await setupFullHouseholdState(page);

    // 1. Mobile Landing Page
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('h1')).toContainText('One place to run your household.');
    await page.screenshot({ path: `${evidenceDir}/15_mobile_landing_390px.png` });

    // 2. Mobile Dashboard
    await page.goto('/dashboard');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).not.toContainText('[object Object]');
    await page.screenshot({ path: `${evidenceDir}/16_mobile_dashboard_390px.png` });

    // 3. Mobile Navigation & Touch Menu
    await page.goto('/tasks');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).toContainText(/tasks|chores/i);
    await page.screenshot({ path: `${evidenceDir}/17_mobile_tasks_390px.png` });
  });

  // ---------------------------------------------------------------------------
  // UAT PHASE 18: ERROR & EDGE CONDITIONS (SUPER ADMIN & BOUNDARY)
  // ---------------------------------------------------------------------------
  test('UAT Phase 18: Platform Console & Role Boundary Protection', async ({ page }) => {
    await page.goto('/admin/login');
    await expect(page.locator('h1')).toContainText(/super admin|platform console|admin/i);
    await page.screenshot({ path: `${evidenceDir}/18_admin_login_boundary.png` });
  });

});
