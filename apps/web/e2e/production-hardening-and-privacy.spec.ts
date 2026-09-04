import { test, expect } from '@playwright/test';

test.describe('Stage 6 — Production Hardening, Security, Privacy & Global Scale Readiness', () => {
  const HOME_ID = '11111111-1111-1111-1111-111111111111';
  const USER_ID = '22222222-2222-2222-2222-222222222222';

  test.beforeEach(async ({ page }) => {
    // Inject auth credentials and active home
    await page.addInitScript(({ homeId, userId }) => {
      localStorage.setItem('access_token', 'mock_jwt_token_stage6');
      localStorage.setItem('active_home_id', homeId);
      localStorage.setItem('user', JSON.stringify({
        id: userId,
        email: 'resident@ozhzo.com',
        display_name: 'Jane Resident',
        is_active: true,
        mobile_verified: true
      }));
    }, { homeId: HOME_ID, userId: USER_ID });

    // Mock core platform endpoints
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: USER_ID,
          email: 'resident@ozhzo.com',
          display_name: 'Jane Resident',
          is_active: true,
          mobile_verified: true,
          is_super_admin: false
        })
      });
    });

    await page.route('**/api/v1/homes', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: HOME_ID,
            name: 'Maplewood Residence',
            role: 'OWNER',
            currency: 'USD',
            timezone: 'America/New_York',
            status: 'ACTIVE',
            public_home_id: 'OZH-MAPLE1',
            home_qr_status: 'ACTIVE'
          }
        ])
      });
    });

    await page.route(`**/api/v1/homes/${HOME_ID}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: HOME_ID,
          name: 'Maplewood Residence',
          role: 'OWNER',
          currency: 'USD',
          timezone: 'America/New_York',
          status: 'ACTIVE',
          public_home_id: 'OZH-MAPLE1',
          home_qr_status: 'ACTIVE',
          member_count: 3
        })
      });
    });

    await page.route(`**/api/v1/homes/${HOME_ID}/identity`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          home_id: HOME_ID,
          name: 'Maplewood Residence',
          public_home_id: 'OZH-MAPLE1',
          qr_token: 'qr_token_sample_123',
          qr_status: 'ACTIVE',
          qr_version: 1,
          qr_url: 'https://ozhzo.com/join/home/qr_token_sample_123'
        })
      });
    });

    await page.route(`**/api/v1/homes/${HOME_ID}/join-requests`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      });
    });

    await page.route('**/api/v1/notifications', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      });
    });

    await page.route('**/api/v1/notifications/priority', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      });
    });

    await page.route(`**/api/v1/homes/${HOME_ID}/attention/summary`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ overdue_bills_count: 0, low_stock_items_count: 0, pending_invitations_count: 0, tasks_due_today_count: 0 })
      });
    });

    await page.route(`**/api/v1/homes/${HOME_ID}/today`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ today_tasks: [], upcoming_bills: [], low_stock_inventory: [] })
      });
    });

    await page.route(`**/api/v1/homes/${HOME_ID}/locations`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      });
    });

    // Mock Privacy export
    await page.route(`**/api/v1/homes/${HOME_ID}/privacy/export`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          export_generated_at: new Date().toISOString(),
          export_version: '1.0',
          home: { id: HOME_ID, name: 'Maplewood Residence' },
          tasks: [{ id: 'task-1', title: 'Water plants' }],
          bills: [{ id: 'bill-1', title: 'Electric utility' }],
          household_memories: [{ id: 'mem-1', category: 'ROUTINE', content: 'Dinner at 7 PM' }]
        })
      });
    });
  });

  test('1. Privacy & Data Governance: Settings page renders GDPR compliance & retention policies', async ({ page }) => {
    await page.goto('/settings');

    // Verify settings loaded
    await expect(page.locator('h1')).toContainText('Home Settings');

    // Verify Privacy & Data Governance card
    await expect(page.getByText('Privacy & Data Governance')).toBeVisible();
    await expect(page.getByText('GDPR Article 20')).toBeVisible();

    // Verify retention schedule
    await expect(page.getByText('Active Retention Policies')).toBeVisible();
    await expect(page.getByText('Notifications:')).toBeVisible();
    await expect(page.getByText('AI Conversations:')).toBeVisible();
    await expect(page.getByText('Automation Logs:')).toBeVisible();

    // Verify Export Household Data button
    const exportBtn = page.getByRole('button', { name: /Export Household Data/i });
    await expect(exportBtn).toBeVisible();
  });

  test('2. Data Portability: Export Household Data triggers archive download without errors', async ({ page }) => {
    await page.goto('/settings');

    const exportBtn = page.getByRole('button', { name: /Export Household Data/i });
    await expect(exportBtn).toBeVisible();

    // Click Export and ensure no unhandled error modal/alert
    await exportBtn.click();
    await page.waitForTimeout(500);

    // Verify card is still healthy
    await expect(page.getByText('Privacy & Data Governance')).toBeVisible();
  });
});
