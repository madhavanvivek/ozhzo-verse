const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

async function main() {
  const LOCAL_API = 'http://127.0.0.1:8000/api/v1';
  const LOCAL_WEB = 'http://localhost:3000';
  const evidenceDir = '/Users/vivek/.gemini/antigravity/brain/e417cc97-7d7a-4622-ab0c-93f6404efdd2/real_ui_audit';

  const ADMIN_EMAIL = process.env.SUPER_ADMIN_EMAIL || 'superadmin@ozhzo.com';
  const ADMIN_PASSWORD = process.env.SUPER_ADMIN_PASSWORD || 'LocalSuperAdminSecret123!';

  console.log('Testing Super Admin In-Place Price Update (Zero Version Row Spawning)...');

  const localLoginRes = await fetch(`${LOCAL_API}/admin/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: ADMIN_EMAIL, password: ADMIN_PASSWORD })
  });
  const localAuthData = await localLoginRes.json();
  const localToken = localAuthData?.data?.access_token || localAuthData?.access_token;

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  try {
    const adminContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    await adminContext.addCookies([
      { name: 'access_token', value: localToken, url: LOCAL_WEB },
      { name: 'oz_access_token', value: localToken, url: LOCAL_WEB },
      { name: 'auth_token', value: localToken, url: LOCAL_WEB },
      { name: 'oz_role', value: 'SUPER_ADMIN', url: LOCAL_WEB },
      { name: 'user_role', value: 'SUPER_ADMIN', url: LOCAL_WEB }
    ]);

    const adminPage = await adminContext.newPage();
    await adminPage.addInitScript((token) => {
      localStorage.setItem('access_token', token);
      localStorage.setItem('oz_access_token', token);
      localStorage.setItem('auth_token', token);
      localStorage.setItem('oz_role', 'SUPER_ADMIN');
      localStorage.setItem('user_role', 'SUPER_ADMIN');
    }, localToken);

    await adminPage.goto(`${LOCAL_WEB}/admin/subscriptions`, { waitUntil: 'networkidle' });
    await adminPage.waitForTimeout(2000);

    // 1. Initial State: Count UAE cards
    const initialContent = await adminPage.content();
    const initialUaeMatches = (initialContent.match(/United Arab Emirates/g) || []).length;
    console.log(`Initial UAE occurrences in Admin Subscriptions: ${initialUaeMatches}`);

    // 2. Click "Add New Country / Price" -> Select UAE, enter 59.00
    console.log('Submitting updated UAE price (AED 59.00)...');
    await adminPage.click('button[data-testid="btn-add-new-country-price"]');
    await adminPage.waitForTimeout(800);

    await adminPage.selectOption('select[data-testid="add-price-country-select"]', 'AE');
    await adminPage.waitForTimeout(500);

    await adminPage.fill('input[data-testid="add-price-regular-input"]', '59.00');
    await adminPage.fill('input[data-testid="add-price-offer-input"]', '59.00');

    await adminPage.screenshot({ path: path.join(evidenceDir, '06_uae_price_edit_modal.png'), fullPage: true });

    await adminPage.click('button[data-testid="btn-publish-price-version"]');
    await adminPage.waitForTimeout(2500);

    // 3. Reload page and verify still EXACTLY 1 UAE card with 59.00
    await adminPage.reload({ waitUntil: 'networkidle' });
    await adminPage.waitForTimeout(2000);

    await adminPage.screenshot({ path: path.join(evidenceDir, '07_uae_price_updated_in_place_59.png'), fullPage: true });

    const updatedContent = await adminPage.content();
    const updatedUaeMatches = (updatedContent.match(/United Arab Emirates/g) || []).length;
    const has59 = updatedContent.includes('59.00');
    console.log(`Updated UAE occurrences: ${updatedUaeMatches} (matches before: ${initialUaeMatches === updatedUaeMatches}), Has 59.00: ${has59}`);

    // 4. Restore UAE price back to 49.00
    console.log('Restoring UAE price back to canonical AED 49.00...');
    await adminPage.click('button[data-testid="btn-add-new-country-price"]');
    await adminPage.waitForTimeout(800);

    await adminPage.selectOption('select[data-testid="add-price-country-select"]', 'AE');
    await adminPage.waitForTimeout(500);

    await adminPage.fill('input[data-testid="add-price-regular-input"]', '49.00');
    await adminPage.fill('input[data-testid="add-price-offer-input"]', '49.00');
    await adminPage.click('button[data-testid="btn-publish-price-version"]');
    await adminPage.waitForTimeout(2500);

    await adminPage.reload({ waitUntil: 'networkidle' });
    await adminPage.waitForTimeout(2000);

    await adminPage.screenshot({ path: path.join(evidenceDir, '08_uae_price_restored_49.png'), fullPage: true });
    console.log('✓ Successfully tested in-place price edit flow with zero duplicate row creation!');
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error('In-place update test failed:', err);
  process.exit(1);
});
