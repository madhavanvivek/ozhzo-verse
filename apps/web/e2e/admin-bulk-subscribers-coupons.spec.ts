import { test, expect } from '@playwright/test';

test.describe('Super Admin End-to-End Platform Integration Suite', () => {

  test.beforeEach(async ({ page, context }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await context.clearCookies();
  });

  test('1 & 2. Super Admin console displays Vivek in Users and Ichu\'s home in Workspaces', async ({ page }) => {
    await page.goto('/admin/login');
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'mock-super-admin-jwt');
    });

    // Mock Super Admin identity
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: '99999999-9999-9999-9999-999999999999',
            email: 'vivek@zinfog.com',
            display_name: 'Vivek',
            is_super_admin: true,
            system_role: 'SUPER_ADMIN',
            homes: [{ home_id: '77777777-7777-7777-7777-777777777777', name: "Ichu's home", role: 'OWNER', status: 'ACTIVE' }]
          }
        })
      });
    });

    // Mock /admin/users
    await page.route('**/api/v1/admin/users*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: '99999999-9999-9999-9999-999999999999',
              email: 'vivek@zinfog.com',
              display_name: 'Vivek',
              is_active: true,
              is_verified: true,
              mobile_verified: true,
              is_super_admin: true,
              system_role: 'SUPER_ADMIN',
              homes_count: 1,
              created_at: '2026-01-01T00:00:00Z'
            }
          ]
        })
      });
    });

    // Mock /admin/homes
    await page.route('**/api/v1/admin/homes*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: '77777777-7777-7777-7777-777777777777',
              name: "Ichu's home",
              status: 'ACTIVE',
              currency: 'USD',
              created_by_email: 'vivek@zinfog.com',
              created_by_name: 'Vivek',
              members_count: 2,
              subscription_status: 'ACTIVE',
              created_at: '2026-01-15T10:00:00Z'
            }
          ]
        })
      });
    });

    // Check Users
    await page.goto('/admin/users');
    await expect(page.getByText('vivek@zinfog.com').first()).toBeVisible();
    await expect(page.getByText('SUPER ADMIN').first()).toBeVisible();

    // Check Homes
    await page.goto('/admin/homes');
    await expect(page.getByText("Ichu's home").first()).toBeVisible();
    await expect(page.getByText('vivek@zinfog.com').first()).toBeVisible();
  });

  test('3. Admin dashboard displays live metrics from analytics endpoint', async ({ page }) => {
    await page.goto('/admin/login');
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'mock-super-admin-jwt');
    });

    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { id: 'admin-id', email: 'vivek@zinfog.com', is_super_admin: true, system_role: 'SUPER_ADMIN', homes: [] }
        })
      });
    });

    await page.route('**/api/v1/admin/system/analytics*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            total_users: 142,
            active_users: 135,
            suspended_users: 7,
            total_homes: 54,
            active_homes: 50,
            total_memberships: 120,
            active_subscriptions: 48,
            trialing_subscriptions: 12,
            paid_seats: 95
          }
        })
      });
    });

    await page.route('**/api/v1/admin/system/config', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { environment: 'production', debug_mode: false, log_level: 'INFO' }
        })
      });
    });

    await page.goto('/admin');
    await expect(page.getByText('Platform Overview')).toBeVisible();
    await expect(page.getByText('142').first()).toBeVisible();
    await expect(page.getByText('54').first()).toBeVisible();
  });

  test('4. Subscriptions page displays Active Subscribers tab with live records', async ({ page }) => {
    await page.goto('/admin/login');
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'mock-super-admin-jwt');
    });

    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { id: 'admin-id', email: 'vivek@zinfog.com', is_super_admin: true, system_role: 'SUPER_ADMIN', homes: [] }
        })
      });
    });

    await page.route('**/api/v1/admin/subscriptions/plans', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: [] }) });
    });
    await page.route('**/api/v1/admin/subscriptions/features', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: [] }) });
    });
    await page.route('**/api/v1/admin/subscriptions/promotions', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: [] }) });
    });

    // Mock subscribers
    await page.route('**/api/v1/admin/subscriptions/subscribers', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: 'sub-1111',
              home_id: '77777777-7777-7777-7777-777777777777',
              home_name: "Ichu's home",
              user_id: '99999999-9999-9999-9999-999999999999',
              user_name: 'Vivek',
              user_email: 'vivek@zinfog.com',
              plan_name: 'Ozhzo Home Standard',
              status: 'ACTIVE',
              coupon_code: 'MOSTWANTED',
              paid_seats: 2,
              start_date: '2026-01-01T00:00:00Z',
              renewal_date: '2027-01-01T00:00:00Z'
            }
          ]
        })
      });
    });

    await page.goto('/admin/subscriptions');
    await page.click('button:has-text("Active Subscribers")');
    await expect(page.getByText('Vivek').first()).toBeVisible();
    await expect(page.getByText("Ichu's home").first()).toBeVisible();
    await expect(page.getByText('MOSTWANTED').first()).toBeVisible();
  });

  test('5. Multi-select bulk actions bar activates on user selection', async ({ page }) => {
    await page.goto('/admin/login');
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'mock-super-admin-jwt');
    });

    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { id: 'admin-id', email: 'vivek@zinfog.com', is_super_admin: true, system_role: 'SUPER_ADMIN', homes: [] }
        })
      });
    });

    await page.route('**/api/v1/admin/users*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { id: 'u1', email: 'user1@example.com', display_name: 'User One', is_active: true, is_super_admin: false, system_role: 'USER', homes_count: 1, created_at: '2026-01-01T00:00:00Z' },
            { id: 'u2', email: 'user2@example.com', display_name: 'User Two', is_active: true, is_super_admin: false, system_role: 'USER', homes_count: 1, created_at: '2026-01-02T00:00:00Z' }
          ]
        })
      });
    });

    await page.goto('/admin/users');
    await expect(page.getByRole('table').getByText('User One')).toBeVisible();

    // Select All
    const selectAllCheckbox = page.getByRole('checkbox', { name: /Select all users/i });
    await selectAllCheckbox.click();

    // Verify Floating Bulk Action Bar
    await expect(page.getByText(/Selected 2 users/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /Suspend/i }).first()).toBeVisible();
    await expect(page.getByRole('button', { name: /Hold/i }).first()).toBeVisible();
  });

  test('6. Coupon creation captures redemption window and benefit duration', async ({ page }) => {
    await page.goto('/admin/login');
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'mock-super-admin-jwt');
      const user = {
        id: '99999999-9999-9999-9999-999999999999',
        email: 'vivek@zinfog.com',
        display_name: 'Vivek',
        is_super_admin: true,
        system_role: 'SUPER_ADMIN',
        homes: [{ home_id: '77777777-7777-7777-7777-777777777777', name: "Ichu's home", role: 'OWNER', status: 'ACTIVE' }]
      };
      localStorage.setItem('user', JSON.stringify(user));
    });

    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: '99999999-9999-9999-9999-999999999999',
            email: 'vivek@zinfog.com',
            display_name: 'Vivek',
            is_super_admin: true,
            system_role: 'SUPER_ADMIN',
            homes: [{ home_id: '77777777-7777-7777-7777-777777777777', name: "Ichu's home", role: 'OWNER', status: 'ACTIVE' }]
          }
        })
      });
    });

    await page.route('**/api/v1/homes**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] })
      });
    });

    await page.route('**/api/v1/admin/coupons/campaigns**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: [] }) });
    });
    await page.route('**/api/v1/admin/coupons/grants**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: [] }) });
    });
    await page.route('**/api/v1/admin/coupons/analytics**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: { total_coupons: 2, total_redemptions: 15 } }) });
    });
    await page.route('**/api/v1/admin/coupons**', async (route) => {
      const url = route.request().url();
      if (url.includes('/campaigns') || url.includes('/grants') || url.includes('/analytics')) {
        await route.fallback();
        return;
      }
      if (route.request().method() === 'GET') {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: [] }) });
      } else if (route.request().method() === 'POST') {
        const payload = JSON.parse(route.request().postData() || '{}');
        expect(payload.code).toBe('SUMMER2026');
        expect(payload.free_period_value).toBe(6);
        expect(payload.free_period_unit).toBe('MONTHS');
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: payload }) });
      }
    });

    await page.goto('/admin/coupons');
    await page.click('button:has-text("Create Coupon")');
    await expect(page.getByRole('heading', { name: 'Create New Coupon Code' })).toBeVisible();

    await page.fill('input[placeholder="WELCOME6M"]', 'SUMMER2026');
    await page.fill('input[placeholder="6 Months Free Early Adopter Access"]', 'Summer Launch 6M');
    await page.click('button[type="submit"]:has-text("Create Coupon")');
  });

});
