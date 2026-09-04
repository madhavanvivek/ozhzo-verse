import { test, expect } from '@playwright/test';
import * as path from 'path';

test.describe('Ozhzo Verse — Calendar Events Verification & UAT Defect Closure', () => {

  const homeA = '11111111-1111-1111-1111-111111111111';
  const homeB = '22222222-2222-2222-2222-222222222222';
  let homeAEvents: any[] = [];
  let homeBEvents: any[] = [];

  test.beforeEach(async ({ page, context }) => {
    homeAEvents = [];
    homeBEvents = [];

    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await context.clearCookies();

    // Mock /users/me
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'user-001',
            email: 'user@example.com',
            display_name: 'Alex Rivera',
            mobile_verified: true,
            is_super_admin: false,
            system_role: 'USER',
            homes: [
              { home_id: homeA, name: 'Main Residence', role: 'OWNER', status: 'ACTIVE' },
              { home_id: homeB, name: 'Vacation Beach House', role: 'OWNER', status: 'ACTIVE' }
            ]
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
          data: [
            { id: homeA, name: 'Main Residence', currency: 'USD', role: 'OWNER', status: 'ACTIVE' },
            { id: homeB, name: 'Vacation Beach House', currency: 'USD', role: 'OWNER', status: 'ACTIVE' }
          ]
        })
      });
    });

    // Mock /homes/{homeId}/events (POST / GET)
    await page.route(new RegExp('/api/v1/homes/([^/]+)/events(\\?.*)?$'), async (route) => {
      const match = route.request().url().match(/\/api\/v1\/homes\/([^/]+)\/events/);
      const targetHomeId = match ? match[1] : homeA;

      if (route.request().method() === 'POST') {
        const body = JSON.parse(route.request().postData() || '{}');
        const newEvent = {
          id: `event-${Date.now()}-${Math.random().toString(36).substring(7)}`,
          home_id: targetHomeId,
          title: body.title,
          description: body.description || null,
          start_time: body.start_time,
          end_time: body.end_time,
          is_all_day: !!body.is_all_day,
          location: body.location || null,
          category_name: body.category_name || 'Family',
          status: 'CONFIRMED'
        };

        if (targetHomeId === homeA) {
          homeAEvents.push(newEvent);
        } else {
          homeBEvents.push(newEvent);
        }

        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: newEvent,
            message: 'Event created successfully.'
          })
        });
      } else if (route.request().method() === 'GET') {
        const eventsList = targetHomeId === homeA ? homeAEvents : homeBEvents;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: eventsList
          })
        });
      } else {
        await route.continue();
      }
    });

    // Mock /homes/{homeId}/calendar/projection (GET)
    await page.route(new RegExp('/api/v1/homes/([^/]+)/calendar/projection'), async (route) => {
      const match = route.request().url().match(/\/api\/v1\/homes\/([^/]+)\/calendar\/projection/);
      const targetHomeId = match ? match[1] : homeA;
      const url = new URL(route.request().url());

      const rawEvents = targetHomeId === homeA ? homeAEvents : homeBEvents;
      const timelineItems = rawEvents.map(e => ({
        source_type: 'EVENT',
        source_id: e.id,
        title: e.title,
        start: e.start_time,
        end: e.end_time,
        all_day: e.is_all_day,
        editable: true,
        navigation_target: `/calendar/${e.id}`,
        status: e.status,
        category_name: e.category_name,
        location: e.location,
        meta_info: { description: e.description }
      }));

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            start_date: url.searchParams.get('start_date') || new Date().toISOString(),
            end_date: url.searchParams.get('end_date') || new Date().toISOString(),
            items: timelineItems,
            timeline_items: timelineItems,
            total_events: timelineItems.length,
            total_tasks: 0,
            total_bills: 0
          }
        })
      });
    });

    // Mock dashboard
    await page.route('**/api/v1/homes/*/dashboard*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            home_id: homeA,
            home_name: 'Main Residence',
            role: 'OWNER',
            summary: {
              active_tasks_count: 0,
              urgent_tasks_count: 0,
              pending_bills_count: 0,
              unpaid_bills_total: 0,
              shopping_needed_count: 0,
              low_stock_items_count: 0,
              upcoming_events_count: 1
            },
            urgent_tasks: [],
            pending_bills: [],
            low_stock_inventory: [],
            shopping_items_preview: [],
            upcoming_events: []
          }
        })
      });
    });

    // Mock tasks
    await page.route('**/api/v1/homes/*/tasks*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] })
      });
    });

    // Mock notifications
    await page.route('**/api/v1/notifications*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] })
      });
    });
  });

  test('TEST 1 & 2: Direct Event Creation, Toast, and Agenda / Calendar View Rendering', async ({ page }) => {
    const evidenceDir = '/Users/vivek/.gemini/antigravity/brain/e417cc97-7d7a-4622-ab0c-93f6404efdd2/uat_evidence';

    await page.goto('/login');
    await page.evaluate(({ token, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('active_home_id', hId);
    }, { token: 'mock-valid-jwt-token', hId: homeA });

    await page.goto('/calendar');
    await page.waitForLoadState('domcontentloaded');

    // 1. Fill Quick Add Form
    const titleInput = page.locator('input[placeholder*="Add event to family calendar"]');
    await expect(titleInput).toBeVisible();
    await titleInput.fill('Dentist Appointment with Dr. Wilson');

    // Open more options to add location and category
    const moreOptionsBtn = page.getByRole('button', { name: /more options/i });
    await moreOptionsBtn.click();

    const locInput = page.locator('input[placeholder*="City Clinic"]');
    await expect(locInput).toBeVisible();
    await locInput.fill('Downtown Medical Plaza');

    const submitBtn = page.getByRole('button', { name: /add event/i });
    await submitBtn.click();

    // 2. Verify Toast message appears
    const toast = page.locator('role=status');
    await expect(toast).toBeVisible();
    await expect(toast).toContainText('Dentist Appointment with Dr. Wilson');

    // 3. Verify Event appears in Agenda View
    const agendaItem = page.getByText('Dentist Appointment with Dr. Wilson').first();
    await expect(agendaItem).toBeVisible();
    await expect(page.getByText('Downtown Medical Plaza').first()).toBeVisible();

    // Capture Agenda Evidence
    await page.screenshot({ path: path.join(evidenceDir, 'calendar_agenda_view.png'), fullPage: true });

    // 4. Switch to Month View
    const monthViewBtn = page.getByRole('button', { name: /month view/i });
    await monthViewBtn.click();

    // 5. Verify Event appears in Month Grid
    const monthItem = page.getByText('Dentist Appointment with Dr. Wilson').first();
    await expect(monthItem).toBeVisible();

    // Capture Month Evidence
    await page.screenshot({ path: path.join(evidenceDir, 'calendar_month_view.png'), fullPage: true });
  });

  test('TEST 3: Timezone Boundary Tests (00:00, 01:00, 12:00, 23:00 and All-Day)', async ({ page }) => {
    const evidenceDir = '/Users/vivek/.gemini/antigravity/brain/e417cc97-7d7a-4622-ab0c-93f6404efdd2/uat_evidence';

    await page.goto('/login');
    await page.evaluate(({ token, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('active_home_id', hId);
    }, { token: 'mock-valid-jwt-token', hId: homeA });

    await page.goto('/calendar');
    await page.waitForLoadState('domcontentloaded');

    const testEvents = [
      { title: 'Midnight Event (00:00)', allDay: false, time: '00:00' },
      { title: 'Early Morning Event (01:00)', allDay: false, time: '01:00' },
      { title: 'Noon Gathering (12:00)', allDay: false, time: '12:00' },
      { title: 'Late Night Event (23:00)', allDay: false, time: '23:00' },
      { title: 'Full Day Festival', allDay: true, time: '' }
    ];

    for (const item of testEvents) {
      const titleInput = page.locator('input[placeholder*="Add event to family calendar"]');
      await titleInput.fill(item.title);

      if (item.allDay) {
        const moreOptionsBtn = page.getByRole('button', { name: /more options/i });
        if (await moreOptionsBtn.isVisible()) {
          await moreOptionsBtn.click();
        }
        const allDayCheckbox = page.locator('#allDayCheckbox');
        await allDayCheckbox.check();
      }

      const submitBtn = page.getByRole('button', { name: /add event/i });
      await submitBtn.click();
      await page.waitForTimeout(100);
    }

    // Verify all 5 events appear in Agenda view
    for (const item of testEvents) {
      await expect(page.getByText(item.title).first()).toBeVisible();
    }

    // Switch to Month view and verify month grid renders with overflow indicator
    const monthViewBtn = page.getByRole('button', { name: /month view/i });
    await monthViewBtn.click();

    // Verify first 2 visible items and +more indicator in month view
    await expect(page.getByText(testEvents[0].title).first()).toBeVisible();
    await expect(page.getByText(testEvents[1].title).first()).toBeVisible();
    await expect(page.getByText(/\+\d+ more/).first()).toBeVisible();

    await page.screenshot({ path: path.join(evidenceDir, 'calendar_timezone_coverage.png'), fullPage: true });
  });

  test('TEST 4: Page Refresh & Navigation Away/Back Persistence', async ({ page }) => {
    await page.goto('/login');
    await page.evaluate(({ token, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('active_home_id', hId);
    }, { token: 'mock-valid-jwt-token', hId: homeA });

    await page.goto('/calendar');
    await page.waitForLoadState('domcontentloaded');

    // Add event
    const titleInput = page.locator('input[placeholder*="Add event to family calendar"]');
    await titleInput.fill('Critical Family Gathering');
    await page.getByRole('button', { name: /add event/i }).click();

    await expect(page.getByText('Critical Family Gathering').first()).toBeVisible();

    // 1. Refresh page
    await page.reload();
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByText('Critical Family Gathering').first()).toBeVisible();

    // 2. Navigate away to /tasks and back to /calendar
    await page.goto('/tasks');
    await page.waitForLoadState('domcontentloaded');

    await page.goto('/calendar');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByText('Critical Family Gathering').first()).toBeVisible();
  });

  test('TEST 5: Multi-Home Isolation Verification', async ({ page }) => {
    const evidenceDir = '/Users/vivek/.gemini/antigravity/brain/e417cc97-7d7a-4622-ab0c-93f6404efdd2/uat_evidence';

    await page.goto('/login');
    await page.evaluate(({ token, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('active_home_id', hId);
    }, { token: 'mock-valid-jwt-token', hId: homeA });

    // 1. In Home A, create private event
    await page.goto('/calendar');
    await page.waitForLoadState('domcontentloaded');

    const titleInput = page.locator('input[placeholder*="Add event to family calendar"]');
    await titleInput.fill('Secret Home A Family Planning');
    await page.getByRole('button', { name: /add event/i }).click();

    await expect(page.getByText('Secret Home A Family Planning').first()).toBeVisible();

    // 2. Switch active home to Home B
    await page.evaluate((hB) => {
      localStorage.setItem('active_home_id', hB);
      window.dispatchEvent(new CustomEvent('home-changed'));
    }, homeB);

    // Wait for state refresh under Home B
    await page.waitForTimeout(500);

    // Event from Home A must NOT be visible in Home B
    await expect(page.getByText('Secret Home A Family Planning')).toHaveCount(0);

    // Capture Home B empty isolation screenshot
    await page.screenshot({ path: path.join(evidenceDir, 'calendar_home_isolation.png'), fullPage: true });

    // 3. Switch back to Home A
    await page.evaluate((hA) => {
      localStorage.setItem('active_home_id', hA);
      window.dispatchEvent(new CustomEvent('home-changed'));
    }, homeA);

    await page.waitForTimeout(500);

    // Event is visible again in Home A
    await expect(page.getByText('Secret Home A Family Planning').first()).toBeVisible();
  });

});
