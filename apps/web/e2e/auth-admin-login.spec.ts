import { test, expect } from '@playwright/test';

test.describe('Ozhzo Verse Authentication and Super Admin Access Flow', () => {

  test.beforeEach(async ({ page, context }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await context.clearCookies();
  });

  test('1. Normal household /login renders properly with Phone and Email tabs', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('h1')).toContainText('Welcome Back');
    await expect(page.getByText('Sign in to your Ozhzo Verse home')).toBeVisible();

    // Verify Tab Toggle
    const emailTab = page.getByRole('button', { name: 'Email' });
    await emailTab.click();
    await expect(page.locator('#email')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
  });

  test('2. /admin/login page renders Platform Operations Console frame', async ({ page }) => {
    await page.goto('/admin/login');
    await expect(page.getByText('Platform Operations Console')).toBeVisible();
    await expect(page.locator('h1')).toContainText('Platform Administration');
    await expect(page.locator('#admin-login-email')).toBeVisible();
    await expect(page.locator('#admin-login-password')).toBeVisible();
    await expect(page.getByRole('button', { name: /Sign in to Platform/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Return to Household Login/i }).first()).toBeVisible();
  });

  test('3. Flow C: Wrong password displays "Authentication Failed" & "Invalid email or password."', async ({ page }) => {
    // Intercept backend auth login with 401
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          detail: 'Invalid credentials or verification code.'
        })
      });
    });

    await page.goto('/admin/login');
    await page.fill('#admin-login-email', 'vivek@zinfog.com');
    await page.fill('#admin-login-password', 'wrongpassword');
    await page.click('#admin-submit-btn');

    // Verify Error Box
    await expect(page.getByText('Authentication Failed')).toBeVisible();
    await expect(page.getByText('Invalid email or password.')).toBeVisible();
    // Ensure legacy string is not present
    await expect(page.getByText('Invalid platform administrator email or password.')).not.toBeVisible();
  });

  test('4. Flows A & D: Household OWNER/MEMBER authenticated but not Super Admin displays "Access Restricted"', async ({ page }) => {
    // Intercept auth/login to return valid tokens
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            access_token: 'fake-jwt-token-owner',
            refresh_token: 'fake-refresh-token',
            user_id: '11111111-1111-1111-1111-111111111111',
            email: 'household_owner@example.com'
          }
        })
      });
    });

    // Intercept users/me to return non-admin profile (household owner)
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: '11111111-1111-1111-1111-111111111111',
            email: 'household_owner@example.com',
            display_name: 'Household Owner',
            is_super_admin: false,
            system_role: 'USER',
            homes: [
              {
                home_id: '22222222-2222-2222-2222-222222222222',
                name: 'Main Villa',
                role: 'OWNER',
                status: 'ACTIVE'
              }
            ]
          }
        })
      });
    });

    await page.goto('/admin/login');
    await page.fill('#admin-login-email', 'household_owner@example.com');
    await page.fill('#admin-login-password', 'ValidOwnerPassword123');
    await page.click('#admin-submit-btn');

    // Verify Access Restricted Message
    await expect(page.getByText('Access Restricted')).toBeVisible();
    await expect(page.getByText('Platform administrator access required. Household accounts (OWNER, HOME_ADMIN, MEMBER) cannot administer the platform.')).toBeVisible();
    await expect(page.getByRole('link', { name: /Return to Household Login/i }).first()).toBeVisible();

    // Verify tokens cleared
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(token).toBeNull();
  });

  test('5. Flows B & E: Super Admin authentication succeeds and redirects to /admin', async ({ page }) => {
    // Intercept auth/login with successful response
    await page.route('**/api/v1/auth/login', async (route) => {
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
    });

    // Intercept users/me returning Super Admin flags
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
            homes: [
              {
                home_id: '33333333-3333-3333-3333-333333333333',
                name: 'Vivek Home',
                role: 'OWNER',
                status: 'ACTIVE'
              }
            ]
          }
        })
      });
    });

    // Intercept admin analytics to allow /admin dashboard rendering
    await page.route('**/api/v1/admin/system/analytics/summary', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            total_users: 120,
            active_users: 110,
            total_homes: 30,
            active_homes: 29,
            total_memberships: 85,
            active_subscriptions: 28,
            paid_seats: 60
          }
        })
      });
    });

    await page.goto('/admin/login');
    await page.fill('#admin-login-email', 'vivek@zinfog.com');
    await page.fill('#admin-login-password', 'CorrectPassword123');
    await page.click('#admin-submit-btn');

    // Verifies navigation to /admin
    await page.waitForURL('**/admin', { timeout: 10000 });
    expect(page.url()).toContain('/admin');
  });

  test('6. Super Admin Settings: Full Email-OTP verified password change flow', async ({ page }) => {
    // Setup authenticated state with mock tokens
    await page.goto('/admin/login');
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'mock-super-admin-jwt');
      localStorage.setItem('refresh_token', 'mock-super-admin-refresh');
    });

    // Intercept users/me
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
            homes: []
          }
        })
      });
    });

    // Intercept send-email-otp
    await page.route('**/api/v1/admin/security/send-email-otp', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            message: 'Verification code sent to v***k@zinfog.com.',
            email: 'v***k@zinfog.com',
            cooldown_seconds: 60,
            expires_in_seconds: 600,
            is_demo_otp: true,
            otp_code: '123456'
          }
        })
      });
    });

    // Intercept verify-email-otp
    await page.route('**/api/v1/admin/security/verify-email-otp', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            message: 'Email address successfully verified.',
            verification_ticket: 'test-verification-ticket-1234567890',
            expires_in_seconds: 900
          }
        })
      });
    });

    // Intercept change-password
    await page.route('**/api/v1/admin/security/change-password', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            message: 'Super Admin password updated successfully.',
            access_token: 'new-rotated-super-admin-jwt',
            refresh_token: 'new-rotated-refresh-token',
            expires_in: 900
          }
        })
      });
    });

    // Navigate to /admin/settings
    await page.goto('/admin/settings');
    await expect(page.getByText('Platform Security & Settings')).toBeVisible();
    await expect(page.locator('#super-admin-email')).toContainText('vivek@zinfog.com');
    await expect(page.getByText('••••••••••••')).toBeVisible();

    // Step 1: Click "Change Password"
    await page.click('#change-password-btn');

    // Step 2 & 3: Shows OTP verification step
    await expect(page.getByRole('heading', { name: /Verify your email/i })).toBeVisible();
    await expect(page.locator('#email-otp-input')).toBeVisible();

    // Fill OTP and click Verify Email
    await page.fill('#email-otp-input', '123456');
    await page.click('#verify-otp-btn');

    // Step 4: Shows New Password form
    await expect(page.getByText('Set New Password')).toBeVisible();
    await page.fill('#new-password-input', 'NewSuperPass@2026');
    await page.fill('#confirm-password-input', 'NewSuperPass@2026');

    // Submit new password
    await page.click('#submit-new-password-btn');

    // Step 5: Verify Success Screen
    await expect(page.getByRole('heading', { name: /Password Updated Successfully/i })).toBeVisible();
    await expect(page.getByText('All other active sessions have been securely invalidated')).toBeVisible();

    // Click Done to return to settings
    await page.click('#password-success-done-btn');
    await expect(page.getByText('Platform Security & Settings')).toBeVisible();

    // Verify tokens were refreshed in localStorage
    const refreshedToken = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(refreshedToken).toBe('new-rotated-super-admin-jwt');
  });

  test('7. /admin/profile route renders Security & Settings console', async ({ page }) => {
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
          data: {
            id: '99999999-9999-9999-9999-999999999999',
            email: 'vivek@zinfog.com',
            is_super_admin: true,
            system_role: 'SUPER_ADMIN',
            homes: []
          }
        })
      });
    });

    await page.goto('/admin/profile');
    await expect(page.getByText('Platform Security & Settings')).toBeVisible();
    await expect(page.locator('#change-password-btn')).toBeVisible();
  });

  test('8. /admin/users renders real users list, shows SUPER ADMIN badge for vivek@zinfog.com, and supports search', async ({ page }) => {
    await page.goto('/admin/login');
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'mock-super-admin-jwt');
    });

    // Mock /users/me as Super Admin
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: '99999999-9999-9999-9999-999999999999',
            email: 'vivek@zinfog.com',
            is_super_admin: true,
            system_role: 'SUPER_ADMIN',
            homes: []
          }
        })
      });
    });

    // Mock /admin/users list
    await page.route('**/api/v1/admin/users*', async (route) => {
      const url = route.request().url();
      if (url.includes('query=vivek')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [
              {
                id: '99999999-9999-9999-9999-999999999999',
                email: 'vivek@zinfog.com',
                phone_number: '+1234567890',
                display_name: 'Vivek',
                is_active: true,
                is_verified: true,
                mobile_verified: true,
                is_super_admin: true,
                system_role: 'SUPER_ADMIN',
                homes_count: 2,
                created_at: '2026-01-01T00:00:00Z'
              }
            ]
          })
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [
              {
                id: '99999999-9999-9999-9999-999999999999',
                email: 'vivek@zinfog.com',
                phone_number: '+1234567890',
                display_name: 'Vivek',
                is_active: true,
                is_verified: true,
                mobile_verified: true,
                is_super_admin: true,
                system_role: 'SUPER_ADMIN',
                homes_count: 2,
                created_at: '2026-01-01T00:00:00Z'
              },
              {
                id: '88888888-8888-8888-8888-888888888888',
                email: 'member@example.com',
                phone_number: '+1987654321',
                display_name: 'Regular Household Member',
                is_active: true,
                is_verified: true,
                mobile_verified: true,
                is_super_admin: false,
                system_role: 'USER',
                homes_count: 1,
                created_at: '2026-01-02T00:00:00Z'
              }
            ]
          })
        });
      }
    });

    await page.goto('/admin/users');
    await expect(page.getByRole('heading', { name: 'User Accounts Management' })).toBeVisible();

    // Verify vivek@zinfog.com is listed in table
    await expect(page.getByRole('table').getByText('vivek@zinfog.com')).toBeVisible();
    await expect(page.getByRole('table').getByText('SUPER ADMIN')).toBeVisible();
    await expect(page.getByRole('table').getByText('2 Homes')).toBeVisible();

    // Verify search
    const searchInput = page.getByPlaceholder('Search by email, phone, or name...');
    await searchInput.fill('vivek@zinfog.com');
    await page.getByRole('button', { name: 'Search' }).click();
    await expect(page.getByRole('table').getByText('vivek@zinfog.com')).toBeVisible();
  });

  test('9. /admin/users/[id] displays user inspection detail without exposing secret credentials', async ({ page }) => {
    const vivekId = '99999999-9999-9999-9999-999999999999';

    await page.goto('/admin/login');
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'mock-super-admin-jwt');
    });

    // Mock /users/me as Super Admin
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: vivekId,
            email: 'vivek@zinfog.com',
            is_super_admin: true,
            system_role: 'SUPER_ADMIN',
            homes: []
          }
        })
      });
    });

    // Mock /admin/users/{id}
    await page.route(`**/api/v1/admin/users/${vivekId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: vivekId,
            email: 'vivek@zinfog.com',
            phone_number: '+1234567890',
            country_code: '+1',
            display_name: 'Vivek',
            is_active: true,
            is_verified: true,
            mobile_verified: true,
            is_super_admin: true,
            system_role: 'SUPER_ADMIN',
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
            memberships: [
              {
                home_id: '33333333-3333-3333-3333-333333333333',
                home_name: 'Main Villa',
                role: 'OWNER',
                status: 'ACTIVE',
                joined_at: '2026-01-01T00:00:00Z'
              }
            ]
          }
        })
      });
    });

    await page.goto(`/admin/users/${vivekId}`);
    await expect(page.getByText('vivek@zinfog.com').first()).toBeVisible();
    await expect(page.getByText('Platform Super Admin')).toBeVisible();
    await expect(page.getByText('Main Villa')).toBeVisible();
    await expect(page.getByText('OWNER')).toBeVisible();

    // Verify that sensitive strings are not present in DOM
    const bodyText = await page.textContent('body');
    expect(bodyText).not.toContain('password_hash');
    expect(bodyText).not.toContain('argon2id');
  });

  test('10. Session Boundary: Account A -> Logout -> Account B isolates active home without 403 error', async ({ page }) => {
    page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));
    page.on('pageerror', err => console.log('PAGE ERROR:', err.message));
    const userA_HomeId = 'aaaa-1111-aaaa-1111';
    const userB_HomeId = 'bbbb-2222-bbbb-2222';

    // Register all routes before navigation
    await page.route('**/api/v1/users/me', async (route) => {
      const auth = route.request().headers()['authorization'] || '';
      if (auth.includes('token-user-a')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              id: 'user-a-uuid',
              email: 'userA@example.com',
              display_name: 'User A',
              is_super_admin: false,
              system_role: 'USER',
              is_verified: true,
              mobile_verified: true,
              homes: [{ home_id: userA_HomeId, name: 'Home A', role: 'OWNER', status: 'ACTIVE' }]
            }
          })
        });
      } else if (auth.includes('token-user-b')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              id: 'user-b-uuid',
              email: 'userB@example.com',
              display_name: 'User B',
              is_super_admin: false,
              system_role: 'USER',
              is_verified: true,
              mobile_verified: true,
              homes: [{ home_id: userB_HomeId, name: 'Home B', role: 'OWNER', status: 'ACTIVE' }]
            }
          })
        });
      } else {
        await route.continue();
      }
    });

    await page.route('**/api/v1/homes', async (route) => {
      const auth = route.request().headers()['authorization'] || '';
      if (auth.includes('token-user-a')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [{ id: userA_HomeId, name: 'Home A', role: 'OWNER' }]
          })
        });
      } else if (auth.includes('token-user-b')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [{ id: userB_HomeId, name: 'Home B', role: 'OWNER' }]
          })
        });
      } else {
        await route.continue();
      }
    });

    // Mock Dashboard data for both homes
    await page.route(`**/api/v1/homes/${userA_HomeId}/dashboard`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            home_id: userA_HomeId,
            home_name: 'Home A',
            summary: { total_members: 1, low_stock_count: 0, pending_tasks: 0, upcoming_bills: 0 },
            quick_stats: { in_stock_pct: 100 },
            recent_activities: []
          }
        })
      });
    });

    await page.route(`**/api/v1/homes/${userB_HomeId}/dashboard`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            home_id: userB_HomeId,
            home_name: 'Home B',
            summary: { total_members: 1, low_stock_count: 0, pending_tasks: 0, upcoming_bills: 0 },
            quick_stats: { in_stock_pct: 100 },
            recent_activities: []
          }
        })
      });
    });

    // If User B tries to access Home A, return 403
    await page.route(`**/api/v1/homes/${userA_HomeId}/**`, async (route) => {
      const auth = route.request().headers()['authorization'] || '';
      if (auth.includes('token-user-b')) {
        await route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({
            success: false,
            detail: 'You are not an active member of this home.'
          })
        });
      } else {
        await route.continue();
      }
    });

    // Step 2: Login as User B
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            access_token: 'token-user-b',
            refresh_token: 'refresh-user-b',
            user_id: 'user-b-uuid',
            email: 'userB@example.com'
          }
        })
      });
    });

    // Step 1: User A was previously logged in with stale Home A state
    await page.goto('/login');
    await expect(page.locator('h1')).toContainText('Welcome Back');
    await page.evaluate(({ homeId }) => {
      localStorage.setItem('access_token', 'token-user-a');
      localStorage.setItem('active_home_id', homeId);
    }, { homeId: userA_HomeId });

    await page.click('#email-tab-btn');
    await expect(page.locator('#email')).toBeVisible();
    await page.fill('#email', 'userB@example.com');
    await page.fill('#password', 'ValidPass123!');
    await page.click('#login-submit-btn');

    // Step 3: Verify reaching /dashboard as Home B without 403 error
    await page.waitForURL('**/dashboard');
    await expect(page.getByText('Home B').first()).toBeVisible();
    await expect(page.getByText('You are not an active member of this home')).not.toBeVisible();
  });

  test('11. /admin/homes displays real tenant workspaces including "ichu\'s home"', async ({ page }) => {
    const homeId = '77777777-7777-7777-7777-777777777777';

    await page.goto('/admin/login');
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'mock-super-admin-jwt');
    });

    // Mock Super Admin profile
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: '99999999-9999-9999-9999-999999999999',
            email: 'vivek@zinfog.com',
            is_super_admin: true,
            system_role: 'SUPER_ADMIN',
            homes: []
          }
        })
      });
    });

    // Mock /admin/homes list
    await page.route('**/api/v1/admin/homes*', async (route) => {
      const url = route.request().url();
      if (url.includes('query=ichu') || url.includes('query=') || !url.includes('query')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [
              {
                id: homeId,
                name: "ichu's home",
                status: 'ACTIVE',
                currency: 'USD',
                created_by_email: 'vivek@zinfog.com',
                created_by_name: 'Vivek',
                members_count: 4,
                subscription_status: 'ACTIVE',
                created_at: '2026-01-15T10:00:00Z'
              }
            ]
          })
        });
      }
    });

    await page.goto('/admin/homes');
    await expect(page.getByRole('heading', { name: 'Household Workspaces' })).toBeVisible();

    // Verify "ichu's home" is in table
    await expect(page.getByText("ichu's home").first()).toBeVisible();
    await expect(page.getByText('vivek@zinfog.com').first()).toBeVisible();
    await expect(page.getByText('Vivek').first()).toBeVisible();
    await expect(page.getByText('4').first()).toBeVisible();
    await expect(page.locator('table').getByText('Active').first()).toBeVisible();
  });

  test('12. /admin/homes search filters for "ichu" dynamically', async ({ page }) => {
    const homeId = '77777777-7777-7777-7777-777777777777';

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

    await page.route('**/api/v1/admin/homes*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: homeId,
              name: "ichu's home",
              status: 'ACTIVE',
              currency: 'USD',
              created_by_email: 'vivek@zinfog.com',
              created_by_name: 'Vivek',
              members_count: 4,
              subscription_status: 'ACTIVE',
              created_at: '2026-01-15T10:00:00Z'
            }
          ]
        })
      });
    });

    await page.goto('/admin/homes');
    const searchInput = page.getByPlaceholder('Search by workspace name...');
    await searchInput.fill('ichu');
    await page.keyboard.press('Enter');

    await expect(page.getByText("ichu's home").first()).toBeVisible();
  });

  test('13. /admin/homes/[id] inspects details without leaking passwords or secrets', async ({ page }) => {
    const homeId = '77777777-7777-7777-7777-777777777777';

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

    await page.route(`**/api/v1/admin/homes/${homeId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: homeId,
            name: "ichu's home",
            status: 'ACTIVE',
            currency: 'USD',
            timezone: 'UTC',
            address: '123 Smart Home Lane',
            created_by_id: '99999999-9999-9999-9999-999999999999',
            created_by_email: 'vivek@zinfog.com',
            created_by_name: 'Vivek',
            created_at: '2026-01-15T10:00:00Z',
            members_count: 2,
            subscription_status: 'ACTIVE',
            subscription_plan: 'Ozhzo Home Standard',
            paid_seats: 1,
            members: [
              {
                user_id: '99999999-9999-9999-9999-999999999999',
                display_name: 'Vivek',
                email: 'vivek@zinfog.com',
                role: 'OWNER',
                status: 'ACTIVE',
                created_at: '2026-01-15T10:00:00Z'
              },
              {
                user_id: '88888888-8888-8888-8888-888888888888',
                display_name: 'Ichu Member',
                email: 'ichu@example.com',
                role: 'MEMBER',
                status: 'ACTIVE',
                created_at: '2026-01-16T10:00:00Z'
              }
            ]
          }
        })
      });
    });

    await page.goto(`/admin/homes/${homeId}`);
    await expect(page.getByText("ichu's home").first()).toBeVisible();
    await expect(page.getByText('Vivek').first()).toBeVisible();
    await expect(page.getByText('Ichu Member').first()).toBeVisible();
    await expect(page.getByText('OWNER').first()).toBeVisible();
    await expect(page.getByText('MEMBER').first()).toBeVisible();

    // Verify secret integrity
    const bodyContent = await page.textContent('body');
    expect(bodyContent).not.toContain('password_hash');
    expect(bodyContent).not.toContain('refresh_token');
  });

  test('14. /admin/homes API failure renders Retry button and does not claim "No Workspaces Found"', async ({ page }) => {
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

    // Mock API Failure
    await page.route('**/api/v1/admin/homes*', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          error: { message: 'Database connection failed' }
        })
      });
    });

    await page.goto('/admin/homes');
    await expect(page.getByText('Unable to load household workspaces')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Retry' })).toBeVisible();
    await expect(page.getByText('No household workspaces found.')).not.toBeVisible();
  });

});

