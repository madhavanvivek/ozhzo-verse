import { test, expect } from '@playwright/test';

test.describe('Ozhzo Verse — Home Admin, Invitations & UI End-to-End Tests', () => {

  const homeId = 'home-ichu-777';
  let homeName = "Ichu's Home";
  let pendingInvitations: any[] = [];

  test.beforeEach(async ({ page, context }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await context.clearCookies();

    // Default notifications
    await page.route('**/api/v1/notifications**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] })
      });
    });

    // Default auth/login
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            access_token: 'mock-user-token',
            refresh_token: 'mock-user-refresh',
            user_id: 'user-vivek-123',
            email: 'vivek@zinfog.com'
          }
        })
      });
    });

    // Default users/me
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'user-vivek-123',
            email: 'vivek@zinfog.com',
            display_name: 'Vivek',
            mobile_verified: true,
            is_super_admin: false,
            system_role: 'USER',
            homes: [
              {
                home_id: homeId,
                name: homeName,
                role: 'OWNER',
                status: 'ACTIVE'
              }
            ]
          }
        })
      });
    });

    // Default homes list
    await page.route('**/api/v1/homes', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [
              {
                id: homeId,
                name: homeName,
                currency: 'USD',
                role: 'OWNER',
                status: 'ACTIVE',
                created_at: new Date().toISOString()
              }
            ]
          })
        });
      } else {
        await route.continue();
      }
    });

    // Default single home endpoint
    await page.route(`**/api/v1/homes/${homeId}`, async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              id: homeId,
              name: homeName,
              currency: 'USD',
              timezone: 'UTC',
              address: '742 Evergreen Terrace',
              status: 'ACTIVE',
              role: 'OWNER',
              created_by: 'user-vivek-123',
              members: [
                {
                  id: 'mem-1',
                  user_id: 'user-vivek-123',
                  display_name: 'Vivek',
                  role: 'OWNER',
                  status: 'ACTIVE'
                }
              ]
            }
          })
        });
      } else if (route.request().method() === 'PATCH' || route.request().method() === 'PUT') {
        const body = route.request().postDataJSON();
        if (body?.name) homeName = body.name;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              id: homeId,
              name: homeName,
              currency: body?.currency || 'USD',
              timezone: body?.timezone || 'UTC',
              address: body?.address || '742 Evergreen Terrace',
              status: 'ACTIVE'
            }
          })
        });
      } else if (route.request().method() === 'DELETE') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, message: 'Home deleted successfully' })
        });
      } else {
        await route.continue();
      }
    });

    // Default members list
    await page.route(`**/api/v1/homes/${homeId}/members*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: 'mem-1',
              user_id: 'user-vivek-123',
              display_name: 'Vivek',
              role: 'OWNER',
              status: 'ACTIVE'
            }
          ]
        })
      });
    });

    // Default invitations list and create
    await page.route(`**/api/v1/homes/${homeId}/invitations*`, async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: pendingInvitations
          })
        });
      } else if (route.request().method() === 'POST') {
        const body = route.request().postDataJSON();
        const newInv = {
          id: `inv-${Date.now()}`,
          home_id: homeId,
          email: body?.email || 'invite@ozhzo.com',
          role: body?.role || 'MEMBER',
          status: 'PENDING',
          invitation_mode: 'EMAIL',
          invitation_code: 'OZ-789XYZ',
          token: 'tok-abc-123',
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 86400000).toISOString()
        };
        pendingInvitations.push(newInv);
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: newInv
          })
        });
      } else {
        await route.continue();
      }
    });

    // Default identity and join requests
    await page.route(`**/api/v1/homes/${homeId}/identity*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            home_id: homeId,
            name: homeName,
            public_home_id: 'PUB-123',
            qr_token: 'mock-qr-token',
            qr_status: 'ACTIVE',
            qr_version: 1,
            qr_url: 'https://ozhzo.com/join/home/PUB-123'
          }
        })
      });
    });

    await page.route(`**/api/v1/homes/${homeId}/join-requests*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] })
      });
    });
  });

  test('1. Super Admin UI Login Flow (/admin/login -> /admin)', async ({ page }) => {
    const mockAdminLogin = async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            access_token: 'valid-super-admin-token',
            refresh_token: 'valid-super-admin-refresh',
            user_id: '99999999-9999-9999-9999-999999999999',
            email: 'vivek@zinfog.com'
          }
        })
      });
    };
    await page.route('**/api/v1/admin/auth/login', mockAdminLogin);
    await page.route('**/api/v1/admin/login', mockAdminLogin);

    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: '99999999-9999-9999-9999-999999999999',
            email: 'vivek@zinfog.com',
            display_name: 'Vivek Super Admin',
            is_super_admin: true,
            system_role: 'SUPER_ADMIN',
            homes: []
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

    await page.route('**/api/v1/admin/system/config**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            environment: 'production',
            supported_currencies: ['INR', 'USD'],
            default_timezone: 'UTC',
            rate_limiting_enabled: true,
            feature_flags: {}
          }
        })
      });
    });

    await page.route('**/api/v1/admin/system/analytics-summary**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            total_users: 10,
            active_users: 8,
            suspended_users: 2,
            total_homes: 5,
            active_homes: 5,
            suspended_homes: 0,
            average_members_per_home: 2.4,
            total_active_subscriptions: 4,
            total_paid_member_seats: 8
          }
        })
      });
    });

    await page.route('**/api/v1/admin/analytics/countries**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] })
      });
    });

    await page.route('**/api/v1/admin/analytics/retention**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: null })
      });
    });

    await page.goto('/admin/login');
    await expect(page.locator('h1')).toContainText('Platform Administration');

    const testAdminEmail = process.env.ADMIN_EMAIL || 'admin@example.com';
    const testAdminPassword = process.env.ADMIN_PASSWORD || 'TestAdminPassword123!';
    await page.fill('#admin-login-email', testAdminEmail);
    await page.fill('#admin-login-password', testAdminPassword);
    await page.click('#admin-submit-btn');

    await page.waitForURL('**/admin', { timeout: 15000 });
    await expect(page.getByText('Platform Overview & Operational Control Center').or(page.getByText('Platform Overview'))).toBeVisible({ timeout: 10000 });
  });

  test('2. Home Admin Edit Home Settings Flow (/settings)', async ({ page, context }) => {
    await context.addCookies([
      { name: 'access_token', value: 'mock-user-token', domain: 'localhost', path: '/' }
    ]);
    await page.addInitScript(({ token, rToken, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('refresh_token', rToken);
      localStorage.setItem('active_home_id', hId);
    }, { token: 'mock-user-token', rToken: 'mock-user-refresh', hId: homeId });

    await page.goto('/settings');
    await expect(page.locator('h1')).toContainText('Home Settings & Management');

    const nameInput = page.locator('#homeName');
    await expect(nameInput).toBeVisible();
    await expect(nameInput).toBeEnabled();

    const uniqueSuffix = Date.now().toString().slice(-4);
    const updatedName = `Ichu's Home ${uniqueSuffix}`;
    await nameInput.fill(updatedName);
    await page.selectOption('#currency', 'USD');
    await page.selectOption('#timezone', 'UTC');
    await page.fill('#address', '742 Evergreen Terrace');

    const saveBtn = page.getByRole('button', { name: /Save Changes/i });
    await expect(saveBtn).toBeVisible();
    await saveBtn.click();

    await expect(page.getByText('Home settings updated successfully')).toBeVisible({ timeout: 10000 });

    await page.reload();
    await expect(page.locator('#homeName')).toHaveValue(updatedName, { timeout: 10000 });
    await expect(page.locator('#currency')).toHaveValue('USD');
    await expect(page.locator('#timezone')).toHaveValue('UTC');
  });

  test('3. Home Admin Member Invitation, Code Visibility & Persistence (/members)', async ({ page, context }) => {
    await context.addCookies([
      { name: 'access_token', value: 'mock-user-token', domain: 'localhost', path: '/' }
    ]);
    await page.addInitScript(({ token, rToken, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('refresh_token', rToken);
      localStorage.setItem('active_home_id', hId);
    }, { token: 'mock-user-token', rToken: 'mock-user-refresh', hId: homeId });

    await page.goto('/members');
    await expect(page.locator('h1')).toContainText('Family Members');

    const uniqueEmail = `invite_test_${Date.now().toString().slice(-6)}@ozhzo.com`;
    await page.fill('#inviteEmail', uniqueEmail);
    await page.selectOption('#inviteRole', 'MEMBER');
    await page.click('button[type="submit"]');

    const modal = page.getByRole('dialog', { name: 'Invitation Created' });
    await expect(modal).toBeVisible({ timeout: 10000 });
    await expect(modal.getByText('Invitation Code', { exact: true })).toBeVisible();
    await expect(modal.getByText(/OZ-/i)).toBeVisible();

    const copyCodeModalBtn = modal.getByRole('button', { name: /Copy Code/i });
    if (await copyCodeModalBtn.isVisible()) {
      await copyCodeModalBtn.click();
      await expect(modal.getByText('Code Copied')).toBeVisible({ timeout: 5000 });
    }

    const doneBtn = modal.getByRole('button', { name: /Done/i });
    await doneBtn.click();
    await expect(modal).not.toBeVisible();

    const pendingSection = page.getByText(/Pending Invitations/i);
    await expect(pendingSection).toBeVisible();

    const inviteRow = page.locator('div').filter({ hasText: uniqueEmail }).first();
    await expect(inviteRow).toBeVisible();
    await expect(inviteRow.getByText('Code:', { exact: true })).toBeVisible();
    await expect(inviteRow.getByText(/OZ-/i).first()).toBeVisible();

    const copyCodeBtn = inviteRow.getByRole('button', { name: /Copy Code/i });
    await expect(copyCodeBtn).toBeVisible();
    await copyCodeBtn.click();
    await expect(inviteRow.getByText('Code Copied')).toBeVisible({ timeout: 5000 });

    const copyLinkBtn = inviteRow.getByRole('button', { name: /Copy Link/i });
    await expect(copyLinkBtn).toBeVisible();
    await copyLinkBtn.click();
    await expect(inviteRow.getByText('Link Copied')).toBeVisible({ timeout: 5000 });

    await page.reload();
    await expect(page.locator('h1')).toContainText('Family Members');

    const refreshedInviteRow = page.locator('div').filter({ hasText: uniqueEmail }).first();
    await expect(refreshedInviteRow).toBeVisible({ timeout: 10000 });
    await expect(refreshedInviteRow.getByText('Code:', { exact: true })).toBeVisible();
    await expect(refreshedInviteRow.getByText(/OZ-/i).first()).toBeVisible();
    await expect(refreshedInviteRow.getByRole('button', { name: /Copy Code/i })).toBeVisible();
    await expect(refreshedInviteRow.getByRole('button', { name: /Copy Link/i })).toBeVisible();
  });

  test('4. Join Home by Code Flow (/join)', async ({ page }) => {
    await page.goto('/join');
    await expect(page.locator('h1')).toContainText(/Join a (Household|Home Workspace)/i);
    await expect(page.locator('#invitationCode')).toBeVisible();
    await expect(page.getByRole('button', { name: /Accept Invitation|Join Home/i })).toBeVisible();
  });

  test('5. Home Settings Danger Zone Delete Workspace Flow', async ({ page, context }) => {
    await context.addCookies([
      { name: 'access_token', value: 'mock-user-token', domain: 'localhost', path: '/' }
    ]);
    await page.addInitScript(({ token, rToken, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('refresh_token', rToken);
      localStorage.setItem('active_home_id', hId);
    }, { token: 'mock-user-token', rToken: 'mock-user-refresh', hId: homeId });

    await page.goto('/settings');
    await expect(page.getByText('Danger Zone')).toBeVisible();
    await expect(page.getByRole('button', { name: /Delete This Home/i })).toBeVisible();
  });

});

