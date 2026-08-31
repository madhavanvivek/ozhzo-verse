import { test, expect } from '@playwright/test';

test.describe('Ozhzo Verse Dashboard Home-State UX & Workspace Resolution', () => {

  test.beforeEach(async ({ page, context }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await context.clearCookies();

    // Default mock for notifications
    await page.route('**/api/v1/notifications**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] })
      });
    });
  });

  test('EXACT BUG FIX: User with active Home "Ichu\'s home" opens /dashboard into Ichu\'s home and NOT onboarding', async ({ page }) => {
    const homeId = 'home-ichu-777';
    const homeName = "Ichu's home";

    // Setup authenticated session
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
            id: 'user-vivek-123',
            display_name: 'Vivek',
            email: 'vivek@zinfog.com',
            mobile_verified: true,
            is_super_admin: false,
            system_role: 'USER'
          }
        })
      });
    });

    // Mock /homes (user belongs to Ichu's home)
    await page.route('**/api/v1/homes', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [
              {
                id: homeId,
                name: homeName,
                currency: 'USD',
                timezone: 'UTC',
                role: 'OWNER'
              }
            ]
          })
        });
      } else {
        await route.continue();
      }
    });

    // Mock /homes/{homeId}/dashboard
    await page.route(`**/api/v1/homes/${homeId}/dashboard`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            greeting: {
              greeting: 'Good morning',
              user_display_name: 'Vivek',
              date_formatted: 'Monday, 24 August 2026',
              time_period: 'morning'
            },
            summary: {
              home_id: homeId,
              home_name: homeName,
              currency: 'USD',
              timezone: 'UTC',
              members_count: 3,
              active_tasks_count: 4,
              low_stock_count: 2,
              unpaid_bills_count: 1,
              unpaid_bills_sum: 45.0,
              upcoming_events_count: 1,
              unread_notifications_count: 0
            },
            pending_tasks: [
              { id: 't-1', title: 'Restock groceries', priority: 'HIGH', status: 'TODO' }
            ],
            upcoming_bills: [
              { id: 'b-1', title: 'Fiber Internet', amount: 45.0, currency: 'USD', due_date: '2026-08-30', status: 'PENDING' }
            ],
            upcoming_events: [],
            low_stock_inventory: [
              { id: 'i-1', name: 'Milk', quantity: 1, unit: 'liters', status: 'LOW_STOCK' }
            ],
            shopping_items: [],
            notifications: [],
            role: 'OWNER'
          }
        })
      });
    });

    await page.goto('/dashboard');

    // 1. Must immediately show Ichu's home and Vivek greeting
    await expect(page.getByText("Ichu's home").first()).toBeVisible();
    await expect(page.getByText(/Good morning, Vivek|Welcome, Vivek/i).first()).toBeVisible();

    // 2. Must show active dashboard summary cards
    await expect(page.getByText('Household Attention Required')).toBeVisible();
    await expect(page.getByText('Restock groceries')).toBeVisible();

    // 3. Must NOT show Create Home / Join Home onboarding card
    await expect(page.getByText("You haven't created or joined a Home yet")).not.toBeVisible();
    await expect(page.getByRole('button', { name: 'Create Your Home' })).not.toBeVisible();
  });

  test('TEST 1: User with zero Homes renders State A onboarding experience', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('access_token', 'mock-valid-jwt-token');
      localStorage.removeItem('active_home_id');
    });

    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { id: 'user-new-001', display_name: 'New User', email: 'new@example.com', mobile_verified: true }
        })
      });
    });

    // Zero homes returned from backend
    await page.route('**/api/v1/homes', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data: [] })
        });
      } else {
        await route.continue();
      }
    });

    await page.goto('/dashboard');

    // Onboarding should be visible
    await expect(page.getByText('Welcome to Ozhzo Verse')).toBeVisible();
    await expect(page.getByText("You haven't created or joined a Home yet")).toBeVisible();
    await expect(page.getByRole('button', { name: 'Create Your Home' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Join a Home' })).toBeVisible();
  });

  test('TEST 2: User with one Home renders active Home dashboard without onboarding cards', async ({ page }) => {
    const homeId = 'home-solo-999';

    await page.addInitScript(({ token, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('active_home_id', hId);
    }, { token: 'mock-valid-jwt-token', hId: homeId });

    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { id: 'user-solo', display_name: 'Solo User', email: 'solo@example.com', mobile_verified: true }
        })
      });
    });

    await page.route('**/api/v1/homes', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [{ id: homeId, name: 'Mountain Retreat', currency: 'USD', timezone: 'UTC', role: 'OWNER' }]
          })
        });
      } else {
        await route.continue();
      }
    });

    await page.route(`**/api/v1/homes/${homeId}/dashboard`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            greeting: { greeting: 'Welcome', user_display_name: 'Solo User', date_formatted: 'Today', time_period: 'morning' },
            summary: { home_id: homeId, home_name: 'Mountain Retreat', currency: 'USD', timezone: 'UTC', members_count: 1, active_tasks_count: 0, low_stock_count: 0, unpaid_bills_count: 0, unpaid_bills_sum: 0, upcoming_events_count: 0, unread_notifications_count: 0 },
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

    await page.goto('/dashboard');

    await expect(page.getByText('Mountain Retreat').first()).toBeVisible();
    await expect(page.getByText("You haven't created or joined a Home yet")).not.toBeVisible();
  });

  test('TEST 3: User with multiple Homes shows active Home and allows switching via HomeSwitcher', async ({ page }) => {
    const home1Id = 'home-primary-1';
    const home2Id = 'home-beach-2';

    await page.addInitScript(({ token, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('active_home_id', hId);
    }, { token: 'mock-valid-jwt-token', hId: home1Id });

    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { id: 'user-multi', display_name: 'Multi Owner', email: 'multi@example.com', mobile_verified: true }
        })
      });
    });

    await page.route('**/api/v1/homes', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [
              { id: home1Id, name: 'Primary Residence', currency: 'USD', timezone: 'UTC', role: 'OWNER' },
              { id: home2Id, name: 'Beach House', currency: 'USD', timezone: 'UTC', role: 'MEMBER' }
            ]
          })
        });
      } else {
        await route.continue();
      }
    });

    await page.route(`**/api/v1/homes/${home1Id}/dashboard`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            greeting: { greeting: 'Welcome', user_display_name: 'Multi Owner', date_formatted: 'Today', time_period: 'morning' },
            summary: { home_id: home1Id, home_name: 'Primary Residence', currency: 'USD', timezone: 'UTC', members_count: 2, active_tasks_count: 0, low_stock_count: 0, unpaid_bills_count: 0, unpaid_bills_sum: 0, upcoming_events_count: 0, unread_notifications_count: 0 },
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

    await page.route(`**/api/v1/homes/${home2Id}/dashboard`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            greeting: { greeting: 'Welcome', user_display_name: 'Multi Owner', date_formatted: 'Today', time_period: 'morning' },
            summary: { home_id: home2Id, home_name: 'Beach House', currency: 'USD', timezone: 'UTC', members_count: 4, active_tasks_count: 1, low_stock_count: 0, unpaid_bills_count: 0, unpaid_bills_sum: 0, upcoming_events_count: 0, unread_notifications_count: 0 },
            pending_tasks: [{ id: 't-b1', title: 'Clean patio', priority: 'NORMAL', status: 'TODO' }],
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

    await page.goto('/dashboard');

    // Initially loads Primary Residence
    await expect(page.getByText('Primary Residence').first()).toBeVisible();

    // Open HomeSwitcher
    await page.locator('#home-switcher-dropdown-btn:visible').click();
    await expect(page.locator('#home-switcher-menu:visible')).toBeVisible();
    await expect(page.locator('#home-switcher-menu:visible').getByText('Beach House')).toBeVisible();
    await expect(page.locator('#switcher-create-home-btn:visible')).toBeVisible();
    await expect(page.locator('#switcher-join-home-btn:visible')).toBeVisible();

    // Switch to Beach House
    await page.locator('#home-switcher-menu:visible button:has-text("Beach House")').click();
    await expect(page.getByText('Beach House').first()).toBeVisible();
    await expect(page.getByText('Clean patio')).toBeVisible();
  });

  test('TEST 4: Stale active_home_id in localStorage is automatically discarded and valid Home loaded', async ({ page }) => {
    const validHomeId = 'home-valid-555';

    // Set a stale active home ID from another session
    await page.addInitScript(({ token, validId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('active_home_id', 'stale-foreign-home-id-999');
    }, { token: 'mock-valid-jwt-token', validId: validHomeId });

    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { id: 'user-clean', display_name: 'Clean User', email: 'clean@example.com', mobile_verified: true }
        })
      });
    });

    await page.route('**/api/v1/homes', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [{ id: validHomeId, name: 'True Home', currency: 'USD', timezone: 'UTC', role: 'OWNER' }]
          })
        });
      } else {
        await route.continue();
      }
    });

    await page.route('**/api/v1/homes/*/dashboard', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            greeting: { greeting: 'Welcome', user_display_name: 'Clean User', date_formatted: 'Today', time_period: 'morning' },
            summary: { home_id: validHomeId, home_name: 'True Home', currency: 'USD', timezone: 'UTC', members_count: 1, active_tasks_count: 0, low_stock_count: 0, unpaid_bills_count: 0, unpaid_bills_sum: 0, upcoming_events_count: 0, unread_notifications_count: 0 },
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

    await page.goto('/dashboard');

    // Verify True Home is loaded
    await expect(page.getByText('True Home').first()).toBeVisible();

    // Verify active_home_id in localStorage was updated to the valid home
    const storedHomeId = await page.evaluate(() => localStorage.getItem('active_home_id'));
    expect(storedHomeId).toBe(validHomeId);
  });

  test('TEST 5: Logout User A -> Login User B isolates Home session boundary completely', async ({ page }) => {
    // 1. Setup User A session
    await page.addInitScript(() => {
      localStorage.setItem('access_token', 'token-user-a');
      localStorage.setItem('active_home_id', 'home-user-a-111');
    });

    let currentAuthUser = 'A';

    await page.route('**/api/v1/users/me', async (route) => {
      if (currentAuthUser === 'A') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { id: 'user-a', display_name: 'User A', email: 'usera@example.com', mobile_verified: true }
          })
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { id: 'user-b', display_name: 'User B', email: 'userb@example.com', mobile_verified: true }
          })
        });
      }
    });

    await page.route('**/api/v1/homes', async (route) => {
      if (currentAuthUser === 'A') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [{ id: 'home-user-a-111', name: "User A's Sanctuary", currency: 'USD', timezone: 'UTC', role: 'OWNER' }]
          })
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [{ id: 'home-user-b-222', name: "User B's Haven", currency: 'USD', timezone: 'UTC', role: 'OWNER' }]
          })
        });
      }
    });

    await page.route('**/api/v1/homes/home-user-a-111/dashboard', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            greeting: { greeting: 'Welcome', user_display_name: 'User A', date_formatted: 'Today', time_period: 'morning' },
            summary: { home_id: 'home-user-a-111', home_name: "User A's Sanctuary", currency: 'USD', timezone: 'UTC', members_count: 1, active_tasks_count: 0, low_stock_count: 0, unpaid_bills_count: 0, unpaid_bills_sum: 0, upcoming_events_count: 0, unread_notifications_count: 0 },
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

    await page.route('**/api/v1/homes/home-user-b-222/dashboard', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            greeting: { greeting: 'Welcome', user_display_name: 'User B', date_formatted: 'Today', time_period: 'morning' },
            summary: { home_id: 'home-user-b-222', home_name: "User B's Haven", currency: 'USD', timezone: 'UTC', members_count: 1, active_tasks_count: 0, low_stock_count: 0, unpaid_bills_count: 0, unpaid_bills_sum: 0, upcoming_events_count: 0, unread_notifications_count: 0 },
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

    await page.goto('/dashboard');
    await expect(page.getByText("User A's Sanctuary").first()).toBeVisible();

    // 2. Perform Logout
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    // 3. User B Logs In
    currentAuthUser = 'B';
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'token-user-b');
    });

    await page.goto('/dashboard');

    // 4. Confirm User B's dashboard is loaded and User A's sanctuary is NOT present
    await expect(page.getByText("User B's Haven").first()).toBeVisible();
    await expect(page.getByText("User A's Sanctuary")).not.toBeVisible();
  });

  test('TEST 6: Unverified user with existing Home can access and view Dashboard without blocking', async ({ page }) => {
    const homeId = 'home-existing-333';

    await page.addInitScript(({ token, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('active_home_id', hId);
    }, { token: 'mock-valid-jwt-token', hId: homeId });

    // mobile_verified is FALSE
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { id: 'user-unverified', display_name: 'Unverified Member', email: 'unverified@example.com', mobile_verified: false, phone_number: '+1234567890' }
        })
      });
    });

    await page.route('**/api/v1/homes', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [{ id: homeId, name: 'Family Homestead', currency: 'USD', timezone: 'UTC', role: 'MEMBER' }]
          })
        });
      } else {
        await route.continue();
      }
    });

    await page.route(`**/api/v1/homes/${homeId}/dashboard`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            greeting: { greeting: 'Welcome', user_display_name: 'Unverified Member', date_formatted: 'Today', time_period: 'morning' },
            summary: { home_id: homeId, home_name: 'Family Homestead', currency: 'USD', timezone: 'UTC', members_count: 5, active_tasks_count: 0, low_stock_count: 0, unpaid_bills_count: 0, unpaid_bills_sum: 0, upcoming_events_count: 0, unread_notifications_count: 0 },
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

    await page.goto('/dashboard');

    // Dashboard renders normally for existing home membership
    await expect(page.getByText('Family Homestead').first()).toBeVisible();
    await expect(page.getByText(/Welcome, Unverified Member/i).first()).toBeVisible();
  });

  test('TEST 7: Unverified user attempting to Create New Home shows mobile verification requirement modal', async ({ page }) => {
    const homeId = 'home-existing-444';

    await page.addInitScript(({ token, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('active_home_id', hId);
    }, { token: 'mock-valid-jwt-token', hId: homeId });

    // mobile_verified is FALSE
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { id: 'user-unverified-creator', display_name: 'Unverified Creator', email: 'ucreator@example.com', mobile_verified: false, phone_number: '+15551234567' }
        })
      });
    });

    await page.route('**/api/v1/homes', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [{ id: homeId, name: 'Family Flat', currency: 'USD', timezone: 'UTC', role: 'MEMBER' }]
          })
        });
      } else {
        await route.continue();
      }
    });

    await page.route(`**/api/v1/homes/${homeId}/dashboard`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            greeting: { greeting: 'Welcome', user_display_name: 'Unverified Creator', date_formatted: 'Today', time_period: 'morning' },
            summary: { home_id: homeId, home_name: 'Family Flat', currency: 'USD', timezone: 'UTC', members_count: 2, active_tasks_count: 0, low_stock_count: 0, unpaid_bills_count: 0, unpaid_bills_sum: 0, upcoming_events_count: 0, unread_notifications_count: 0 },
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

    await page.goto('/dashboard');
    await expect(page.getByText('Family Flat').first()).toBeVisible();

    // Trigger Create New Home from Switcher
    await page.locator('#home-switcher-dropdown-btn:visible').click();
    await page.locator('#switcher-create-home-btn:visible').click();

    // Verification requirement guidance must be rendered
    await expect(page.getByText('Verify your mobile number to continue')).toBeVisible();
    await expect(page.locator('#modal-verify-mobile-action-btn')).toBeVisible();
  });

  test('TEST 8: Verified user can create a Home without verification blocking', async ({ page }) => {
    const homeId = 'home-existing-555';

    await page.addInitScript(({ token, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('active_home_id', hId);
    }, { token: 'mock-valid-jwt-token', hId: homeId });

    // mobile_verified is TRUE
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { id: 'user-verified', display_name: 'Verified Creator', email: 'vcreator@example.com', mobile_verified: true, phone_number: '+15559876543' }
        })
      });
    });

    const userHomesList = [{ id: homeId, name: 'First Home', currency: 'USD', timezone: 'UTC', role: 'OWNER' }];

    await page.route('**/api/v1/homes', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: userHomesList
          })
        });
      } else if (route.request().method() === 'POST') {
        const payload = route.request().postDataJSON();
        const newHome = {
          id: 'home-newly-created-666',
          name: payload.name,
          currency: payload.currency || 'USD',
          timezone: payload.timezone || 'UTC',
          role: 'OWNER'
        };
        userHomesList.push(newHome);
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: newHome
          })
        });
      }
    });

    await page.route(`**/api/v1/homes/${homeId}/dashboard`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            greeting: { greeting: 'Welcome', user_display_name: 'Verified Creator', date_formatted: 'Today', time_period: 'morning' },
            summary: { home_id: homeId, home_name: 'First Home', currency: 'USD', timezone: 'UTC', members_count: 1, active_tasks_count: 0, low_stock_count: 0, unpaid_bills_count: 0, unpaid_bills_sum: 0, upcoming_events_count: 0, unread_notifications_count: 0 },
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

    await page.route('**/api/v1/homes/home-newly-created-666/dashboard', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            greeting: { greeting: 'Welcome', user_display_name: 'Verified Creator', date_formatted: 'Today', time_period: 'morning' },
            summary: { home_id: 'home-newly-created-666', home_name: 'Second Villa', currency: 'USD', timezone: 'UTC', members_count: 1, active_tasks_count: 0, low_stock_count: 0, unpaid_bills_count: 0, unpaid_bills_sum: 0, upcoming_events_count: 0, unread_notifications_count: 0 },
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

    await page.goto('/dashboard');

    // Trigger Create New Home
    await page.locator('#home-switcher-dropdown-btn:visible').click();
    await page.locator('#switcher-create-home-btn:visible').click();

    // Form is available directly without blocking
    await expect(page.getByText('Verify your mobile number to continue')).not.toBeVisible();
    await page.fill('#homeName', 'Second Villa');
    await page.click('button[type="submit"]:has-text("Create Home")');

    // After creation, new home dashboard is loaded
    await expect(page.getByText('Second Villa').first()).toBeVisible();
  });

});
