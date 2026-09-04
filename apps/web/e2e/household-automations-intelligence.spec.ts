import { test, expect } from '@playwright/test';

test.describe('Stage 4 — Household Automations & Predictive Intelligence', () => {
  const homeId = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';

  test.beforeEach(async ({ page, context }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await context.clearCookies();

    // Set auth tokens in localStorage
    await page.addInitScript(
      ({ token, hId }) => {
        localStorage.setItem('access_token', token);
        localStorage.setItem('active_home_id', hId);
        localStorage.setItem(
          'user_info',
          JSON.stringify({
            id: 'user-stage4-admin',
            email: 'admin@ozhzo.com',
            display_name: 'Stage 4 Admin',
            mobile_verified: true,
          })
        );
      },
      { token: 'mock-token-stage4', hId: homeId }
    );

    // Mock Users Me
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'user-stage4-admin',
            email: 'admin@ozhzo.com',
            display_name: 'Stage 4 Admin',
            mobile_verified: true,
            free_home_consumed: true,
            is_super_admin: false,
            system_role: 'USER',
            homes: [{ home_id: homeId, name: 'Ozhzo Smart Home', role: 'OWNER', status: 'ACTIVE' }],
          },
        }),
      });
    });

    // Mock Homes
    await page.route('**/api/v1/homes', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [{ id: homeId, name: 'Ozhzo Smart Home', currency: 'INR', role: 'OWNER', status: 'ACTIVE' }],
        }),
      });
    });

    // Mock Notifications
    await page.route('**/api/v1/notifications*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { items: [], unread_count: 0, critical_count: 0, high_count: 0, action_required_count: 0 },
        }),
      });
    });

    // Mock Intelligence Dashboard API
    await page.route(`**/api/v1/homes/${homeId}/intelligence/dashboard`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            home_name: 'Ozhzo Smart Home',
            active_automations_count: 2,
            total_automations_count: 3,
            recent_executions_count: 5,
            failed_automations_count: 0,
            active_automations: [
              {
                id: 'auto-1',
                home_id: homeId,
                name: 'Auto Restock Whole Milk',
                description: 'Add milk to shopping list when quantity is below 2 bottles',
                enabled: true,
                trigger_type: 'INVENTORY_LOW',
                conditions: { operator: 'AND', rules: [{ field: 'quantity', op: 'LESS_THAN', value: 2.0 }] },
                actions: [{ action_type: 'ADD_SHOPPING_ITEM', params: { name: 'Whole Milk', quantity: 1 } }],
                schedule: {},
                execution_policy: {},
                status: 'ACTIVE',
                failure_count: 0,
                consecutive_failures: 0,
                created_at: new Date().toISOString(),
              },
              {
                id: 'auto-2',
                home_id: homeId,
                name: 'Electricity Bill Payment Reminder',
                description: 'Creates high priority task 3 days before electricity bill is due',
                enabled: false,
                trigger_type: 'BILL_APPROACHING',
                conditions: {},
                actions: [{ action_type: 'CREATE_TASK', params: { title: 'Pay Electricity Bill', priority: 'HIGH' } }],
                schedule: {},
                execution_policy: {},
                status: 'PAUSED',
                failure_count: 0,
                consecutive_failures: 0,
                created_at: new Date().toISOString(),
              },
            ],
            recent_executions: [
              {
                id: 'exec-1',
                automation_id: 'auto-1',
                trigger_event: { source: 'INVENTORY_CHANGE', quantity: 1.0 },
                evaluated_conditions: { result: true },
                actions_attempted: 1,
                actions_succeeded: 1,
                actions_failed: 0,
                duration_ms: 24,
                status: 'SUCCESS',
                error_details: 'Added Whole Milk to purchase list',
                created_at: new Date().toISOString(),
              },
            ],
            recommendations: [
              {
                id: 'rec-1',
                domain: 'INVENTORY',
                title: 'Restock Olive Oil',
                reason: 'Olive Oil has only 0.5 bottle remaining in the pantry.',
                confidence: 0.95,
                source_category: 'LOW_STOCK_ALERT',
                suggested_action: { action_type: 'ADD_SHOPPING_ITEM', params: { name: 'Olive Oil' } },
                status: 'NEW',
              },
            ],
            predicted_patterns: [
              {
                pattern_type: 'CONSUMPTION_CYCLE',
                insight: 'Pantry items are restocked on average every 7 to 10 days.',
                confidence: 0.92,
              },
              {
                pattern_type: 'UTILITY_BILL_CYCLE',
                insight: 'Utility bills are concentrated between 5th and 15th of the month.',
                confidence: 0.96,
              },
            ],
          },
        }),
      });
    });

    // Mock AI Propose API
    await page.route(`**/api/v1/homes/${homeId}/ai/automations/propose`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            name: 'Auto-Restock Milk',
            description: 'Automatically adds Milk to the shopping list when stock drops below threshold.',
            trigger_type: 'INVENTORY_LOW',
            conditions: { operator: 'AND', rules: [{ field: 'quantity', op: 'LESS_THAN', value: 2.0 }] },
            actions: [{ action_type: 'ADD_SHOPPING_ITEM', params: { name: 'Milk', quantity: 1, unit: 'bottle' } }],
            schedule: null,
            explanation: 'When inventory quantity of Milk drops below 2.0, an item will be added to the shopping list.',
            requires_confirmation: true,
          },
        }),
      });
    });

    // Mock Automation Create API
    await page.route(`**/api/v1/homes/${homeId}/automations`, async (route) => {
      if (route.request().method() === 'POST') {
        const body = JSON.parse(route.request().postData() || '{}');
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              id: 'auto-created-new',
              home_id: homeId,
              name: body.name || 'New Rule',
              description: body.description || '',
              enabled: true,
              trigger_type: body.trigger_type || 'INVENTORY_LOW',
              conditions: body.conditions || {},
              actions: body.actions || [],
              schedule: body.schedule || {},
              execution_policy: {},
              status: 'ACTIVE',
              failure_count: 0,
              consecutive_failures: 0,
              created_at: new Date().toISOString(),
            },
          }),
        });
      } else {
        await route.continue();
      }
    });

    // Mock Run API
    await page.route(`**/api/v1/homes/${homeId}/automations/*/run`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'exec-manual-1',
            automation_id: 'auto-1',
            status: 'SUCCESS',
            actions_attempted: 1,
            actions_succeeded: 1,
            actions_failed: 0,
            duration_ms: 18,
            created_at: new Date().toISOString(),
          },
        }),
      });
    });
  });

  test('should render automations dashboard and KPI metrics', async ({ page }) => {
    await page.goto('/automations');

    await expect(page.locator('h1')).toContainText('Household Automations & Insights');
    await expect(page.getByText('Stage 4 Intelligence')).toBeVisible();

    // KPI verification
    await expect(page.getByText('Active Rules')).toBeVisible();
    await expect(page.getByText('Recent Executions')).toBeVisible();
    await expect(page.getByText('Proactive Insights')).toBeVisible();
    await expect(page.getByText('Optimal')).toBeVisible();

    // Automation cards
    await expect(page.getByText('Auto Restock Whole Milk')).toBeVisible();
    await expect(page.getByText('Electricity Bill Payment Reminder')).toBeVisible();
  });

  test('should switch tabs and display predictive insights and patterns', async ({ page }) => {
    await page.goto('/automations');

    // Click Predictive Insights tab
    await page.getByRole('button', { name: /Predictive Insights/i }).click();

    await expect(page.getByText('Detected Household Cycles & Patterns')).toBeVisible();
    await expect(page.getByText('CONSUMPTION_CYCLE')).toBeVisible();
    await expect(page.getByText('UTILITY_BILL_CYCLE')).toBeVisible();

    // Actionable recommendations
    await expect(page.getByText('Restock Olive Oil')).toBeVisible();
    await expect(page.getByRole('button', { name: /Accept & Execute/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Dismiss/i })).toBeVisible();
  });

  test('should switch to execution history tab and show immutable audit trail', async ({ page }) => {
    await page.goto('/automations');

    // Click Execution History tab
    await page.getByRole('button', { name: /Execution History/i }).click();

    await expect(page.getByText('Immutable Execution Trail')).toBeVisible();
    await expect(page.getByText('SUCCESS')).toBeVisible();
    await expect(page.getByText('24ms')).toBeVisible();
  });

  test('should support AI automation proposal generation and confirmation', async ({ page }) => {
    await page.goto('/automations');

    // Open AI Generator modal
    await page.getByRole('button', { name: /AI Rule Generator/i }).click();
    await expect(page.getByText('AI Automation Generator')).toBeVisible();

    // Enter natural language prompt
    const textarea = page.getByPlaceholder(/Whenever milk is low/i);
    await textarea.fill('Whenever milk runs low in pantry, add it to shopping list');

    // Click Generate Rule
    await page.getByRole('button', { name: /Generate Automation Rule/i }).click();

    // Verify structured proposal preview
    await expect(page.getByText('Auto-Restock Milk')).toBeVisible();
    await expect(page.getByText(/When inventory quantity of Milk drops below 2.0/i)).toBeVisible();

    // Confirm and create
    await page.getByRole('button', { name: /Confirm & Create Rule/i }).click();

    // Modal closes
    await expect(page.getByText('AI Automation Generator')).not.toBeVisible();
  });
});
