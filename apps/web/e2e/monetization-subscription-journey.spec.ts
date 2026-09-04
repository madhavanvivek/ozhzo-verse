import { test, expect } from '@playwright/test';

test.describe('Stage 2.2 Monetization & Subscription Management Suite', () => {

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

    // Default mock for credits
    await page.route('**/api/v1/subscription/my-credits**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] })
      });
    });

    // Default mock for transactions
    await page.route('**/api/v1/subscription/transactions**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] })
      });
    });
  });

  test('1. User visits /settings/subscription and sees Entitlement Quota & Plans', async ({ page }) => {
    const homeId = '11111111-1111-1111-1111-111111111111';

    await page.addInitScript(({ token, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('active_home_id', hId);
    }, { token: 'mock-user-jwt', hId: homeId });

    // Mock /users/me
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'user-monetize-01',
            email: 'subscriber@ozhzo.com',
            display_name: 'Subscriber User',
            mobile_verified: true,
            free_home_consumed: true,
            is_super_admin: false,
            system_role: 'USER',
            homes: [{ home_id: homeId, name: "Primary Haven", role: 'OWNER', status: 'ACTIVE' }]
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
            {
              id: homeId,
              name: 'Primary Haven',
              currency: 'USD',
              role: 'OWNER',
              status: 'ACTIVE'
            }
          ]
        })
      });
    });

    // Mock /subscription/me
    await page.route('**/api/v1/subscription/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            free_home_consumed: true,
            free_home_included: 1,
            active_homes_count: 1,
            total_allowed_homes: 1,
            can_create_home: false,
            active_subscription: null
          }
        })
      });
    });

    // Mock /subscription/plans
    await page.route('**/api/v1/subscription/plans', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: 'plan-pro-01',
              name: 'Ozhzo Multi-Home Pro',
              code: 'MULTI_HOME_PRO',
              description: 'For users managing multiple properties and households.',
              plan_type: 'HOME',
              status: 'ACTIVE',
              included_members: 5,
              max_homes: 5,
              additional_member_allowed: true,
              introductory_enabled: false,
              introductory_duration_days: 0,
              introductory_price: '0.00',
              prices: [
                {
                  id: 'price-usd-01',
                  plan_id: 'plan-pro-01',
                  country: 'GLOBAL',
                  currency: 'USD',
                  billing_period: 'ANNUAL',
                  list_price: '49.00',
                  additional_member_list_price: '20.00',
                  is_active: true
                }
              ]
            }
          ]
        })
      });
    });

    // Mock /subscription/transactions
    await page.route('**/api/v1/subscription/transactions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] })
      });
    });

    // Mock /homes/*/members
    await page.route('**/api/v1/homes/*/members', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [{ id: 'm1', user_id: 'user-monetize-01', display_name: 'Subscriber User', role: 'OWNER', status: 'ACTIVE' }]
        })
      });
    });

    await page.goto('/settings/subscription');
    await expect(page.locator('h1')).toContainText('Household Subscription & Multi-Home Entitlements');
    await expect(page.getByText('1 / 1')).toBeVisible();
    await expect(page.getByText('Ozhzo Multi-Home Pro')).toBeVisible();
    await expect(page.getByText('Up to 5 Households')).toBeVisible();
  });

  test('2. User applies coupon and confirms checkout simulation', async ({ page }) => {
    const homeId = '11111111-1111-1111-1111-111111111111';

    await page.addInitScript(({ token, hId }) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('active_home_id', hId);
    }, { token: 'mock-user-jwt', hId: homeId });

    // Mock /users/me
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'user-monetize-01',
            email: 'subscriber@ozhzo.com',
            display_name: 'Subscriber User',
            mobile_verified: true,
            free_home_consumed: true,
            is_super_admin: false,
            system_role: 'USER',
            homes: [{ home_id: homeId, name: "Primary Haven", role: 'OWNER', status: 'ACTIVE' }]
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
            {
              id: homeId,
              name: 'Primary Haven',
              currency: 'USD',
              role: 'OWNER',
              status: 'ACTIVE'
            }
          ]
        })
      });
    });

    let currentEntitlements = {
      free_home_consumed: true,
      free_home_included: 1,
      active_homes_count: 1,
      total_allowed_homes: 1,
      can_create_home: false,
      active_subscription: null
    };

    await page.route('**/api/v1/subscription/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: currentEntitlements })
      });
    });

    await page.route('**/api/v1/subscription/plans', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: 'plan-pro-01',
              name: 'Ozhzo Multi-Home Pro',
              code: 'MULTI_HOME_PRO',
              description: 'For users managing multiple properties and households.',
              plan_type: 'HOME',
              status: 'ACTIVE',
              included_members: 5,
              max_homes: 5,
              additional_member_allowed: true,
              introductory_enabled: false,
              introductory_duration_days: 0,
              introductory_price: '0.00',
              prices: [
                {
                  id: 'price-usd-01',
                  plan_id: 'plan-pro-01',
                  country: 'GLOBAL',
                  currency: 'USD',
                  billing_period: 'ANNUAL',
                  list_price: '49.00',
                  additional_member_list_price: '20.00',
                  is_active: true
                }
              ]
            }
          ]
        })
      });
    });

    await page.route('**/api/v1/subscription/transactions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] })
      });
    });

    await page.route('**/api/v1/homes/*/members', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [{ id: 'm1', user_id: 'user-monetize-01', display_name: 'Subscriber User', role: 'OWNER', status: 'ACTIVE' }]
        })
      });
    });

    // Mock coupon validation
    await page.route('**/api/v1/coupons/validate', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            valid: true,
            code: 'LAUNCH50',
            coupon_type: 'PERCENTAGE_DISCOUNT',
            benefit: '50% discount',
            discount_value: 50.0
          }
        })
      });
    });

    // Mock checkout initiation
    await page.route('**/api/v1/subscription/checkout', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            transaction_id: 'tx-001-mock',
            amount: 49.0,
            discount_amount: 24.5,
            final_amount: 24.5,
            currency: 'USD',
            provider_transaction_id: 'mock_provider_tx_999',
            payment_required: true,
            status: 'PENDING'
          }
        })
      });
    });

    // Mock payment confirmation
    await page.route('**/api/v1/subscription/confirm-payment', async (route) => {
      currentEntitlements = {
        free_home_consumed: true,
        free_home_included: 1,
        active_homes_count: 1,
        total_allowed_homes: 5,
        can_create_home: true,
        active_subscription: {
          id: 'sub-active-01',
          plan_name: 'Ozhzo Multi-Home Pro',
          status: 'ACTIVE',
          current_period_ends_at: '2027-01-01T00:00:00Z',
          paid_member_seats: 0,
          effective_price: 24.5,
          currency: 'USD'
        }
      };

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            success: true,
            status: 'ACTIVE',
            subscription_id: 'sub-active-01',
            message: 'Subscription activated successfully.'
          }
        })
      });
    });

    await page.goto('/settings/subscription');

    // 1. Enter coupon code
    await page.fill('input[placeholder*="LAUNCH50"]', 'LAUNCH50');
    await page.click('button:has-text("Apply Coupon")');
    await expect(page.getByText('Coupon "LAUNCH50" applied')).toBeVisible();

    // 2. Click Select & Subscribe
    await page.click('button:has-text("Select & Subscribe")');
    await expect(page.getByText('Confirm Subscription Purchase')).toBeVisible();
    await expect(page.getByText('USD 24.50', { exact: true })).toBeVisible();

    // 3. Confirm Payment
    await page.click('button:has-text("Pay & Activate Subscription")');
    await expect(page.getByText('Subscription activated successfully!')).toBeVisible();
  });

  test('3. Super Admin console displays Revenue Analytics, Plans with max_homes, and Transactions audit', async ({ page }) => {
    await page.addInitScript(({ token }) => {
      localStorage.setItem('access_token', token);
    }, { token: 'mock-super-admin-jwt' });

    // Mock Super Admin identity
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'super-admin-01',
            email: 'admin@ozhzo.com',
            display_name: 'Super Admin',
            is_super_admin: true,
            system_role: 'SUPER_ADMIN',
            homes: []
          }
        })
      });
    });

    // Mock analytics
    await page.route('**/api/v1/admin/subscriptions/analytics', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            total_revenue: 1250.0,
            total_transactions: 25,
            active_subscribers: 22,
            trial_subscribers: 5,
            past_due_subscribers: 1,
            cancelled_subscribers: 2,
            average_order_value: 50.0,
            currency: 'USD'
          }
        })
      });
    });

    // Mock admin plans
    await page.route('**/api/v1/admin/subscriptions/plans', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: 'plan-multi-10',
              name: 'Enterprise Multi-Household',
              code: 'ENTERPRISE_MULTI',
              description: 'Multi-home estate coverage',
              plan_type: 'HOME',
              status: 'ACTIVE',
              included_members: 10,
              max_homes: 15,
              additional_member_allowed: true,
              introductory_enabled: false,
              introductory_duration_days: 0,
              introductory_price: '0.00',
              prices: []
            }
          ]
        })
      });
    });

    // Mock features
    await page.route('**/api/v1/admin/subscriptions/features', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] })
      });
    });

    // Mock transactions
    await page.route('**/api/v1/admin/subscriptions/transactions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: 'tx-audit-01',
              user_id: 'user-001',
              user_email: 'customer@ozhzo.com',
              plan_name: 'Enterprise Multi-Household',
              amount: '120.00',
              discount_amount: '20.00',
              final_amount: '100.00',
              currency: 'USD',
              provider: 'MOCK_GATEWAY',
              status: 'SUCCESS',
              created_at: '2026-08-31T12:00:00Z'
            }
          ]
        })
      });
    });

    await page.goto('/admin/subscriptions');

    // 1. Verify revenue analytics
    await expect(page.getByText('$1250.00')).toBeVisible();
    await expect(page.getByText('22')).toBeVisible(); // Active subscribers

    // 2. Verify max_homes on plan card
    await expect(page.getByText('Max 15 Homes')).toBeVisible();

    // 3. Switch to Payment Transactions tab
    await page.click('button:has-text("Payment Transactions")');
    await expect(page.getByText('customer@ozhzo.com')).toBeVisible();
    await expect(page.getByText('Enterprise Multi-Household')).toBeVisible();
    await expect(page.getByText('USD 100.00')).toBeVisible();
  });
});
