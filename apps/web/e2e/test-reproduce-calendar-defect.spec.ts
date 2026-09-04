import { test, expect } from '@playwright/test';

test.describe('Calendar Event Visibility UAT Defect Reproduction', () => {

  const homeId = '11111111-1111-1111-1111-111111111111';
  let createdEvents: any[] = [];

  test.beforeEach(async ({ page, context }) => {
    createdEvents = [];
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await context.clearCookies();

    await page.addInitScript(({ token, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('active_home_id', hId);
    }, { token: 'mock-valid-jwt-token', hId: homeId });

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
            display_name: 'Test User',
            mobile_verified: true,
            is_super_admin: false,
            system_role: 'USER',
            homes: [
              { home_id: homeId, name: 'Family Home', role: 'OWNER', status: 'ACTIVE' }
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
            { id: homeId, name: 'Family Home', currency: 'USD', role: 'OWNER', status: 'ACTIVE' }
          ]
        })
      });
    });

    // Mock /homes/{homeId}/events (POST create)
    await page.route(`**/api/v1/homes/${homeId}/events`, async (route) => {
      if (route.request().method() === 'POST') {
        const body = JSON.parse(route.request().postData() || '{}');
        const newEvent = {
          id: `event-${Date.now()}`,
          home_id: homeId,
          title: body.title,
          description: body.description || null,
          start_time: body.start_time,
          end_time: body.end_time,
          is_all_day: !!body.is_all_day,
          location: body.location || null,
          category_name: body.category_name || 'Family',
          status: 'CONFIRMED'
        };
        createdEvents.push(newEvent);

        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: newEvent,
            message: 'Event created successfully.'
          })
        });
      } else {
        await route.continue();
      }
    });

    // Mock /homes/{homeId}/calendar/projection (GET)
    await page.route(`**/api/v1/homes/${homeId}/calendar/projection*`, async (route) => {
      const url = new URL(route.request().url());
      console.log('[PROJECTION REQUEST URL]', url.toString());

      const timelineItems = createdEvents.map(e => ({
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
            total_events: timelineItems.length,
            total_tasks: 0,
            total_bills: 0
          }
        })
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

  test('Create Calendar event and verify it appears in Agenda and Month views', async ({ page }) => {
    // 1. Visit Calendar
    await page.goto('/calendar');
    await page.waitForLoadState('domcontentloaded');

    // 2. Add an event
    const titleInput = page.locator('input[placeholder*="Add event to family calendar"]');
    await expect(titleInput).toBeVisible();
    await titleInput.fill('Dentist Appointment with Dr. Smith');

    const submitBtn = page.getByRole('button', { name: /add event/i });
    await submitBtn.click();

    // 3. Verify toast message
    await expect(page.locator('role=status')).toContainText('Dentist Appointment with Dr. Smith');

    // 4. Verify event in Agenda view
    console.log('[ASSERTION] Checking Agenda view for event...');
    await expect(page.getByText('Dentist Appointment with Dr. Smith').first()).toBeVisible();

    // 5. Switch to Month View
    const monthViewBtn = page.getByRole('button', { name: /month view/i });
    await monthViewBtn.click();

    // 6. Verify event in Month view
    console.log('[ASSERTION] Checking Month view for event...');
    await expect(page.getByText('Dentist Appointment with Dr. Smith').first()).toBeVisible();
  });

});
