import { chromium } from 'playwright';

async function test() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
  page.on('pageerror', err => console.log('BROWSER ERROR:', err.message));
  page.on('requestfailed', req => console.log('REQ FAILED:', req.url(), req.failure()?.errorText));

  console.log('Navigating to login...');
  await page.goto('http://localhost:3000/admin/login');

  const adminEmail = process.env.SUPER_ADMIN_EMAIL || process.env.ADMIN_EMAIL || 'admin@example.com';
  const adminPassword = process.env.SUPER_ADMIN_PASSWORD || process.env.ADMIN_PASSWORD || '';
  await page.fill('#admin-login-email', adminEmail);
  await page.fill('#admin-login-password', adminPassword);
  
  console.log('Clicking submit...');
  await page.click('#admin-submit-btn');

  console.log('Waiting for response...');
  await page.waitForTimeout(5000);

  console.log('Current URL:', page.url());
  const html = await page.content();
  console.log('Has Platform text?', html.includes('Platform Overview') || html.includes('Operations Console'));

  await browser.close();
}

test().catch(console.error);
