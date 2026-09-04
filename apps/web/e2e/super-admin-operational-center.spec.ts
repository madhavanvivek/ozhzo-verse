import { test, expect } from '@playwright/test';

test.describe('Super Admin Operational Control Center', () => {
  test.beforeEach(async ({ page, context }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await context.clearCookies();

    // Inject local storage credentials before page loads
    await page.addInitScript(() => {
      localStorage.setItem('access_token', 'mock-super-admin-jwt');
      const superAdminUser = {
        id: '550e8400-e29b-41d4-a716-446655440099',
        email: 'superadmin@ozhzo.com',
        display_name: 'Master Admin',
        is_super_admin: true,
        system_role: 'SUPER_ADMIN',
        is_active: true,
        homes: [{ home_id: '11111111-1111-1111-1111-111111111111', name: "The Madhavan Residence", role: 'OWNER', status: 'ACTIVE' }],
      };
      localStorage.setItem('user', JSON.stringify(superAdminUser));
      localStorage.setItem('user_info', JSON.stringify(superAdminUser));
    });

    // Mock Super Admin Profile & Session
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: '550e8400-e29b-41d4-a716-446655440099',
            email: 'superadmin@ozhzo.com',
            display_name: 'Master Admin',
            is_super_admin: true,
            system_role: 'SUPER_ADMIN',
            is_active: true,
            homes: [{ home_id: '11111111-1111-1111-1111-111111111111', name: "The Madhavan Residence", role: 'OWNER', status: 'ACTIVE' }],
          },
        }),
      });
    });

    // Mock Dashboard Analytics & Config
    await page.route('**/api/v1/admin/system/analytics-summary', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            total_users: 142,
            active_users: 138,
            suspended_users: 4,
            total_homes: 52,
            active_homes: 50,
            suspended_homes: 2,
            average_members_per_home: 2.8,
            total_active_subscriptions: 48,
            total_paid_member_seats: 96,
            generated_at: new Date().toISOString(),
          },
        }),
      });
    });

    await page.route('**/api/v1/admin/system/config', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            environment: 'production',
            supported_currencies: ['INR', 'AED', 'SAR', 'GBP', 'USD'],
            default_timezone: 'UTC',
            feature_flags: { dynamic_pricing: true },
            available_system_roles: ['USER', 'SUPPORT', 'ADMIN', 'SUPER_ADMIN'],
            available_home_roles: ['OWNER', 'HOME_ADMIN', 'MEMBER', 'CHILD', 'GUEST'],
            password_hashing_algorithm: 'bcrypt',
            mfa_enforced_for_admins: false,
            rate_limiting_enabled: true,
          },
        }),
      });
    });

    await page.route('**/api/v1/admin/analytics/countries', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            {
              country_code: 'IN',
              country_name: 'India',
              currency: 'INR',
              total_users: 85,
              total_homes: 32,
              active_subscriptions: 30,
              paid_subscriptions: 24,
              mrr_estimated: 14999.0,
              conversion_rate: 28.2,
            },
            {
              country_code: 'AE',
              country_name: 'United Arab Emirates',
              currency: 'AED',
              total_users: 35,
              total_homes: 12,
              active_subscriptions: 12,
              paid_subscriptions: 10,
              mrr_estimated: 2490.0,
              conversion_rate: 28.6,
            },
          ],
        }),
      });
    });

    await page.route('**/api/v1/admin/analytics/retention', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            total_homes: 52,
            active_homes: 50,
            d1_retention_rate: 88.5,
            d7_retention_rate: 76.2,
            d30_retention_rate: 64.8,
            two_plus_module_adoption_rate: 82.4,
          },
        }),
      });
    });

    // Mock Regions List & Patch
    await page.route('**/api/v1/admin/regions**', async (route) => {
      const url = route.request().url();
      if (url.includes('/pricing')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [
              {
                id: 'price-1',
                plan_id: 'plan-1',
                country: 'IN',
                region: 'South Asia',
                currency: 'INR',
                billing_period: 'ANNUAL',
                list_price: 1799.0,
                additional_member_list_price: 499.0,
                version: 1,
                is_active: true,
                effective_from: '2026-01-01T00:00:00Z',
              },
            ],
          }),
        });
      } else if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [
              {
                id: '11111111-1111-1111-1111-111111111111',
                country_code: 'IN',
                country_name: 'India',
                region: 'South Asia',
                currency: 'INR',
                default_plan_code: 'HOME_STANDARD',
                payment_gateway: 'RAZORPAY',
                tax_percentage: '18.00',
                is_active: true,
                is_default: false,
                promotional_eligibility_enabled: true,
                metadata_json: {},
              },
              {
                id: '22222222-2222-2222-2222-222222222222',
                country_code: 'AE',
                country_name: 'United Arab Emirates',
                region: 'Middle East',
                currency: 'AED',
                default_plan_code: 'HOME_STANDARD',
                payment_gateway: 'STRIPE',
                tax_percentage: '5.00',
                is_active: true,
                is_default: false,
                promotional_eligibility_enabled: true,
                metadata_json: {},
              },
            ],
          }),
        });
      } else if (route.request().method() === 'PATCH') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { country_code: 'IN', country_name: 'India', is_active: true, tax_percentage: '18.00' },
          }),
        });
      } else {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { id: '33333333-3333-3333-3333-333333333333', country_code: 'SG', country_name: 'Singapore', is_active: true },
          }),
        });
      }
    });

    // Mock Feature Flags List
    await page.route('**/api/v1/admin/feature-flags**', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [
              {
                id: 'flag-1',
                key: 'smart_pantry_ai_replenish',
                name: 'AI Smart Replenishment',
                description: 'Proactively draft shopping lists from consumption velocity.',
                is_enabled: true,
                target_countries: ['IN', 'AE'],
                target_plans: ['HOME_PRO'],
                rollout_percentage: 100,
                rules_json: {},
              },
            ],
          }),
        });
      } else {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { id: 'flag-2', key: 'voice_memo_tasks', name: 'Voice Tasks', is_enabled: false },
          }),
        });
      }
    });

    // Mock Invitations List
    await page.route('**/api/v1/admin/invitations**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: 'inv-1',
              home_id: 'home-1',
              home_name: 'The Madhavan Residence',
              invitation_code: 'OZ-FE9EDU',
              role: 'MEMBER',
              email: 'vyshak@example.com',
              phone_number: '+919876543210',
              status: 'PENDING',
              invited_by_name: 'Vivek Madhavan',
              expires_at: new Date(Date.now() + 86400000 * 7).toISOString(),
              created_at: new Date().toISOString(),
              is_expired: false,
            },
          ],
        }),
      });
    });

    // Mock AI & Automations Config
    await page.route('**/api/v1/admin/ai/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            provider: 'GEMINI',
            model: 'gemini-1.5-flash',
            daily_request_limit_default: 150,
            monthly_cost_budget_usd: 500.0,
            max_context_tokens: 8192,
            total_ai_records: 620,
            total_estimated_cost_usd: 18.4,
            total_tokens_consumed: 420000,
            active_quotas_count: 24,
          },
        }),
      });
    });

    await page.route('**/api/v1/admin/automations/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: 'auto-1',
              home_id: 'home-1',
              home_name: 'Smith Villa',
              name: 'Restock Coffee Beans',
              trigger_type: 'LOW_STOCK',
              failure_count: 5,
              consecutive_failures: 5,
              last_error: 'API Rate Limit exceeded during auto-cart dispatch',
              status: 'ERROR',
              enabled: false,
              updated_at: new Date().toISOString(),
            },
          ],
        }),
      });
    });

    // Mock Subscriptions Endpoints
    await page.route('**/api/v1/admin/subscriptions/plans**', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [
              {
                id: 'plan-1',
                name: 'Home Standard OS',
                code: 'HOME_STANDARD',
                description: 'Complete household operating system.',
                plan_type: 'HOME',
                status: 'ACTIVE',
                included_members: 4,
                maximum_members: 10,
                max_homes: 5,
                additional_member_allowed: true,
                introductory_enabled: true,
                introductory_duration_days: 365,
                introductory_price: '0.00',
                prices: [
                  {
                    id: 'price-1',
                    plan_id: 'plan-1',
                    country: 'IN',
                    region: 'South Asia',
                    currency: 'INR',
                    billing_period: 'ANNUAL',
                    list_price: 1799.0,
                    additional_member_list_price: 499.0,
                    base_price: 1799.0,
                    additional_member_price: 499.0,
                    version: 1,
                    is_active: true,
                    effective_from: '2026-01-01T00:00:00Z',
                  },
                ],
              },
            ],
          }),
        });
      } else if (route.request().method() === 'PATCH') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { id: 'plan-1', name: 'Home Standard OS (Updated)', status: 'ACTIVE' },
          }),
        });
      }
    });

    await page.route('**/api/v1/admin/subscriptions/features**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] }),
      });
    });

    await page.route('**/api/v1/admin/subscriptions/analytics**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            total_revenue: 12500.0,
            average_order_value: 120.0,
            active_subscribers: 48,
            trial_subscribers: 12,
            total_transactions: 95,
            past_due_subscribers: 1,
            cancelled_subscribers: 2,
          },
        }),
      });
    });

    await page.route('**/api/v1/admin/subscriptions/prices**', async (route) => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'price-2',
            plan_id: 'plan-1',
            country: 'IN',
            currency: 'INR',
            billing_period: 'ANNUAL',
            list_price: 2499.0,
            additional_member_list_price: 599.0,
            version: 2,
            is_active: true,
          },
        }),
      });
    });

    await page.route('**/api/v1/admin/subscriptions/promotions**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: [] }) });
    });

    await page.route('**/api/v1/admin/subscriptions/subscribers**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: [] }) });
    });

    await page.route('**/api/v1/admin/subscriptions/transactions**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: [] }) });
    });

    await page.route('**/api/v1/admin/subscriptions/gateway-status**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: { status: 'ONLINE', providers: ['STRIPE', 'RAZORPAY'] } }) });
    });

    await page.route('**/api/v1/admin/subscriptions/credits**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: [] }) });
    });

    // Mock Coupons API
    await page.route('**/api/v1/admin/coupons/campaigns**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] }),
      });
    });

    await page.route('**/api/v1/admin/coupons/grants**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] }),
      });
    });

    await page.route('**/api/v1/admin/coupons/analytics**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { active_coupons: 3, total_coupons: 5, total_redemptions: 42, active_direct_grants: 4 },
        }),
      });
    });

    await page.route('**/api/v1/admin/coupons/**/redemptions**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: 'red-1',
              user_id: '550e8400-e29b-41d4-a716-446655440099',
              home_id: '770e8400-e29b-41d4-a716-446655440000',
              redeemed_at: new Date().toISOString(),
              discount_amount_applied: '50.00',
            },
          ],
        }),
      });
    });

    await page.route('**/api/v1/admin/coupons**', async (route) => {
      const url = route.request().url();
      if (url.includes('/campaigns') || url.includes('/grants') || url.includes('/analytics') || url.includes('/redemptions')) {
        await route.fallback();
        return;
      }
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [
              {
                id: 'c-1',
                name: 'Launch Discount 50%',
                code: 'LAUNCH50',
                description: '50% launch discount voucher',
                coupon_type: 'PERCENTAGE_DISCOUNT',
                discount_value: '50.00',
                free_period_value: 0,
                free_period_unit: 'MONTHS',
                eligibility_type: 'ANY_USER',
                country: 'IN',
                redemptions_count: 14,
                maximum_total_redemptions: 100,
                maximum_redemptions_per_user: 1,
                status: 'ACTIVE',
                created_at: new Date().toISOString(),
              },
            ],
          }),
        });
      } else if (route.request().method() === 'PATCH') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { id: 'c-1', code: 'LAUNCH50', discount_value: '60.00', status: 'ACTIVE' },
          }),
        });
      } else {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { id: 'c-2', code: 'PROMO100', discount_value: '100.00', status: 'ACTIVE' },
          }),
        });
      }
    });

    // Mock Homes endpoint to prevent 401 redirect
    await page.route('**/api/v1/homes**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [{ id: '11111111-1111-1111-1111-111111111111', name: "The Madhavan Residence", role: 'OWNER' }],
        }),
      });
    });
  });

  test('Super Admin Dashboard loads telemetry, KPIs, and country breakdown', async ({ page }) => {
    await page.goto('/admin');

    await expect(page.getByRole('heading', { name: 'Platform Overview & Operational Control Center' })).toBeVisible();
    await expect(page.getByText('Total User Accounts')).toBeVisible();
    await expect(page.getByText('Total Households')).toBeVisible();
    await expect(page.getByText('Regional Commercial Performance')).toBeVisible();
    await expect(page.getByText('India').first()).toBeVisible();
    await expect(page.getByText('United Arab Emirates').first()).toBeVisible();
  });

  test('Super Admin can navigate and view Regional Pricing Configuration', async ({ page }) => {
    await page.goto('/admin/regions');

    await expect(page.getByRole('heading', { name: 'Regional Configuration & Dynamic Pricing' })).toBeVisible();
    await expect(page.getByText('India').first()).toBeVisible();
    await expect(page.getByText('RAZORPAY')).toBeVisible();
    await expect(page.getByText('18.00%')).toBeVisible();
    await expect(page.getByText('United Arab Emirates').first()).toBeVisible();
    await expect(page.getByText('STRIPE')).toBeVisible();

    // Verify Add Country Modal triggers
    await page.getByRole('button', { name: 'Add Supported Country' }).click();
    await expect(page.getByText('Country Code (ISO-2) *')).toBeVisible();
  });

  test('Super Admin can edit subscription plans and add regional price versions', async ({ page }) => {
    await page.goto('/admin/subscriptions');

    await expect(page.getByText('Configured Subscription Plans')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Home Standard OS' })).toBeVisible();
    await expect(page.getByText('HOME_STANDARD')).toBeVisible();

    // Open Edit Plan Modal
    await page.getByRole('button', { name: 'Edit Plan' }).first().click();
    await expect(page.getByRole('heading', { name: /Edit Subscription Plan/i })).toBeVisible();
    await page.getByRole('button', { name: 'Save Plan Changes' }).click();
    await expect(page.getByRole('heading', { name: /Edit Subscription Plan/i })).not.toBeVisible();

    // Verify update success banner and plan heading
    await expect(page.getByText(/updated successfully/i)).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Home Standard OS' })).toBeVisible();

    // Open Add Price Version Modal
    await page.getByRole('button', { name: 'Add Price Version' }).first().click();
    await expect(page.getByRole('heading', { name: /Create Price Version/i })).toBeVisible();
    await page.getByRole('button', { name: 'Publish Price Version' }).click();
    await expect(page.getByRole('heading', { name: /Create Price Version/i })).not.toBeVisible();
  });

  test('Super Admin can edit coupons, modify discount, and view redemptions audit log', async ({ page }) => {
    await page.goto('/admin/coupons');

    await expect(page.getByText('Coupons, Campaigns & Grants')).toBeVisible();
    await expect(page.getByText('LAUNCH50', { exact: true })).toBeVisible();
    await expect(page.getByText(/50(\.00)?%\s*Off/i)).toBeVisible();

    // Open Edit Coupon Modal
    await page.getByRole('button', { name: 'Edit' }).first().click();
    await expect(page.getByRole('heading', { name: /Edit Coupon: LAUNCH50/i })).toBeVisible();
    await page.getByRole('button', { name: 'Save Changes' }).click();
    await expect(page.getByRole('heading', { name: /Edit Coupon: LAUNCH50/i })).not.toBeVisible();

    // Verify update success banner
    await expect(page.getByText(/Coupon "LAUNCH50" updated successfully/i)).toBeVisible();

    // Open Redemptions Log Modal
    await page.getByRole('button', { name: /Redemptions/i }).first().click();
    await expect(page.getByRole('heading', { name: /Redemptions Audit Log/i })).toBeVisible();
    await expect(page.getByText('$50.00')).toBeVisible();
  });

  test('Super Admin can inspect Global Invitations Desk', async ({ page }) => {
    await page.goto('/admin/invitations');

    await expect(page.getByRole('heading', { name: 'Global Household Invitations Desk' })).toBeVisible();
    await expect(page.getByText('OZ-FE9EDU')).toBeVisible();
    await expect(page.getByText('The Madhavan Residence')).toBeVisible();
    await expect(page.getByText('+919876543210')).toBeVisible();
  });

  test('Super Admin can inspect Feature Flags Console', async ({ page }) => {
    await page.goto('/admin/feature-flags');

    await expect(page.getByRole('heading', { name: 'Feature Flags & Rollout Controls' })).toBeVisible();
    await expect(page.getByText('AI Smart Replenishment')).toBeVisible();
    await expect(page.getByText('smart_pantry_ai_replenish')).toBeVisible();
    await expect(page.getByText('100%')).toBeVisible();
  });

  test('Super Admin can inspect AI & Automations Operations Desk', async ({ page }) => {
    await page.goto('/admin/ai-automations');

    await expect(page.getByRole('heading', { name: 'AI Intelligence & Automations Operations' })).toBeVisible();
    await expect(page.getByText('GEMINI / gemini-1.5-flash')).toBeVisible();
    await expect(page.getByText('Platform Automation Quarantine Desk')).toBeVisible();
    await expect(page.getByText('Restock Coffee Beans')).toBeVisible();
    await expect(page.getByText('Restore & Reset')).toBeVisible();
  });
});
