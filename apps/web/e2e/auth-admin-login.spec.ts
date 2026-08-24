import { test, expect } from '@playwright/test';

test.describe('Ozhzo Verse Authentication and Super Admin Access Flow', () => {

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
    await page.addInitScript(() => {
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
    await page.addInitScript(() => {
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

});
