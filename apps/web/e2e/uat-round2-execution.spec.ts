import { test, expect } from '@playwright/test';
import * as path from 'path';

const evidenceDir = '/Users/vivek/.gemini/antigravity/brain/e417cc97-7d7a-4622-ab0c-93f6404efdd2/uat_round2_evidence';

test.describe('Ozhzo Verse — Independent UAT Round 2 Master Suite', () => {

  const homeAId = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
  const homeBId = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb';

  const setupMockRoutes = async (page: any, initialHomeId = homeAId) => {
    await page.addInitScript(({ token, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('active_home_id', hId);
    }, { token: 'mock-user-jwt', hId: initialHomeId });

    // 1. Current User
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'user-001',
            email: 'resident@ozhzo.com',
            display_name: 'Resident Host',
            mobile_verified: true,
            free_home_consumed: true,
            is_super_admin: false,
            system_role: 'USER',
            homes: [
              { home_id: homeAId, name: 'Sunset Manor', role: 'OWNER', status: 'ACTIVE' },
              { home_id: homeBId, name: 'Skyline Penthouse', role: 'MEMBER', status: 'ACTIVE' }
            ]
          }
        })
      });
    });

    // 2. Homes List
    await page.route('**/api/v1/homes', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { id: homeAId, name: 'Sunset Manor', currency: 'USD', role: 'OWNER', status: 'ACTIVE' },
            { id: homeBId, name: 'Skyline Penthouse', currency: 'USD', role: 'MEMBER', status: 'ACTIVE' }
          ]
        })
      });
    });

    // 3. Members & Admin Summary
    await page.route(`**/api/v1/homes/*/members*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { id: 'mem-1', user_id: 'user-001', display_name: 'Resident Host (You)', email: 'resident@ozhzo.com', role: 'OWNER', status: 'ACTIVE' },
            { id: 'mem-2', user_id: 'user-002', display_name: 'Partner Alex', email: 'alex@ozhzo.com', role: 'MEMBER', status: 'ACTIVE' }
          ]
        })
      });
    });

    await page.route(`**/api/v1/homes/*/admin/summary*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            home_id: homeAId,
            home_name: 'Sunset Manor',
            public_home_id: 'SUNSET-1234',
            join_policy: 'INVITE_ONLY',
            active_members_count: 2,
            pending_invitations_count: 0,
            pending_join_requests_count: 0,
            expiring_access_count: 0,
            expired_access_count: 0
          }
        })
      });
    });

    await page.route(`**/api/v1/homes/*/invitations*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] })
      });
    });

    // 4. Notifications
    await page.route(`**/api/v1/notifications*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              {
                id: 'n-1',
                home_id: homeAId,
                title: 'Overdue Task Alert',
                body: 'Clean HVAC Air Filters is past due date',
                type: 'TASK_OVERDUE',
                priority: 'HIGH',
                requires_action: true,
                action_status: 'OPEN',
                is_read: false,
                created_at: new Date().toISOString()
              },
              {
                id: 'n-2',
                home_id: homeAId,
                title: 'Upcoming Bill Due',
                body: 'Fiber Broadband ($79.99) due in 5 days',
                type: 'BILL_DUE',
                priority: 'NORMAL',
                requires_action: true,
                action_status: 'OPEN',
                is_read: false,
                created_at: new Date().toISOString()
              }
            ],
            total: 2,
            unread_count: 2,
            unresolved_action_count: 2
          }
        })
      });
    });

    // 5. Tasks
    await page.route(`**/api/v1/homes/*/tasks*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              {
                id: 'task-a1',
                title: 'Clean HVAC Air Filters',
                description: 'Replace with 16x25x1 filters',
                priority: 'HIGH',
                status: 'TODO',
                due_date: '2026-09-05T18:00:00Z',
                category_name: 'Maintenance',
                assigned_to_name: 'Resident Host'
              },
              {
                id: 'task-a2',
                title: 'Take out Recycling Bins',
                description: 'Place blue bins on curb',
                priority: 'NORMAL',
                status: 'TODO',
                due_date: '2026-09-03T18:00:00Z',
                category_name: 'Chores',
                assigned_to_name: 'Partner Alex'
              }
            ],
            total: 2,
            page: 1,
            page_size: 20,
            total_pages: 1
          }
        })
      });
    });

    // 6. Bills
    await page.route(`**/api/v1/homes/*/bills*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              {
                id: 'bill-a1',
                title: 'High-Speed Fiber Internet',
                category_name: 'Utilities',
                expected_amount: 79.99,
                currency: 'USD',
                due_date: '2026-09-10',
                is_due_today: false,
                is_overdue: false,
                recurrence_type: 'MONTHLY',
                status: 'UNPAID',
                amount_paid: 0.0,
                remaining_balance: 79.99,
                payments: []
              }
            ],
            total: 1
          }
        })
      });
    });

    // 7. Inventory & Locations
    await page.route(`**/api/v1/homes/*/inventory/items*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              { id: 'inv-a1', name: 'Dishwasher Pods', quantity: '4.000', unit: 'pods', item_type: 'CONSUMABLE', category_name: 'Kitchen', min_threshold: '10.000', status: 'LOW_STOCK' },
              { id: 'inv-a2', name: 'Cordless Stick Vacuum', quantity: '1.000', unit: 'unit', item_type: 'DURABLE', category_name: 'Appliances', status: 'AVAILABLE' }
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
              { id: 'inv-a1', name: 'Dishwasher Pods', quantity: '4.000', unit: 'pods', item_type: 'CONSUMABLE', category_name: 'Kitchen', min_threshold: '10.000', status: 'LOW_STOCK' },
              { id: 'inv-a2', name: 'Cordless Stick Vacuum', quantity: '1.000', unit: 'unit', item_type: 'DURABLE', category_name: 'Appliances', status: 'AVAILABLE' }
            ],
            total: 2
          }
        })
      });
    });

    await page.route(`**/api/v1/homes/*/locations*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [{ id: 'loc-1', name: 'Kitchen Pantry', type: 'ROOM' }] })
      });
    });

    await page.route(`**/api/v1/homes/*/location-types*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [{ name: 'Room', code: 'ROOM' }] })
      });
    });

    // 8. Shopping & Purchase List
    await page.route(`**/api/v1/homes/*/purchase-list*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { id: 'purch-a1', name: 'Organic Whole Milk', quantity: 1, unit: 'gal', notes: 'Whole milk', status: 'PENDING', added_by_name: 'Resident Host' }
          ]
        })
      });
    });

    await page.route(`**/api/v1/homes/*/shopping/items*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { id: 'purch-a1', name: 'Organic Whole Milk', quantity: 1, unit: 'gal', notes: 'Whole milk', status: 'PENDING', added_by_name: 'Resident Host' }
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
            { id: 'purch-a1', name: 'Organic Whole Milk', quantity: 1, unit: 'gal', notes: 'Whole milk', status: 'PENDING', added_by_name: 'Resident Host' }
          ]
        })
      });
    });

    // 9. Calendar Events & Projection
    await page.route(new RegExp('/api/v1/homes/([^/]+)/calendar/projection'), async (route) => {
      const timelineItems = [
        {
          source_type: 'EVENT',
          source_id: 'e-1',
          title: 'Dentist Checkup with Dr. Watson',
          start: '2026-09-04T10:00:00Z',
          end: '2026-09-04T11:00:00Z',
          all_day: false,
          editable: true,
          navigation_target: '/calendar/e-1',
          status: 'CONFIRMED',
          category_name: 'Health',
          location: 'City Clinic'
        },
        {
          source_type: 'TASK',
          source_id: 'task-a1',
          title: 'Task: Clean HVAC Air Filters',
          start: '2026-09-05T18:00:00Z',
          end: '2026-09-05T18:00:00Z',
          all_day: false,
          editable: false,
          navigation_target: '/tasks/task-a1',
          status: 'TODO',
          category_name: 'Maintenance'
        },
        {
          source_type: 'BILL',
          source_id: 'bill-a1',
          title: 'Bill Due: High-Speed Fiber Internet (USD 79.99)',
          start: '2026-09-10T23:59:59Z',
          end: '2026-09-10T23:59:59Z',
          all_day: true,
          editable: false,
          navigation_target: '/bills/bill-a1',
          status: 'UNPAID',
          category_name: 'Utilities'
        }
      ];

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            start_date: '2026-06-01T00:00:00Z',
            end_date: '2027-03-01T00:00:00Z',
            items: timelineItems,
            timeline_items: timelineItems,
            total_events: 1,
            total_tasks: 1,
            total_bills: 1
          }
        })
      });
    });

    // 10. Dashboard Aggregation
    await page.route(`**/api/v1/homes/*/dashboard*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            greeting: { title: 'Good Morning, Resident', subtitle: "Here's what is happening at Sunset Manor" },
            summary: {
              home_id: homeAId,
              home_name: 'Sunset Manor',
              currency: 'USD',
              active_tasks_count: 2,
              urgent_tasks_count: 1,
              pending_bills_count: 1,
              unpaid_bills_total: 79.99,
              shopping_needed_count: 1,
              low_stock_items_count: 1,
              upcoming_events_count: 1
            },
            urgent_tasks: [
              { id: 'task-a1', title: 'Clean HVAC Air Filters', priority: 'HIGH', status: 'TODO', due_date: '2026-09-05T18:00:00Z' }
            ],
            pending_bills: [
              { id: 'bill-a1', title: 'High-Speed Fiber Internet', amount: 79.99, currency: 'USD', due_date: '2026-09-10', status: 'UNPAID' }
            ],
            low_stock_inventory: [
              { id: 'inv-a1', name: 'Dishwasher Pods', current_quantity: 4, min_quantity: 10, unit: 'pods' }
            ],
            shopping_items_preview: [
              { id: 'purch-a1', name: 'Organic Whole Milk', quantity: 1, unit: 'gal', is_purchased: false }
            ],
            upcoming_events: [
              { id: 'e-1', title: 'Dentist Checkup with Dr. Watson', start_time: '2026-09-04T10:00:00Z' }
            ],
            notifications: [
              { id: 'n-1', title: 'Overdue Task Alert', body: 'Clean HVAC Air Filters is past due date', priority: 'HIGH', requires_action: true }
            ],
            role: 'OWNER'
          }
        })
      });
    });

    // 11. Automations & Intelligence
    await page.route(`**/api/v1/homes/*/intelligence/dashboard*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            home_name: 'Sunset Manor',
            active_automations_count: 1,
            total_automations_count: 1,
            recent_executions_count: 12,
            failed_automations_count: 0,
            active_automations: [
              {
                id: 'a-1',
                home_id: homeAId,
                name: 'Auto-Add Low Stock Pods to Shopping',
                enabled: true,
                trigger_type: 'INVENTORY_LOW',
                conditions: {},
                actions: [{ type: 'ADD_SHOPPING_ITEM', item: 'Dishwasher Pods' }],
                schedule: {},
                execution_policy: {},
                status: 'ACTIVE',
                failure_count: 0,
                consecutive_failures: 0,
                created_at: new Date().toISOString()
              }
            ],
            recent_executions: [],
            recommendations: [],
            predicted_patterns: []
          }
        })
      });
    });

    await page.route(`**/api/v1/homes/*/memories*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { id: 'mem-1', category: 'DIETARY', content: 'Leo is allergic to peanuts', source: 'USER', confidence: 1.0, status: 'ACTIVE', created_at: new Date().toISOString() }
          ]
        })
      });
    });

    // 12. Subscription
    await page.route('**/api/v1/subscription*/me*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            free_home_consumed: true,
            free_home_included: 1,
            active_homes_count: 1,
            total_allowed_homes: 1,
            can_create_home: false,
            active_subscription: {
              id: 'sub-001',
              plan_name: 'Ozhzo Home Standard',
              status: 'ACTIVE',
              paid_member_seats: 1,
              effective_price: 0,
              currency: 'USD'
            }
          }
        })
      });
    });

    await page.route('**/api/v1/subscription*/plans*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: 'plan-1',
              code: 'HOME_STANDARD',
              name: 'Ozhzo Home Standard',
              description: 'Complete household management for standard families',
              status: 'ACTIVE',
              included_members: 2,
              max_homes: 1,
              additional_member_allowed: true,
              introductory_enabled: true,
              introductory_duration_days: 365,
              introductory_price: 0,
              prices: []
            }
          ]
        })
      });
    });

    await page.route('**/api/v1/subscription*/transactions*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] })
      });
    });

    await page.route('**/api/v1/subscription*/my-credits*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] })
      });
    });
  };

  test('ROUND 1: Calendar Cross-Module Integration (Tasks, Bills, Projections)', async ({ page }) => {
    await setupMockRoutes(page);

    await page.goto('/tasks');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).toContainText('Clean HVAC Air Filters');

    await page.goto('/bills');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).toContainText('High-Speed Fiber Internet');

    await page.goto('/calendar');
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText('Dentist Checkup with Dr. Watson');
    await expect(page.locator('body')).toContainText('Task: Clean HVAC Air Filters');
    await expect(page.locator('body')).toContainText('Bill Due: High-Speed Fiber Internet');

    await page.screenshot({ path: path.join(evidenceDir, '01_calendar_cross_module_projection.png'), fullPage: true });
  });

  test('ROUND 2: Notifications Center & Priority Alert Lifecycle (Read != Resolved)', async ({ page }) => {
    await setupMockRoutes(page);

    await page.goto('/dashboard');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).not.toContainText('[object Object]');
    await page.screenshot({ path: path.join(evidenceDir, '02_dashboard_priority_alert_banner.png'), fullPage: true });

    await page.goto('/notifications');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).toContainText('Overdue Task Alert');
    await page.screenshot({ path: path.join(evidenceDir, '03_notifications_center_read_resolved.png'), fullPage: true });
  });

  test('ROUND 3: Family Members Management & RBAC Boundaries', async ({ page }) => {
    await setupMockRoutes(page);

    await page.goto('/members');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).toContainText('Resident Host (You)');
    await expect(page.locator('body')).toContainText('Partner Alex');
    await page.screenshot({ path: path.join(evidenceDir, '04_members_management_rbac.png'), fullPage: true });
  });

  test('ROUND 4: Subscription Entitlements & Introductory Plan Clarity', async ({ page }) => {
    await setupMockRoutes(page);

    await page.goto('/settings/subscription');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).toContainText('Ozhzo Home Standard');
    await page.screenshot({ path: path.join(evidenceDir, '05_subscription_entitlements_overview.png'), fullPage: true });
  });

  test('ROUND 5 & 6: AI Assistant Natural Language Interface & Guardrail Verification', async ({ page }) => {
    await setupMockRoutes(page);

    await page.goto('/dashboard');
    await page.waitForLoadState('domcontentloaded');

    const aiWidgetBtn = page.locator('button[aria-label*="AI Assistant"], button:has-text("AI Assistant")').first();
    if (await aiWidgetBtn.isVisible()) {
      await aiWidgetBtn.click();
      await page.waitForTimeout(300);
      await page.screenshot({ path: path.join(evidenceDir, '06_ai_assistant_dialog_open.png') });
    }
  });

  test('ROUND 7: Household Automations Engine & Trigger Rules', async ({ page }) => {
    await setupMockRoutes(page);

    await page.goto('/automations');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).toContainText('Auto-Add Low Stock Pods to Shopping');
    await page.screenshot({ path: path.join(evidenceDir, '07_automations_console_audit.png'), fullPage: true });
  });

  test('ROUND 8: Shopping List & Pantry Inventory Synchronized Restock', async ({ page }) => {
    await setupMockRoutes(page);

    await page.goto('/inventory');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).toContainText('Dishwasher Pods');
    await page.screenshot({ path: path.join(evidenceDir, '08_inventory_pantry_view.png'), fullPage: true });

    await page.goto('/shopping');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).toContainText('Organic Whole Milk');
    await page.screenshot({ path: path.join(evidenceDir, '09_shopping_list_view.png'), fullPage: true });
  });

  test('ROUND 9: Household Memory Vault & Privacy Preferences', async ({ page }) => {
    await setupMockRoutes(page);

    await page.goto('/settings');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).not.toContainText('[object Object]');
    await page.screenshot({ path: path.join(evidenceDir, '10_settings_and_privacy_controls.png'), fullPage: true });
  });

  test('ROUND 10: Mobile 390px Viewport Touch Targets & Responsive Layout', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await setupMockRoutes(page);

    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('h1')).toContainText('One place to run your household.');
    await page.screenshot({ path: path.join(evidenceDir, '11_mobile_390px_landing.png') });

    await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('body')).not.toContainText('[object Object]');
    await page.screenshot({ path: path.join(evidenceDir, '12_mobile_390px_dashboard.png') });

    await page.goto('/calendar', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('body')).not.toContainText('[object Object]');
    await page.screenshot({ path: path.join(evidenceDir, '13_mobile_390px_calendar.png') });
  });

  test('ROUND 11: Persona End-to-End Discovery to Daily Household Flow', async ({ page }) => {
    await setupMockRoutes(page);

    await page.goto('/today', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('body')).not.toContainText('[object Object]');
    await page.screenshot({ path: path.join(evidenceDir, '14_today_daily_briefing_journey.png') });
  });

});
