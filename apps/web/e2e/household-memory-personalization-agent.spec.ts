import { test, expect } from '@playwright/test';

test.describe('Stage 5 — Household Memory, Personalization & Advanced AI Agent', () => {
  const homeId = '55555555-5555-5555-5555-555555555555';

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
            id: 'user-stage5-host',
            email: 'host@ozhzo.com',
            display_name: 'Stage 5 Host',
            mobile_verified: true,
          })
        );
      },
      { token: 'mock-token-stage5', hId: homeId }
    );

    // Mock Users Me
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'user-stage5-host',
            email: 'host@ozhzo.com',
            display_name: 'Stage 5 Host',
            mobile_verified: true,
            free_home_consumed: true,
            is_super_admin: false,
            system_role: 'USER',
            homes: [{ home_id: homeId, name: 'Maplewood Residence', role: 'OWNER', status: 'ACTIVE' }],
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
          data: [{ id: homeId, name: 'Maplewood Residence', currency: 'INR', role: 'OWNER', status: 'ACTIVE' }],
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
          data: { items: [], total: 0, unread_count: 0, unresolved_action_count: 0 },
        }),
      });
    });

    // Mock Dashboard
    await page.route(`**/api/v1/homes/${homeId}/dashboard*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            greeting: { title: 'Welcome', subtitle: 'Maplewood Residence' },
            summary: {
              home_name: 'Maplewood Residence',
              currency: 'INR',
              active_tasks_count: 2,
              due_today_tasks_count: 1,
              overdue_tasks_count: 0,
              unpaid_bills_count: 1,
              unpaid_bills_amount: '1500.00',
              low_stock_count: 1,
              members_count: 3
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
            role: 'OWNER'
          }
        })
      });
    });

    // Intercept Stage 5 Memories
    await page.route(`**/api/v1/homes/${homeId}/memories*`, async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [
              {
                id: 'mem-001',
                home_id: homeId,
                category: 'PREFERENCE',
                content: 'Prefers reminders 1 day before bill due dates',
                source: 'USER_PROVIDED',
                confidence: 1.0,
                status: 'ACTIVE',
                created_at: new Date().toISOString()
              },
              {
                id: 'mem-002',
                home_id: homeId,
                category: 'ROUTINE',
                content: 'Family shops for groceries on Saturday mornings',
                source: 'SYSTEM_INFERRED',
                confidence: 0.92,
                status: 'ACTIVE',
                created_at: new Date().toISOString()
              }
            ]
          })
        });
      } else if (route.request().method() === 'POST') {
        const body = route.request().postDataJSON();
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              id: 'mem-new-123',
              home_id: homeId,
              category: body.category || 'PREFERENCE',
              content: body.content,
              source: 'USER_PROVIDED',
              confidence: 1.0,
              status: 'ACTIVE',
              created_at: new Date().toISOString()
            }
          })
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data: { status: 'DELETED' } })
        });
      }
    });

    // Intercept Personalization Preferences
    await page.route(`**/api/v1/homes/${homeId}/personalization`, async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              id: 'pref-001',
              user_id: 'user-stage5-host',
              home_id: homeId,
              personalization_enabled: true,
              ai_memory_enabled: true,
              reminder_timing_preference: '1_DAY_BEFORE',
              recommendation_frequency: 'BALANCED',
              digest_enabled: true,
              digest_day_of_week: 'SUNDAY',
              preferences_json: {},
              updated_at: new Date().toISOString()
            }
          })
        });
      } else {
        const patchData = route.request().postDataJSON();
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              id: 'pref-001',
              user_id: 'user-stage5-host',
              home_id: homeId,
              personalization_enabled: patchData.personalization_enabled ?? true,
              ai_memory_enabled: patchData.ai_memory_enabled ?? true,
              reminder_timing_preference: patchData.reminder_timing_preference || 'SAME_DAY_MORNING',
              recommendation_frequency: 'BALANCED',
              digest_enabled: true,
              digest_day_of_week: 'SUNDAY',
              preferences_json: {},
              updated_at: new Date().toISOString()
            }
          })
        });
      }
    });

    // Intercept Weekly Intelligence Digest
    await page.route(`**/api/v1/homes/${homeId}/intelligence/digest`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            home_id: homeId,
            home_name: 'Maplewood Residence',
            period_start: new Date(Date.now() - 7 * 86400000).toISOString(),
            period_end: new Date().toISOString(),
            tasks_completed_count: 8,
            tasks_overdue_count: 1,
            bills_paid_count: 3,
            bills_upcoming_count: 1,
            shopping_items_purchased_count: 12,
            inventory_low_count: 2,
            automations_executed_count: 14,
            highlights: [
              '8 chores and household tasks completed.',
              '3 bills settled successfully.',
              '12 grocery & household items purchased.',
              '14 automated rules executed smoothly.'
            ],
            key_recommendations: [
              '2 pantry consumables are running low on stock.'
            ]
          }
        })
      });
    });

    // Intercept Automations Intelligence Dashboard
    await page.route(`**/api/v1/homes/${homeId}/intelligence/dashboard`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            home_name: 'Maplewood Residence',
            active_automations_count: 3,
            total_automations_count: 4,
            recent_executions_count: 14,
            failed_automations_count: 0,
            active_automations: [
              {
                id: 'auto-001',
                home_id: homeId,
                name: 'Auto Restock Whole Milk',
                enabled: true,
                trigger_type: 'INVENTORY_LOW',
                actions: [{ type: 'ADD_SHOPPING_ITEM', target_item_name: 'Whole Milk' }],
                status: 'ACTIVE',
                created_at: new Date().toISOString()
              }
            ],
            recent_executions: [],
            recommendations: [],
            predicted_patterns: []
          }
        })
      });
    });

    // Intercept Stage 5 AI Agent Chat & Plan Execution
    await page.route(`**/api/v1/homes/${homeId}/ai/agent/chat`, async (route) => {
      const body = route.request().postDataJSON();
      const prompt = (body.prompt || '').toLowerCase();

      if (prompt.includes('weekend') || prompt.includes('prepare')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              session_token: 'sess-stage5-xyz',
              response_text: 'Here is a proposed household preparation plan for the weekend.',
              suggested_plan: {
                plan_id: 'plan-weekend-001',
                title: 'Weekend Household Preparation Plan',
                summary: 'Review low pantry supplies, restock grocery list, and schedule chore routines.',
                steps: [
                  {
                    step_number: 1,
                    action_type: 'QUERY',
                    target_domain: 'INVENTORY',
                    description: 'Check low stock pantry items',
                    tool_name: 'query_inventory',
                    permission_required: 'inventory:view',
                    status: 'PENDING'
                  },
                  {
                    step_number: 2,
                    action_type: 'WRITE',
                    target_domain: 'SHOPPING',
                    description: 'Add restock items to shopping list',
                    tool_name: 'create_shopping_item',
                    permission_required: 'shopping:create',
                    status: 'PENDING'
                  },
                  {
                    step_number: 3,
                    action_type: 'WRITE',
                    target_domain: 'TASK',
                    description: 'Schedule weekend cleaning chore',
                    tool_name: 'create_task',
                    permission_required: 'tasks:create',
                    status: 'PENDING'
                  }
                ],
                requires_confirmation: true
              },
              retrieved_memory_snippets: ['[ROUTINE] Family shops on Saturday mornings'],
              requires_confirmation: true
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
              session_token: 'sess-stage5-xyz',
              response_text: 'I have processed your household request.',
              retrieved_memory_snippets: ['[PREFERENCE] Prefers reminders 1 day before bill due dates'],
              requires_confirmation: false
            }
          })
        });
      }
    });

    await page.route(`**/api/v1/homes/${homeId}/ai/agent/plans/*/execute`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            status: 'SUCCESS',
            plan_id: 'plan-weekend-001',
            executed_steps_count: 3
          }
        })
      });
    });
  });

  test('should render Memory & Personalization tab with vault and weekly digest', async ({ page }) => {
    await page.goto('/automations');

    // Verify Stage 5 badge and Memory tab
    await expect(page.locator('text=Stage 5 Intelligence')).toBeVisible();
    const memoryTab = page.locator('button:has-text("Memory & Personalization")');
    await expect(memoryTab).toBeVisible();

    await memoryTab.click();

    // Verify Weekly Digest Card
    await expect(page.locator('text=This Week at Maplewood Residence')).toBeVisible();
    await expect(page.locator('text=8 chores and household tasks completed.')).toBeVisible();

    // Verify Personalization Controls
    await expect(page.locator('text=Personalization & Memory Controls')).toBeVisible();
    await expect(page.locator('button:has-text("Memory Enabled")')).toBeVisible();

    // Verify Stored Memories Vault
    await expect(page.locator('text=Long-Term Household Memory Vault')).toBeVisible();
    await expect(page.locator('text=Prefers reminders 1 day before bill due dates')).toBeVisible();
    await expect(page.locator('text=Family shops for groceries on Saturday mornings')).toBeVisible();
  });

  test('should allow adding a new household memory to the vault', async ({ page }) => {
    await page.goto('/automations');

    await page.locator('button:has-text("Memory & Personalization")').click();

    const input = page.locator('input[placeholder*="Family shops for groceries"]');
    await input.fill('Water filters replaced every 6 months');
    await page.locator('button:has-text("Save Memory")').click();

    await expect(input).toHaveValue('');
  });

  test('should handle multi-turn AI planning and multi-step plan confirmation in widget', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByText('Maplewood Residence').first()).toBeVisible();

    // Open AI Assistant Widget
    const aiButton = page.locator('button[aria-label="Open AI Assistant"]').first();
    await expect(aiButton).toBeVisible();
    await aiButton.click();

    // Verify Assistant Header
    await expect(page.locator('text=Ozhzo Assistant')).toBeVisible();

    // Send compound planning prompt
    const chatInput = page.locator('input[placeholder*="Ask anything or request a plan"]');
    await chatInput.fill('Prepare the house for the weekend');
    await page.locator('button[aria-label="Send message"]').click();


    // Verify Multi-step plan card
    await expect(page.locator('text=Weekend Household Preparation Plan')).toBeVisible();
    await expect(page.locator('text=Check low stock pantry items')).toBeVisible();
    await expect(page.locator('text=Add restock items to shopping list')).toBeVisible();
    await expect(page.locator('text=Schedule weekend cleaning chore')).toBeVisible();

    // Verify memory snippet badge
    await expect(page.locator('text=[ROUTINE] Family shops on Saturday mornings')).toBeVisible();

    // Confirm & Execute Plan
    const confirmBtn = page.locator('button:has-text("Confirm & Execute Plan")');
    await expect(confirmBtn).toBeVisible();
    await confirmBtn.click();

    // Verify success confirmation
    await expect(page.locator('text=Plan "Weekend Household Preparation Plan" executed')).toBeVisible();
  });
});
