import { chromium } from 'playwright';
import * as path from 'path';
import * as fs from 'fs';

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const screenshotsDir = '/Users/vivek/.gemini/antigravity/brain/e417cc97-7d7a-4622-ab0c-93f6404efdd2/real_ui_audit';
  if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir, { recursive: true });
  }

  console.log('1. Navigating to /admin/login...');
  await page.goto('http://localhost:3000/admin/login');
  await page.waitForLoadState('networkidle');

  const adminEmail = process.env.SUPER_ADMIN_EMAIL || process.env.ADMIN_EMAIL || 'admin@example.com';
  const adminPassword = process.env.SUPER_ADMIN_PASSWORD || process.env.ADMIN_PASSWORD || '';
  await page.fill('#admin-login-email', adminEmail);
  await page.fill('#admin-login-password', adminPassword);
  await page.click('#admin-submit-btn');

  await page.waitForURL('**/admin**', { timeout: 15000 });
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: path.join(screenshotsDir, '01_real_admin_dashboard.png'), fullPage: true });
  console.log('Saved 01_real_admin_dashboard.png');

  console.log('3. Navigating to /admin/subscriptions...');
  await page.goto('http://localhost:3000/admin/subscriptions');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(screenshotsDir, '02_real_admin_subscriptions.png'), fullPage: true });
  console.log('Saved 02_real_admin_subscriptions.png');

  console.log('4. Navigating to /admin/coupons...');
  await page.goto('http://localhost:3000/admin/coupons');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(screenshotsDir, '03_real_admin_coupons.png'), fullPage: true });
  console.log('Saved 03_real_admin_coupons.png');

  console.log('5. Navigating to /admin/regions...');
  await page.goto('http://localhost:3000/admin/regions');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(screenshotsDir, '04_real_admin_regions.png'), fullPage: true });
  console.log('Saved 04_real_admin_regions.png');

  await browser.close();
  console.log('Inspection complete.');
}

main().catch(err => {
  console.error('Inspection failed:', err);
  process.exit(1);
});
