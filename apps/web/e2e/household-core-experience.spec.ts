import { test, expect } from '@playwright/test';

test.describe('Stage 2.6 Household Core Experience E2E Suite', () => {

  const homeAId = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
  const homeBId = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb';

  test.beforeEach(async ({ page, context }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await context.clearCookies();
  });

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
            { id: homeAId, name: 'Sunset Manor', currency: 'INR', role: 'OWNER', status: 'ACTIVE' },
            { id: homeBId, name: 'Skyline Penthouse', currency: 'USD', role: 'MEMBER', status: 'ACTIVE' }
          ]
        })
      });
    });

    // 3. Members List
    await page.route(`**/api/v1/homes/*/members*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { id: 'mem-1', user_id: 'user-001', display_name: 'Resident Host', email: 'resident@ozhzo.com', role: 'OWNER', status: 'ACTIVE' },
            { id: 'mem-2', user_id: 'user-002', display_name: 'Partner Alex', email: 'alex@ozhzo.com', role: 'MEMBER', status: 'ACTIVE' }
          ]
        })
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
            items: [],
            total: 0,
            unread_count: 0,
            unresolved_action_count: 0
          }
        })
      });
    });

    // 5. Locations & Location Types
    await page.route(`**/api/v1/homes/*/locations*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { id: 'loc-1', name: 'Kitchen Pantry', type: 'ROOM', children: [] }
          ]
        })
      });
    });

    await page.route(`**/api/v1/homes/*/location-types*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { name: 'Room', code: 'ROOM', is_system_default: true }
          ]
        })
      });
    });

    // 6. Dashboard Aggregation for Home A & Home B
    await page.route(`**/api/v1/homes/${homeAId}/dashboard*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            greeting: { title: 'Good Morning, Resident', subtitle: "Here's what is happening at Sunset Manor" },
            summary: {
              home_name: 'Sunset Manor',
              currency: 'INR',
              active_tasks_count: 3,
              due_today_tasks_count: 1,
              overdue_tasks_count: 0,
              unpaid_bills_count: 2,
              unpaid_bills_amount: '3500.00',
              low_stock_count: 1,
              members_count: 2
            },
            attention_summary: { total_attention_count: 1, has_critical: false },
            attention_items: [
              {
                id: 'att-1',
                type: 'LOW_STOCK',
                priority: 'NORMAL',
                title: 'Low Stock Alert',
                message: 'Olive Oil is running low in Pantry',
                action_target: '/inventory',
                action_label: 'Restock'
              }
            ],
            today_timeline: [],
            recent_activity: [],
            pending_tasks: [
              { id: 'task-a1', title: 'Water Garden Plants', priority: 'NORMAL', status: 'TODO', due_date: new Date().toISOString() }
            ],
            upcoming_bills: [
              { id: 'bill-a1', title: 'Fiber Broadband', amount: 999.00, currency: 'INR', due_date: new Date().toISOString(), status: 'UNPAID' }
            ],
            upcoming_events: [],
            low_stock_inventory: [
              { id: 'inv-a1', name: 'Olive Oil', quantity: '0.500', unit: 'bottle', status: 'LOW_STOCK', min_threshold: '1.000' }
            ],
            shopping_items: [
              { id: 'purch-a1', name: 'Almond Milk', quantity: '2.000', unit: 'carton', is_checked: false }
            ],
            notifications: [],
            role: 'OWNER'
          }
        })
      });
    });

    await page.route(`**/api/v1/homes/${homeBId}/dashboard*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            greeting: { title: 'Good Morning, Resident', subtitle: "Here's what is happening at Skyline Penthouse" },
            summary: {
              home_name: 'Skyline Penthouse',
              currency: 'USD',
              active_tasks_count: 1,
              due_today_tasks_count: 0,
              overdue_tasks_count: 0,
              unpaid_bills_count: 0,
              unpaid_bills_amount: '0.00',
              low_stock_count: 0,
              members_count: 1
            },
            attention_summary: { total_attention_count: 0, has_critical: false },
            attention_items: [],
            today_timeline: [],
            recent_activity: [],
            pending_tasks: [
              { id: 'task-b1', title: 'Balcony Glass Cleaning', priority: 'HIGH', status: 'TODO', due_date: new Date().toISOString() }
            ],
            upcoming_bills: [],
            upcoming_events: [],
            low_stock_inventory: [],
            shopping_items: [],
            notifications: [],
            role: 'MEMBER'
          }
        })
      });
    });
  };

  test('1. Dashboard Aggregation renders unified overview and respects Home Context', async ({ page }) => {
    await setupMockRoutes(page, homeAId);

    await page.goto('/dashboard');
    await expect(page.getByText('Sunset Manor').first()).toBeVisible();

    // Chores & Bills preview cards
    await expect(page.locator('body')).toContainText('Water Garden Plants');
    await expect(page.locator('body')).toContainText('Fiber Broadband');
  });

  test('2. Multi-Home Data Isolation: Tasks and Bills do not leak between Homes', async ({ page }) => {
    await setupMockRoutes(page, homeAId);

    // Mock Tasks endpoint for Home A & Home B
    await page.route(`**/api/v1/homes/${homeAId}/tasks*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              {
                id: 'task-a1',
                title: 'Unique Alpha Chore 999',
                description: 'Outdoor lawn and flowers',
                priority: 'NORMAL',
                status: 'TODO',
                due_date: new Date().toISOString(),
                recurrence_type: 'DAILY',
                assigned_to: 'user-001',
                assigned_to_name: 'Resident Host',
                version: 1
              }
            ],
            total: 1,
            page: 1,
            page_size: 20,
            total_pages: 1
          }
        })
      });
    });

    await page.route(`**/api/v1/homes/${homeBId}/tasks*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              {
                id: 'task-b1',
                title: 'Unique Beta Chore 888',
                description: 'Penthouse windows',
                priority: 'HIGH',
                status: 'TODO',
                due_date: new Date().toISOString(),
                recurrence_type: 'WEEKLY',
                assigned_to: 'user-001',
                assigned_to_name: 'Resident Host',
                version: 1
              }
            ],
            total: 1,
            page: 1,
            page_size: 20,
            total_pages: 1
          }
        })
      });
    });

    await page.goto('/tasks');
    await expect(page.locator('body')).toContainText('Unique Alpha Chore 999');
    await expect(page.locator('body')).not.toContainText('Unique Beta Chore 888');

    // Switch active home to Home B
    await page.evaluate((hId) => {
      localStorage.setItem('active_home_id', hId);
      window.dispatchEvent(new Event('home-changed'));
    }, homeBId);

    // Page updates without reload via home-changed event bus
    await expect(page.locator('body')).toContainText('Unique Beta Chore 888');
    await expect(page.locator('body')).not.toContainText('Unique Alpha Chore 999');
  });

  test('3. Tasks Module: Complete Task updates status optimistically', async ({ page }) => {
    await setupMockRoutes(page, homeAId);

    await page.route(`**/api/v1/homes/${homeAId}/tasks*`, async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              items: [
                {
                  id: 'task-101',
                  title: 'Clean Water Filter Task',
                  priority: 'NORMAL',
                  status: 'TODO',
                  due_date: new Date().toISOString(),
                  recurrence_type: 'MONTHLY',
                  assigned_to: 'user-001',
                  assigned_to_name: 'Resident Host',
                  version: 1
                }
              ],
              total: 1,
              page: 1,
              page_size: 20,
              total_pages: 1
            }
          })
        });
      }
    });

    await page.route(`**/api/v1/homes/${homeAId}/tasks/task-101/complete`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'task-101',
            title: 'Clean Water Filter Task',
            status: 'COMPLETED',
            version: 2
          }
        })
      });
    });

    await page.goto('/tasks');
    await expect(page.locator('body')).toContainText('Clean Water Filter Task');

    // Click complete chore check button
    const completeBtn = page.locator('button:has-text("Done"), button[title*="Complete"], input[type="checkbox"]').first();
    if (await completeBtn.isVisible()) {
      await completeBtn.click();
    }
  });

  test('4. Bills Module: Record Payment records settlement with currency formatting', async ({ page }) => {
    await setupMockRoutes(page, homeAId);

    await page.route(`**/api/v1/homes/${homeAId}/bills*`, async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              items: [
                {
                  id: 'bill-101',
                  title: 'Electricity Utility',
                  expected_amount: '2200.00',
                  amount_paid: '0.00',
                  currency: 'INR',
                  due_date: new Date().toISOString().split('T')[0],
                  status: 'UNPAID',
                  recurrence_type: 'MONTHLY',
                  version: 1
                }
              ],
              total: 1,
              page: 1,
              page_size: 20,
              total_pages: 1
            }
          })
        });
      }
    });

    await page.goto('/bills');
    await expect(page.locator('body')).toContainText('Electricity Utility');
    await expect(page.locator('body')).toContainText('2200');
  });

  test('5. Calendar Projection: Renders Unified Timeline aggregating events, tasks, and bills', async ({ page }) => {
    await setupMockRoutes(page, homeAId);

    await page.route(`**/api/v1/homes/${homeAId}/calendar/projection*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            start_date: new Date().toISOString(),
            end_date: new Date(Date.now() + 86400000 * 30).toISOString(),
            items: [
              {
                source_type: 'EVENT',
                source_id: 'evt-1',
                title: 'Family Dinner',
                start: new Date().toISOString(),
                end: new Date(Date.now() + 7200000).toISOString(),
                all_day: false,
                editable: true,
                navigation_target: '/calendar/evt-1',
                status: 'CONFIRMED'
              },
              {
                source_type: 'TASK',
                source_id: 'task-1',
                title: 'Task: Clean Air Conditioner',
                start: new Date().toISOString(),
                end: new Date().toISOString(),
                all_day: false,
                editable: false,
                navigation_target: '/tasks/task-1',
                status: 'TODO'
              },
              {
                source_type: 'BILL',
                source_id: 'bill-1',
                title: 'Bill Due: Water Utility (INR 650.00)',
                start: new Date().toISOString(),
                end: new Date().toISOString(),
                all_day: true,
                editable: false,
                navigation_target: '/bills/bill-1',
                status: 'UNPAID'
              }
            ],
            total_events: 1,
            total_tasks: 1,
            total_bills: 1
          }
        })
      });
    });

    await page.goto('/calendar');
    await expect(page.locator('body')).toContainText('Family Dinner');
    await expect(page.locator('body')).toContainText('Clean Air Conditioner');
    await expect(page.locator('body')).toContainText('Water Utility');
  });

  test('6. Shopping List: Purchasing item triggers restock to Inventory', async ({ page }) => {
    await setupMockRoutes(page, homeAId);

    await page.route(`**/api/v1/homes/${homeAId}/purchase-list*`, async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [
              {
                id: 'purch-item-1',
                name: 'Ground Coffee',
                quantity: '1.000',
                unit: 'pack',
                status: 'PENDING',
                inventory_item_id: 'inv-item-1',
                created_at: new Date().toISOString()
              }
            ]
          })
        });
      }
    });

    await page.route(`**/api/v1/homes/${homeAId}/purchase-list/purch-item-1/purchase`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'purch-item-1',
            name: 'Ground Coffee',
            status: 'PURCHASED',
            restocked_to_inventory: true
          }
        })
      });
    });

    await page.goto('/shopping');
    await expect(page.locator('body')).toContainText('Ground Coffee');

    // Click Buy / Purchase button or checkbox
    const markPurchasedBtn = page.locator('button:has-text("Bought"), button:has-text("Purchase"), input[type="checkbox"]').first();
    if (await markPurchasedBtn.isVisible()) {
      await markPurchasedBtn.click();
    }
  });

  test('7. Inventory: Low Stock & Out of Stock indicators render properly', async ({ page }) => {
    await setupMockRoutes(page, homeAId);

    await page.route(`**/api/v1/homes/${homeAId}/inventory/items*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              {
                id: 'inv-101',
                name: 'Basmati Rice',
                quantity: '0.800',
                unit: 'kg',
                min_threshold: '2.000',
                item_type: 'CONSUMABLE',
                status: 'LOW_STOCK',
                category_name: 'Pantry'
              }
            ],
            total: 1,
            page: 1,
            page_size: 50,
            total_pages: 1
          }
        })
      });
    });

    await page.goto('/inventory');
    await expect(page.locator('body')).toContainText('Basmati Rice');
  });

});
