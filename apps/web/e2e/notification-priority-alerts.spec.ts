import { test, expect } from '@playwright/test';

test.describe('Stage 2.5 Notification & Priority Alert Intelligence E2E Suite', () => {

  test.beforeEach(async ({ page, context }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await context.clearCookies();
  });

  test('1. Priority Alert Banner renders on /dashboard and deep-links to Action', async ({ page }) => {
    const homeId = '22222222-2222-2222-2222-222222222222';

    await page.addInitScript(({ token, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('active_home_id', hId);
    }, { token: 'mock-user-jwt', hId: homeId });

    // Mock /users/me
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'user-notif-01',
            email: 'notifuser@ozhzo.com',
            display_name: 'Alert User',
            mobile_verified: true,
            free_home_consumed: true,
            is_super_admin: false,
            system_role: 'USER',
            homes: [{ home_id: homeId, name: "Sunset Manor", role: 'OWNER', status: 'ACTIVE' }]
          }
        })
      });
    });

    // Mock /homes
    await page.route('**/api/v1/homes', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [{ id: homeId, name: 'Sunset Manor', currency: 'USD', role: 'OWNER', status: 'ACTIVE' }]
        })
      });
    });

    // Mock /homes/{homeId}/dashboard
    await page.route(`**/api/v1/homes/${homeId}/dashboard`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            greeting: {
              greeting: 'Good afternoon',
              user_display_name: 'Alert User',
              date_formatted: 'Tuesday, Sep 1',
              time_period: 'afternoon'
            },
            summary: {
              home_id: homeId,
              home_name: 'Sunset Manor',
              currency: 'USD',
              timezone: 'UTC',
              members_count: 1,
              active_tasks_count: 0,
              low_stock_count: 0,
              unpaid_bills_count: 0,
              unpaid_bills_sum: 0,
              upcoming_events_count: 0,
              unread_notifications_count: 1
            },
            pending_tasks: [],
            upcoming_bills: [],
            upcoming_events: [],
            low_stock_inventory: [],
            shopping_items: [],
            notifications: [],
            role: 'OWNER'
          }
        })
      });
    });

    // Consolidated Mock for /notifications
    await page.route('**/api/v1/notifications**', async (route) => {
      const url = route.request().url();
      if (url.includes('/priority')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              action_required_count: 1,
              critical_count: 1,
              high_count: 0,
              unread_count: 1,
              items: [
                {
                  id: 'n-crit-1',
                  home_id: homeId,
                  home_name: 'Sunset Manor',
                  user_id: 'user-notif-01',
                  title: 'Subscription Expired',
                  body: 'Your access to Sunset Manor has expired. Renew to continue.',
                  type: 'SUBSCRIPTION_EXPIRED',
                  priority: 'CRITICAL',
                  requires_action: true,
                  action_status: 'OPEN',
                  action_type: 'RENEW',
                  action_url: '/settings/subscription',
                  action_label: 'Renew Now',
                  is_read: false,
                  created_at: new Date().toISOString()
                }
              ]
            }
          })
        });
      }

      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              {
                id: 'n-crit-1',
                home_id: homeId,
                home_name: 'Sunset Manor',
                user_id: 'user-notif-01',
                title: 'Subscription Expired',
                body: 'Your access to Sunset Manor has expired. Renew to continue.',
                type: 'SUBSCRIPTION_EXPIRED',
                priority: 'CRITICAL',
                requires_action: true,
                action_status: 'OPEN',
                action_type: 'RENEW',
                action_url: '/settings/subscription',
                action_label: 'Renew Now',
                is_read: false,
                created_at: new Date().toISOString()
              }
            ],
            unread_count: 1,
            priority_unread_count: 1,
            action_required_count: 1,
            total: 1
          }
        })
      });
    });

    await page.goto('/dashboard');

    // Priority alert banner should be visible on top of dashboard
    await expect(page.getByText(/1 action requires your attention/i)).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole('button', { name: 'Renew Now' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'View All' })).toBeVisible();
  });

  test('2. /notifications Center validates Read != Resolved and Action Lifecycle', async ({ page }) => {
    const homeId = '22222222-2222-2222-2222-222222222222';

    await page.addInitScript(({ token, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('active_home_id', hId);
    }, { token: 'mock-user-jwt', hId: homeId });

    // Mock /users/me
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'user-notif-01',
            email: 'notifuser@ozhzo.com',
            display_name: 'Alert User',
            mobile_verified: true,
            free_home_consumed: true,
            is_super_admin: false,
            system_role: 'USER',
            homes: [{ home_id: homeId, name: "Sunset Manor", role: 'OWNER', status: 'ACTIVE' }]
          }
        })
      });
    });

    // Mock /homes
    await page.route('**/api/v1/homes', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [{ id: homeId, name: 'Sunset Manor', currency: 'USD', role: 'OWNER', status: 'ACTIVE' }]
        })
      });
    });

    // Mock /notifications route handler
    await page.route('**/api/v1/notifications**', async (route) => {
      const url = route.request().url();
      const method = route.request().method();

      if (url.includes('/priority')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { action_required_count: 1, critical_count: 1, high_count: 0, unread_count: 1, items: [] }
          })
        });
      }

      if (url.includes('/read') && method === 'PATCH') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data: { message: "Notification marked as read." } })
        });
      }

      if (url.includes('/acknowledge') && method === 'PATCH') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data: { message: "Notification acknowledged." } })
        });
      }

      if (url.includes('/resolve') && method === 'PATCH') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data: { message: "Notification marked as resolved." } })
        });
      }

      // Default GET notifications list
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              {
                id: 'n-inv-1',
                home_id: homeId,
                home_name: 'Sunset Manor',
                user_id: 'user-notif-01',
                title: 'Invitation to join Sunset Manor',
                body: 'Alex invited you to join Sunset Manor as ADMIN. Subscription reserved for you.',
                type: 'HOME_INVITATION',
                priority: 'HIGH',
                requires_action: true,
                action_status: 'OPEN',
                action_type: 'JOIN_HOME',
                action_url: '/invite/token-999',
                action_label: 'Accept / Decline',
                extra_metadata: { is_reserved: true },
                is_read: false,
                created_at: new Date().toISOString()
              },
              {
                id: 'n-norm-1',
                home_id: homeId,
                home_name: 'Sunset Manor',
                user_id: 'user-notif-01',
                title: 'Task Assigned',
                body: 'Wash dishes assigned to you.',
                type: 'TASK_ASSIGNED',
                priority: 'NORMAL',
                requires_action: false,
                action_status: 'OPEN',
                is_read: false,
                created_at: new Date().toISOString()
              }
            ],
            unread_count: 2,
            priority_unread_count: 1,
            action_required_count: 1,
            total: 2
          }
        })
      });
    });

    await page.goto('/notifications');

    // 1. Action Required tab is active by default
    await expect(page.getByRole('button', { name: /Action Required/i })).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Invitation to join Sunset Manor')).toBeVisible();
    await expect(page.getByText('Subscription seat pre-reserved and paid by Home Admin.')).toBeVisible();

    // 2. Click "Read" button -> verifies Read != Resolved (Item stays on screen)
    const readBtn = page.getByRole('button', { name: 'Read' }).first();
    await expect(readBtn).toBeVisible();
    await readBtn.click();
    await expect(page.getByText('Marked as read')).toBeVisible();
    await expect(page.getByText('Invitation to join Sunset Manor')).toBeVisible();

    // 3. Click "Acknowledge"
    const ackBtn = page.getByRole('button', { name: 'Acknowledge' });
    await expect(ackBtn).toBeVisible();
    await ackBtn.click();
    await expect(page.getByText('Notification acknowledged')).toBeVisible();

    // 4. Click "Resolve" -> item resolves
    const resolveBtn = page.getByRole('button', { name: 'Resolve', exact: true });
    await expect(resolveBtn).toBeVisible();
    await resolveBtn.click();
    await expect(page.getByText('Marked as resolved')).toBeVisible();
  });

  test('3. /notifications All Notifications tab displays complete household stream', async ({ page }) => {
    const homeId = '22222222-2222-2222-2222-222222222222';

    await page.addInitScript(({ token, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('active_home_id', hId);
    }, { token: 'mock-user-jwt', hId: homeId });

    // Mock /users/me
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'user-notif-01',
            email: 'notifuser@ozhzo.com',
            display_name: 'Alert User',
            mobile_verified: true,
            free_home_consumed: true,
            is_super_admin: false,
            system_role: 'USER',
            homes: [{ home_id: homeId, name: "Sunset Manor", role: 'OWNER', status: 'ACTIVE' }]
          }
        })
      });
    });

    // Mock /homes
    await page.route('**/api/v1/homes', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [{ id: homeId, name: 'Sunset Manor', currency: 'USD', role: 'OWNER', status: 'ACTIVE' }]
        })
      });
    });

    // Mock /notifications/priority
    await page.route('**/api/v1/notifications/priority', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { action_required_count: 0, critical_count: 0, high_count: 0, unread_count: 1, items: [] }
        })
      });
    });

    // Mock /notifications list
    await page.route('**/api/v1/notifications?**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              {
                id: 'n-norm-1',
                home_id: homeId,
                home_name: 'Sunset Manor',
                user_id: 'user-notif-01',
                title: 'Grocery Stock Low',
                body: 'Milk has 0.2 Liters remaining.',
                type: 'LOW_STOCK',
                priority: 'NORMAL',
                requires_action: false,
                action_status: 'OPEN',
                is_read: false,
                created_at: new Date().toISOString()
              }
            ],
            unread_count: 1,
            priority_unread_count: 0,
            action_required_count: 0,
            total: 1
          }
        })
      });
    });

    await page.goto('/notifications');

    // Switch to All Notifications tab
    await page.getByRole('button', { name: /All Notifications/i }).click();
    await expect(page.getByText('Grocery Stock Low')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Milk has 0.2 Liters remaining.')).toBeVisible();
  });

});
