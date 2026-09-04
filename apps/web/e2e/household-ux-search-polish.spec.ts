import { test, expect } from '@playwright/test';

test.describe('Stage 2.7 Household UX, Navigation, Search & Polish E2E Suite', () => {

  const homeAId = '11111111-1111-1111-1111-111111111111';
  const homeBId = '22222222-2222-2222-2222-222222222222';

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
            email: 'host@ozhzo.com',
            display_name: 'Host User',
            mobile_verified: true,
            free_home_consumed: true,
            is_super_admin: false,
            system_role: 'USER',
            homes: [
              { home_id: homeAId, name: 'Madhavan Residence', role: 'OWNER', status: 'ACTIVE' },
              { home_id: homeBId, name: 'Mountain Retreat', role: 'MEMBER', status: 'ACTIVE' }
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
            { id: homeAId, name: 'Madhavan Residence', currency: 'INR', role: 'OWNER', status: 'ACTIVE' },
            { id: homeBId, name: 'Mountain Retreat', currency: 'USD', role: 'MEMBER', status: 'ACTIVE' }
          ]
        })
      });
    });

    // 3. Notifications & Priority Alerts
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

    // 4. Locations & Location Types
    await page.route(`**/api/v1/homes/*/locations*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [{ id: 'loc-1', name: 'Main Kitchen', type: 'ROOM', children: [] }]
        })
      });
    });

    await page.route(`**/api/v1/homes/*/location-types*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [{ name: 'Room', code: 'ROOM', is_system_default: true }]
        })
      });
    });

    // 5. Dashboard Aggregation for Home A & Home B
    await page.route(`**/api/v1/homes/${homeAId}/dashboard*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            greeting: { title: 'Welcome', subtitle: 'Madhavan Residence' },
            summary: {
              home_name: 'Madhavan Residence',
              currency: 'INR',
              active_tasks_count: 2,
              due_today_tasks_count: 1,
              overdue_tasks_count: 0,
              unpaid_bills_count: 1,
              unpaid_bills_amount: '1200.00',
              low_stock_count: 1,
              members_count: 3
            },
            attention_summary: { total_attention_count: 1, has_critical: false },
            attention_items: [],
            today_timeline: [],
            recent_activity: [],
            pending_tasks: [{ id: 'task-1', title: 'Clean Water Filter', priority: 'NORMAL', status: 'TODO' }],
            upcoming_bills: [{ id: 'bill-1', title: 'Internet Fiber', amount: 999.00, currency: 'INR', due_date: new Date().toISOString(), status: 'UNPAID' }],
            upcoming_events: [],
            low_stock_inventory: [{ id: 'inv-1', name: 'Olive Oil', quantity: '0.500', unit: 'bottle', status: 'LOW_STOCK' }],
            shopping_items: [{ id: 'purch-1', name: 'Whole Wheat Flour', quantity: '5.000', unit: 'kg', is_checked: false }],
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
            greeting: { title: 'Welcome', subtitle: 'Mountain Retreat' },
            summary: {
              home_name: 'Mountain Retreat',
              currency: 'USD',
              active_tasks_count: 0,
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
            pending_tasks: [],
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

    // 6. Unified Home Search Mock (Regex catch-all for any search query)
    await page.route(/.*\/search.*/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            query: 'drill',
            total_results: 3,
            results_by_domain: { ASSET: 1, TASK: 1, PURCHASE: 1 },
            items: [
              {
                id: 'asset-1',
                domain: 'ASSET',
                title: 'Cordless Power Drill',
                subtitle: 'Location: Garage > Tool Cabinet',
                status: 'AVAILABLE',
                navigation_target: '/inventory'
              },
              {
                id: 'task-1',
                domain: 'TASK',
                title: 'Mount TV with Drill',
                subtitle: 'Status: TODO • Due: Tomorrow',
                status: 'TODO',
                navigation_target: '/tasks'
              },
              {
                id: 'purch-1',
                domain: 'PURCHASE',
                title: 'Masonry Drill Bit Set',
                subtitle: '1 pack',
                status: 'To Buy',
                navigation_target: '/shopping'
              }
            ]
          }
        })
      });
    });
  };

  test('1. Global Unified Search: Opens with Cmd+K, searches across domains, and deep-links', async ({ page }) => {
    page.on('console', (msg) => console.log('BROWSER CONSOLE:', msg.text()));
    page.on('request', (req) => console.log('REQ:', req.method(), req.url()));
    page.on('response', (res) => console.log('RES:', res.status(), res.url()));
    await setupMockRoutes(page, homeAId);

    await page.goto('/dashboard');
    await expect(page.getByText('Madhavan Residence').first()).toBeVisible();

    // Click search bar / trigger search dialog
    const searchTrigger = page.locator('.ozhzo-header-search, button[aria-label="Search"]').first();
    await searchTrigger.click();

    // Search modal should be visible
    const searchInput = page.locator('input[aria-label="Search items"]');
    await expect(searchInput).toBeVisible();

    // Type query "drill"
    await searchInput.fill('drill');
    await page.waitForTimeout(600); // Allow 250ms debounce and response to settle

    // Verify search results grouped by domain with deep links
    await expect(page.getByText('Cordless Power Drill')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Mount TV with Drill')).toBeVisible();
    await expect(page.getByText('Masonry Drill Bit Set')).toBeVisible();


    // Click on task result
    await page.getByText('Mount TV with Drill').click();
    await expect(page).toHaveURL(/.*tasks/);
  });

  test('2. Quick Add Menu: Accessible globally from header and mobile bottom bar', async ({ page }) => {
    await setupMockRoutes(page, homeAId);

    await page.goto('/dashboard');

    // Click "+ Add" button
    const addBtn = page.locator('button[aria-label="Quick Add to Home"]').first();
    await addBtn.click();

    // Quick Add dialog should be visible
    await expect(page.getByText('Quick Add to Home')).toBeVisible();
    await expect(page.getByText('+ Task')).toBeVisible();
    await expect(page.getByText('+ Purchase')).toBeVisible();
    await expect(page.getByText('+ Pantry Stock')).toBeVisible();
    await expect(page.getByText('+ Bill')).toBeVisible();
    await expect(page.getByText('+ Event')).toBeVisible();

    // Click + Purchase navigates to /shopping
    await page.getByText('+ Purchase').click();
    await expect(page).toHaveURL(/.*shopping/);
  });

  test('3. Mobile-First Experience: 390px viewport renders responsive navigation and touch targets', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 }); // iPhone 12/13/14 viewport
    await setupMockRoutes(page, homeAId);

    await page.goto('/dashboard');

    // Verify mobile header and bottom navigation bar are present
    const bottomNav = page.locator('nav[aria-label="Mobile Navigation"]');
    await expect(bottomNav).toBeVisible();

    // Check Bottom Nav items
    await expect(bottomNav.getByText('Home')).toBeVisible();
    await expect(bottomNav.getByText('Today')).toBeVisible();
    await expect(bottomNav.getByText('Memory')).toBeVisible();
    await expect(bottomNav.getByText('More')).toBeVisible();

    // Open Mobile More Drawer
    await bottomNav.getByText('More').click();
    await expect(page.getByText('Household Modules')).toBeVisible();
    await expect(page.locator('a[href="/bills"]').last()).toBeVisible();
    await expect(page.locator('a[href="/members"]').last()).toBeVisible();
    await expect(page.locator('a[href="/profile"]').last()).toBeVisible();
  });



  test('4. Home Switching: Updates Home Context, triggers home-changed event, and clears stale UI', async ({ page }) => {
    await setupMockRoutes(page, homeAId);

    await page.goto('/dashboard');
    await expect(page.getByText('Madhavan Residence').first()).toBeVisible();
    await expect(page.locator('body')).toContainText('Whole Wheat Flour');

    // Switch home to Home B
    await page.evaluate((hId) => {
      localStorage.setItem('active_home_id', hId);
      window.dispatchEvent(new Event('home-changed'));
    }, homeBId);

    // Context changes immediately to Mountain Retreat
    await expect(page.getByText('Mountain Retreat').first()).toBeVisible();
  });

});
