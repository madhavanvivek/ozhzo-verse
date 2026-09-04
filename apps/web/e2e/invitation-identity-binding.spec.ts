import { test, expect } from '@playwright/test';
import * as path from 'path';

const evidenceDir = '/Users/vivek/.gemini/antigravity/brain/e417cc97-7d7a-4622-ab0c-93f6404efdd2/invitation_fix_evidence';

test.describe('Ozhzo Verse — Invitation Identity Binding & Join Flow Verification', () => {

  const homeSandhyaId = '11111111-1111-1111-1111-111111111111';
  const token = 'OZ-FE9EDU-TOKEN';
  const code = 'OZ-FE9EDU';

  test.beforeAll(async () => {
    // Ensure evidence directory exists
    const fs = require('fs');
    if (!fs.existsSync(evidenceDir)) {
      fs.mkdirSync(evidenceDir, { recursive: true });
    }
  });

  test('1. Wrong-account invitation link: Blocks Accept button and presents Sign in with invited account', async ({ page }) => {
    // Authenticate as Vyshak (wrong user: +19998887777, invite is for +15551234567)
    await page.addInitScript(() => {
      localStorage.setItem('access_token', 'mock-vyshak-token');
      localStorage.setItem('active_home_id', 'h-default');
    });

    // Mock /users/me returning Vyshak
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'user-vyshak',
            email: 'vyshak@example.com',
            display_name: 'vyshak Thayyullathil',
            phone_number: '+19998887777',
            mobile_verified: true,
            is_active: true,
            homes: []
          }
        })
      });
    });

    // Mock /invitations/{token} returning Sandhya House invite issued to +15551234567
    await page.route(`**/api/v1/invitations/${token}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'inv-123',
            home_id: homeSandhyaId,
            home_name: 'Sandhya House',
            role: 'MEMBER',
            token: token,
            invitation_code: code,
            status: 'PENDING',
            invited_by_name: 'Vivek Madhavan',
            invited_by_email: 'vivek@sandhya.com',
            phone_number: '+15551234567',
            email: null,
            expires_at: new Date(Date.now() + 86400000 * 7).toISOString(),
            is_expired: false,
            is_already_member: false,
            is_identity_matched: false,
            identity_mismatch_reason: 'This invitation was issued to a different mobile number.'
          }
        })
      });
    });

    await page.goto(`/invite/${token}`);
    await page.waitForLoadState('domcontentloaded');

    // Verification 1: Header and metadata
    await expect(page.locator('body')).toContainText('Household Invitation');
    await expect(page.locator('body')).toContainText('Sandhya House');
    await expect(page.locator('body')).toContainText('Vivek Madhavan');
    await expect(page.locator('body')).toContainText('vyshak Thayyullathil');

    // Verification 2: Identity mismatch message is visible
    await expect(page.locator('body')).toContainText('This invitation was issued to a different mobile number.');
    await expect(page.locator('body')).toContainText('Please sign in with the account associated with this invitation');

    // Verification 3: "Accept & Join Home" button MUST NOT be present
    const acceptBtn = page.locator('button:has-text("Accept & Join Home")');
    expect(await acceptBtn.isVisible()).toBe(false);

    // Verification 4: "Sign In with Invited Account" CTA is present
    const switchBtn = page.locator('button:has-text("Sign In with Invited Account")');
    expect(await switchBtn.isVisible()).toBe(true);

    // Capture screenshot evidence
    await page.screenshot({ path: path.join(evidenceDir, '01_wrong_account_link_blocked.png'), fullPage: true });
  });

  test('2. Correct-account invitation link: Displays Accept button and joins successfully', async ({ page }) => {
    // Authenticate as Rightful User (+15551234567)
    await page.addInitScript(() => {
      localStorage.setItem('access_token', 'mock-rightful-token');
      localStorage.setItem('active_home_id', 'h-default');
    });

    // Mock /users/me returning Rightful User
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'user-rightful',
            email: 'rightful@sandhya.com',
            display_name: 'Rightful Recipient',
            phone_number: '+15551234567',
            mobile_verified: true,
            is_active: true,
            homes: []
          }
        })
      });
    });

    // Mock /invitations/{token}
    await page.route(`**/api/v1/invitations/${token}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'inv-123',
            home_id: homeSandhyaId,
            home_name: 'Sandhya House',
            role: 'MEMBER',
            token: token,
            invitation_code: code,
            status: 'PENDING',
            invited_by_name: 'Vivek Madhavan',
            invited_by_email: 'vivek@sandhya.com',
            phone_number: '+15551234567',
            email: null,
            expires_at: new Date(Date.now() + 86400000 * 7).toISOString(),
            is_expired: false,
            is_already_member: false,
            is_identity_matched: true,
            identity_mismatch_reason: null
          }
        })
      });
    });

    // Mock /invitations/{token}/accept
    await page.route(`**/api/v1/invitations/${token}/accept`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            home_id: homeSandhyaId,
            home_name: 'Sandhya House',
            role: 'MEMBER',
            message: "You have joined 'Sandhya House'!"
          }
        })
      });
    });

    await page.goto(`/invite/${token}`);
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText('Rightful Recipient');
    const acceptBtn = page.locator('button:has-text("Accept & Join Home")');
    expect(await acceptBtn.isVisible()).toBe(true);

    // Capture screenshot before acceptance
    await page.screenshot({ path: path.join(evidenceDir, '02_correct_account_link_accepted.png'), fullPage: true });

    // Click Accept & Join Home
    await acceptBtn.click();
    await expect(page.locator('body')).toContainText("You have joined 'Sandhya House'!");
  });

  test('3. Wrong-account invitation code on /join: Rejects and presents switch account CTA', async ({ page }) => {
    // Authenticate as Vyshak
    await page.addInitScript(() => {
      localStorage.setItem('access_token', 'mock-vyshak-token');
      localStorage.setItem('active_home_id', 'h-default');
    });

    // Mock /homes/invitations/redeem returning 403 identity mismatch
    await page.route('**/api/v1/homes/invitations/redeem', async (route) => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'This invitation was issued to a different mobile number.'
        })
      });
    });

    await page.goto('/join');
    await page.waitForLoadState('domcontentloaded');

    await page.fill('#invitationCode', code);
    await page.click('button:has-text("Accept Invitation")');

    await expect(page.locator('body')).toContainText('This invitation was issued to a different mobile number.');
    const switchBtn = page.locator('button:has-text("Sign In with Invited Account")');
    expect(await switchBtn.isVisible()).toBe(true);

    await page.screenshot({ path: path.join(evidenceDir, '03_wrong_account_code_blocked.png'), fullPage: true });
  });

  test('4. Correct-account invitation code on /join: Redeems and joins successfully', async ({ page }) => {
    // Authenticate as Rightful User
    await page.addInitScript(() => {
      localStorage.setItem('access_token', 'mock-rightful-token');
      localStorage.setItem('active_home_id', 'h-default');
    });

    // Mock /homes/invitations/redeem returning 200 OK
    await page.route('**/api/v1/homes/invitations/redeem', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            home_id: homeSandhyaId,
            home_name: 'Sandhya House',
            role: 'MEMBER',
            message: 'Welcome to Sandhya House!'
          }
        })
      });
    });

    await page.goto('/join');
    await page.waitForLoadState('domcontentloaded');

    await page.fill('#invitationCode', code);
    await page.click('button:has-text("Accept Invitation")');

    await expect(page.locator('body')).toContainText('Welcome to Sandhya House!');
    await page.screenshot({ path: path.join(evidenceDir, '04_correct_account_code_accepted.png'), fullPage: true });
  });

  test('5. Mobile 390px viewport: Blocked state renders cleanly with responsive touch targets', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });

    // Authenticate as Vyshak
    await page.addInitScript(() => {
      localStorage.setItem('access_token', 'mock-vyshak-token');
    });

    // Mock /users/me
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'user-vyshak',
            email: 'vyshak@example.com',
            display_name: 'vyshak Thayyullathil',
            phone_number: '+19998887777',
            mobile_verified: true,
            is_active: true,
            homes: []
          }
        })
      });
    });

    // Mock /invitations/{token}
    await page.route(`**/api/v1/invitations/${token}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'inv-123',
            home_id: homeSandhyaId,
            home_name: 'Sandhya House',
            role: 'MEMBER',
            token: token,
            invitation_code: code,
            status: 'PENDING',
            invited_by_name: 'Vivek Madhavan',
            invited_by_email: 'vivek@sandhya.com',
            phone_number: '+15551234567',
            email: null,
            expires_at: new Date(Date.now() + 86400000 * 7).toISOString(),
            is_expired: false,
            is_already_member: false,
            is_identity_matched: false,
            identity_mismatch_reason: 'This invitation was issued to a different mobile number.'
          }
        })
      });
    });

    await page.goto(`/invite/${token}`);
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('body')).toContainText('This invitation was issued to a different mobile number.');
    const switchBtn = page.locator('button:has-text("Sign In with Invited Account")');
    expect(await switchBtn.isVisible()).toBe(true);

    const box = await switchBtn.boundingBox();
    expect(box?.height).toBeGreaterThanOrEqual(44);

    await page.screenshot({ path: path.join(evidenceDir, '05_mobile_390px_mismatch_blocked.png') });
  });

});
