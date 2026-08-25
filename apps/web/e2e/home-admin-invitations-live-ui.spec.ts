import { test, expect } from '@playwright/test';

test.describe('Ozhzo Verse — Home Admin, Invitations & UI End-to-End Tests', () => {

  test('1. Super Admin UI Login Flow (/admin/login -> /admin)', async ({ page }) => {
    await page.goto('/admin/login');
    await expect(page.locator('h1')).toContainText('Platform Administration');

    await page.fill('#admin-login-email', 'vivek@zinfog.com');
    await page.fill('#admin-login-password', 'Caseno@123');
    await page.click('#admin-submit-btn');

    // Verify successful redirection to /admin dashboard
    await page.waitForURL('**/admin', { timeout: 15000 });
    await expect(page.getByText('Platform Administration Console').or(page.getByText('Platform Overview'))).toBeVisible({ timeout: 10000 });
  });

  test('2. Home Admin Edit Home Settings Flow (/settings)', async ({ page }) => {
    // 1. Log in through normal user login
    await page.goto('/login');
    const emailTab = page.getByRole('button', { name: 'Email' });
    if (await emailTab.isVisible()) {
      await emailTab.click();
    }
    await page.fill('#email', 'vivek@zinfog.com');
    await page.fill('#password', 'Caseno@123');
    await page.click('button[type="submit"]');

    await page.waitForURL('**/dashboard', { timeout: 15000 });

    // 2. Navigate to Home Settings
    await page.goto('/settings');
    await expect(page.locator('h1')).toContainText('Home Settings & Management');

    // 3. Verify Edit Form is enabled for HOME_ADMIN / OWNER
    const nameInput = page.locator('#homeName');
    await expect(nameInput).toBeVisible();
    await expect(nameInput).toBeEnabled();

    // 4. Update household details
    const uniqueSuffix = Date.now().toString().slice(-4);
    const updatedName = `Ichu's Home ${uniqueSuffix}`;
    await nameInput.fill(updatedName);
    await page.selectOption('#currency', 'USD');
    await page.selectOption('#timezone', 'UTC');
    await page.fill('#address', '742 Evergreen Terrace');

    // 5. Save Changes
    const saveBtn = page.getByRole('button', { name: /Save Changes/i });
    await expect(saveBtn).toBeVisible();
    await saveBtn.click();

    // 6. Verify Save Success Alert
    await expect(page.getByText('Home settings updated successfully')).toBeVisible({ timeout: 10000 });

    // 7. Refresh and verify persistence
    await page.reload();
    await expect(page.locator('#homeName')).toHaveValue(updatedName, { timeout: 10000 });
    await expect(page.locator('#currency')).toHaveValue('USD');
    await expect(page.locator('#timezone')).toHaveValue('UTC');
  });

  test('3. Home Admin Member Invitation, Code Visibility & Persistence (/members)', async ({ page }) => {
    // 1. Log in
    await page.goto('/login');
    const emailTab = page.getByRole('button', { name: 'Email' });
    if (await emailTab.isVisible()) {
      await emailTab.click();
    }
    await page.fill('#email', 'vivek@zinfog.com');
    await page.fill('#password', 'Caseno@123');
    await page.click('button[type="submit"]');

    await page.waitForURL('**/dashboard', { timeout: 15000 });

    // 2. Go to Family Members
    await page.goto('/members');
    await expect(page.locator('h1')).toContainText('Family Members');

    // 3. Fill and submit invitation form
    const uniqueEmail = `invite_test_${Date.now().toString().slice(-6)}@ozhzo.com`;
    await page.fill('#inviteEmail', uniqueEmail);
    await page.selectOption('#inviteRole', 'MEMBER');
    await page.click('button[type="submit"]');

    // 4. Verify Invitation Created Showcase Modal with Code
    const modal = page.getByRole('dialog', { name: 'Invitation Created' });
    await expect(modal).toBeVisible({ timeout: 10000 });
    await expect(modal.getByText(/Invitation Code/i)).toBeVisible();
    await expect(modal.getByText(/OZ-/i)).toBeVisible();

    // Verify Copy buttons inside modal
    const copyCodeModalBtn = modal.getByRole('button', { name: /Copy Code/i });
    if (await copyCodeModalBtn.isVisible()) {
      await copyCodeModalBtn.click();
      await expect(modal.getByText('Code Copied')).toBeVisible({ timeout: 5000 });
    }

    const doneBtn = modal.getByRole('button', { name: /Done/i });
    await doneBtn.click();
    await expect(modal).not.toBeVisible();

    // 5. Verify Pending Invitations List shows Code and Copy buttons
    const pendingSection = page.getByText(/Pending Invitations/i);
    await expect(pendingSection).toBeVisible();

    const inviteRow = page.locator('div').filter({ hasText: uniqueEmail }).first();
    await expect(inviteRow).toBeVisible();
    await expect(inviteRow.getByText(/Code:/i)).toBeVisible();
    await expect(inviteRow.getByText(/OZ-/i)).toBeVisible();

    // 6. Test Copy Code and Copy Link buttons in list
    const copyCodeBtn = inviteRow.getByRole('button', { name: /Copy Code/i });
    await expect(copyCodeBtn).toBeVisible();
    await copyCodeBtn.click();
    await expect(inviteRow.getByText('Code Copied')).toBeVisible({ timeout: 5000 });

    const copyLinkBtn = inviteRow.getByRole('button', { name: /Copy Link/i });
    await expect(copyLinkBtn).toBeVisible();
    await copyLinkBtn.click();
    await expect(inviteRow.getByText('Link Copied')).toBeVisible({ timeout: 5000 });

    // 7. Refresh page and verify Code is STILL visible in the DOM
    await page.reload();
    await expect(page.locator('h1')).toContainText('Family Members');

    const refreshedInviteRow = page.locator('div').filter({ hasText: uniqueEmail }).first();
    await expect(refreshedInviteRow).toBeVisible({ timeout: 10000 });
    await expect(refreshedInviteRow.getByText(/Code:/i)).toBeVisible();
    await expect(refreshedInviteRow.getByText(/OZ-/i)).toBeVisible();
    await expect(refreshedInviteRow.getByRole('button', { name: /Copy Code/i })).toBeVisible();
    await expect(refreshedInviteRow.getByRole('button', { name: /Copy Link/i })).toBeVisible();
  });

  test('4. Join Home by Code Flow (/join)', async ({ page }) => {
    await page.goto('/join');
    await expect(page.locator('h1')).toContainText('Join a Home Workspace');
    await expect(page.locator('#code')).toBeVisible();
    await expect(page.getByRole('button', { name: /Join Home/i })).toBeVisible();
  });

  test('5. Home Settings Danger Zone Delete Workspace Flow', async ({ page }) => {
    // 1. Log in
    await page.goto('/login');
    const emailTab = page.getByRole('button', { name: 'Email' });
    if (await emailTab.isVisible()) {
      await emailTab.click();
    }
    await page.fill('#email', 'vivek@zinfog.com');
    await page.fill('#password', 'Caseno@123');
    await page.click('button[type="submit"]');

    await page.waitForURL('**/dashboard', { timeout: 15000 });

    // 2. Go to /settings
    await page.goto('/settings');
    await expect(page.getByText('Danger Zone')).toBeVisible();
    await expect(page.getByRole('button', { name: /Delete This Home/i })).toBeVisible();
  });

});
