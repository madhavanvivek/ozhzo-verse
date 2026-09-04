import { test, expect } from '@playwright/test';

test.describe('Stage 3 AI Intelligence & Household Assistant E2E Suite', () => {

  const homeAId = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
  const homeBId = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb';

  test.beforeEach(async ({ page, context }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await context.clearCookies();
  });

  const setupMockRoutes = async (page: any, initialHomeId = homeAId) => {
    await page.addInitScript(({ token, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('active_home_id', hId);
      localStorage.setItem('user_info', JSON.stringify({
        id: 'user-001',
        email: 'host@ozhzo.com',
        display_name: 'Resident Host',
        mobile_verified: true,
      }));
    }, { token: 'mock-user-jwt', hId: initialHomeId });

    // 1. Current User
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'user-001',
            email: 'host@ozhzo.com',
            display_name: 'Resident Host',
            mobile_verified: true,
            free_home_consumed: true,
            is_super_admin: false,
            system_role: 'USER',
            homes: [
              { home_id: homeAId, name: 'Madhavan Residence', role: 'OWNER', status: 'ACTIVE' },
              { home_id: homeBId, name: 'Mountain Retreat', role: 'MEMBER', status: 'ACTIVE' }
            ]
          }
        })
      });
    });

    // 2. Homes List
    await page.route('**/api/v1/homes', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { id: homeAId, name: 'Madhavan Residence', currency: 'INR', role: 'OWNER', status: 'ACTIVE' },
            { id: homeBId, name: 'Mountain Retreat', currency: 'USD', role: 'MEMBER', status: 'ACTIVE' }
          ]
        })
      });
    });

    // 3. Members List
    await page.route(`**/api/v1/homes/*/members*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { id: 'mem-1', user_id: 'user-001', display_name: 'Resident Host', email: 'host@ozhzo.com', role: 'OWNER', status: 'ACTIVE' },
            { id: 'mem-2', user_id: 'user-002', display_name: 'Partner Alex', email: 'alex@ozhzo.com', role: 'MEMBER', status: 'ACTIVE' }
          ]
        })
      });
    });

    // 4. Notifications & Priority Alerts
    await page.route(`**/api/v1/notifications*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { items: [], total: 0, unread_count: 0, unresolved_action_count: 0 }
        })
      });
    });

    // 5. Locations
    await page.route(`**/api/v1/homes/*/locations*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [{ id: 'loc-1', name: 'Kitchen Pantry', type: 'ROOM', children: [] }]
        })
      });
    });

    await page.route(`**/api/v1/homes/*/location-types*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [{ name: 'Room', code: 'ROOM', is_system_default: true }]
        })
      });
    });

    await page.route(`**/api/v1/homes/*/attention/summary*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { total_attention_count: 0, has_critical: false }
        })
      });
    });

    await page.route(`**/api/v1/homes/*/today*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { tasks_due_today: [], bills_due_today: [], events_today: [] }
        })
      });
    });

    // 6. Dashboard Aggregation for Home A & Home B
    await page.route(`**/api/v1/homes/${homeAId}/dashboard*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            greeting: { title: 'Welcome', subtitle: 'Madhavan Residence' },
            summary: {
              home_name: 'Madhavan Residence',
              currency: 'INR',
              active_tasks_count: 1,
              due_today_tasks_count: 1,
              overdue_tasks_count: 0,
              unpaid_bills_count: 1,
              unpaid_bills_amount: '999.00',
              low_stock_count: 1,
              members_count: 2
            },
            attention_summary: { total_attention_count: 1, has_critical: false },
            attention_items: [],
            today_timeline: [],
            recent_activity: [],
            pending_tasks: [{ id: 'task-1', title: 'Clean Water Filter', priority: 'NORMAL', status: 'TODO' }],
            upcoming_bills: [{ id: 'bill-1', title: 'Fiber Internet', amount: 999.00, currency: 'INR', due_date: new Date().toISOString(), status: 'UNPAID' }],
            upcoming_events: [],
            low_stock_inventory: [{ id: 'inv-1', name: 'Olive Oil', quantity: '0.500', unit: 'bottle', status: 'LOW_STOCK' }],
            shopping_items: [{ id: 'purch-1', name: 'Whole Wheat Flour', quantity: '5.000', unit: 'kg', is_checked: false }],
            notifications: [],
            role: 'OWNER'
          }
        })
      });
    });

    await page.route(`**/api/v1/homes/${homeBId}/dashboard*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            greeting: { title: 'Welcome', subtitle: 'Mountain Retreat' },
            summary: {
              home_name: 'Mountain Retreat',
              currency: 'USD',
              active_tasks_count: 0,
              due_today_tasks_count: 0,
              overdue_tasks_count: 0,
              unpaid_bills_count: 0,
              unpaid_bills_amount: '0.00',
              low_stock_count: 0,
              members_count: 1
            },
            attention_summary: { total_attention_count: 0, has_critical: false },
            attention_items: [],
            today_timeline: [],
            recent_activity: [],
            pending_tasks: [],
            upcoming_bills: [],
            upcoming_events: [],
            low_stock_inventory: [],
            shopping_items: [],
            notifications: [],
            role: 'MEMBER'
          }
        })
      });
    });

    // 7. Stage 3 AI Chat Endpoint Mock
    await page.route(`**/api/v1/homes/*/ai/chat`, async (route) => {
      const requestData = JSON.parse(route.request().postData() || '{}');
      const msg = (requestData.message || requestData.prompt || '').toLowerCase();

      if (msg.includes('shopping') || msg.includes('milk') || msg.includes('flour')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              message: "I have prepared the action for **Madhavan Residence**: Add 1 item of Organic Milk to household purchase list. Please confirm below to execute it.",
              detected_intent: "ADD_SHOPPING_ITEM",
              intent_confidence: 0.95,
              action_proposal: {
                id: "prop-shop-101",
                action_type: "ADD_SHOPPING_ITEM",
                title: "Add to Shopping List: Organic Milk",
                description: "Add 1 item of Organic Milk to the household purchase list.",
                params: { item_name: "Organic Milk", quantity: 1, unit: "bottle" },
                requires_confirmation: true
              },
              suggested_quick_replies: ["What's due today?", "Show shopping list"]

            }
          })
        });
      } else if (msg.includes('task') || msg.includes('chores') || msg.includes("due today")) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              message: "Here are the active tasks for **Madhavan Residence**:\n\n• **Clean Water Filter** (Priority: NORMAL)\n\nWould you like me to assign or complete any of these?",
              detected_intent: "QUERY_TASKS",
              intent_confidence: 0.95,
              action_proposal: null,
              suggested_quick_replies: ["What bills are due?", "+ Add to shopping", "Check low stock"]
            }
          })
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              message: "Hello! I am your Ozhzo Household Assistant for **Madhavan Residence**. How can I assist you today?",
              detected_intent: "GENERAL_HOUSEHOLD_QUERY",
              intent_confidence: 0.90,
              action_proposal: null,
              suggested_quick_replies: ["What's due today?", "What bills are due?", "Check pantry stock"]
            }
          })
        });
      }
    });

    // 8. Stage 3 AI Action Confirmation Endpoint Mock
    await page.route(`**/api/v1/homes/*/ai/actions/*/confirm`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            success: true,
            action_id: 'prop-shop-101',
            action_type: 'ADD_SHOPPING_ITEM',
            executed_entity_id: 'purch-new-999',
            message: "Added 'Organic Milk' (1.000 bottle) to your shopping list.",
            audit_log_id: 'audit-001'
          }
        })
      });
    });

    // 9. Stage 3 AI Action Rejection Endpoint Mock
    await page.route(`**/api/v1/homes/*/ai/actions/*/reject`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            status: 'REJECTED',
            action_id: 'prop-shop-101'
          }
        })
      });
    });
  };

  test('1. AI Assistant Widget: Opens from header and displays contextual household welcome', async ({ page }) => {
    await setupMockRoutes(page, homeAId);

    await page.goto('/dashboard');
    await expect(page.getByText('Madhavan Residence').first()).toBeVisible();

    // Click AI Assistant button in header
    const assistantBtn = page.locator('button[aria-label="Open AI Assistant"]').first();
    await expect(assistantBtn).toBeVisible();
    await assistantBtn.click();

    // AI Assistant dialog should be visible
    const assistantDialog = page.locator('div[role="dialog"][aria-label="AI Household Assistant"]');
    await expect(assistantDialog).toBeVisible();
    await expect(assistantDialog).toContainText('Ozhzo Assistant');
    await expect(assistantDialog).toContainText('Madhavan Residence');
    await expect(assistantDialog).toContainText("What's due today?");
  });

  test('2. Read Query: Asking "What\'s due today?" returns active chores contextual response', async ({ page }) => {
    await setupMockRoutes(page, homeAId);

    await page.goto('/dashboard');
    await page.locator('button[aria-label="Open AI Assistant"]').first().click();

    // Click quick reply pill "What's due today?"
    const chipBtn = page.locator('button:has-text("What\'s due today?")').first();
    await chipBtn.click();

    // Response should render in chat stream
    const assistantDialog = page.locator('div[role="dialog"][aria-label="AI Household Assistant"]');
    await expect(assistantDialog).toContainText('Clean Water Filter');
    await expect(assistantDialog).toContainText('NORMAL');
  });

  test('3. Write Action: Adding shopping item generates Action Proposal and executes upon confirmation', async ({ page }) => {
    await setupMockRoutes(page, homeAId);

    await page.goto('/dashboard');
    await page.locator('button[aria-label="Open AI Assistant"]').first().click();

    // Type command in input
    const input = page.locator('input[aria-label="Assistant message input"]');
    await input.fill('Add Organic Milk to shopping list');
    await page.locator('button[aria-label="Send message"]').click();

    // Action Proposal Card should appear
    const assistantDialog = page.locator('div[role="dialog"][aria-label="AI Household Assistant"]');
    await expect(assistantDialog).toContainText('Add to Shopping List: Organic Milk');
    await expect(assistantDialog).toContainText('ADD_SHOPPING_ITEM');

    // Click Confirm Action
    const confirmBtn = page.locator('button:has-text("Confirm Action")').first();
    await expect(confirmBtn).toBeVisible();
    await confirmBtn.click();

    // Verification of execution
    await expect(assistantDialog).toContainText("Added 'Organic Milk'");
  });

  test('4. Action Proposal Rejection: Cancelling proposal dismisses action cleanly', async ({ page }) => {
    await setupMockRoutes(page, homeAId);

    await page.goto('/dashboard');
    await page.locator('button[aria-label="Open AI Assistant"]').first().click();

    // Send shopping item request
    const input = page.locator('input[aria-label="Assistant message input"]');
    await input.fill('Add Milk to shopping');
    await page.locator('button[aria-label="Send message"]').click();

    // Cancel the action proposal
    const cancelBtn = page.locator('button:has-text("Cancel")').first();
    await expect(cancelBtn).toBeVisible();
    await cancelBtn.click();


    const assistantDialog = page.locator('div[role="dialog"][aria-label="AI Household Assistant"]');
    await expect(assistantDialog).toContainText('Action cancelled');
  });
});
