import { test, expect } from '@playwright/test';

test.describe('Reproduction Verification: Invitation Identity Mismatch Defect Fix', () => {
  const token = 'OZ-FE9EDU-TOKEN';
  const code = 'OZ-FE9EDU';

  test('Verify that Accept button is NOT rendered when mobile identity does not match and mismatch message is displayed', async ({ page }) => {
    // Authenticate as vyshak Thayyullathil (+19998887777, but invite is for +15551234567)
    await page.addInitScript(() => {
      localStorage.setItem('access_token', 'mock-vyshak-token');
      localStorage.setItem('active_home_id', 'h-1');
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

    // Mock /invitations/{token} returning invitation issued to Vivek Madhavan's friend with phone +15551234567
    await page.route(`**/api/v1/invitations/${token}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'inv-123',
            home_id: 'home-sandhya',
            home_name: 'Sandhya House',
            role: 'MEMBER',
            token: token,
            invitation_code: code,
            status: 'PENDING',
            invited_by_name: 'Vivek Madhavan',
            invited_by_email: 'vivek@sandhya.com',
            phone_number: '+15551234567',
            email: null,
            expires_at: new Date(Date.now() + 86400000).toISOString(),
            is_expired: false,
            is_already_member: false,
            is_identity_matched: false,
            identity_mismatch_reason: 'This invitation was issued to a different mobile number.'
          }
        })
      });
    });

    // Navigate to the invitation link
    await page.goto(`/invite/${token}`);
    await page.waitForLoadState('domcontentloaded');

    // Verify invitation card
    await expect(page.locator('body')).toContainText('Household Invitation');
    await expect(page.locator('body')).toContainText('Sandhya House');
    await expect(page.locator('body')).toContainText('Vivek Madhavan');
    await expect(page.locator('body')).toContainText('vyshak Thayyullathil');

    // Verify identity mismatch banner is shown
    await expect(page.locator('body')).toContainText('This invitation was issued to a different mobile number.');
    await expect(page.locator('body')).toContainText('Please sign in with the account associated with this invitation');

    // Verify Accept & Join Home button is NOT visible
    const acceptBtn = page.locator('button:has-text("Accept & Join Home")');
    expect(await acceptBtn.isVisible()).toBe(false);

    // Verify Sign In with Invited Account CTA is visible
    const switchBtn = page.locator('button:has-text("Sign In with Invited Account")');
    expect(await switchBtn.isVisible()).toBe(true);
  });
});
