import { chromium } from 'playwright';
import * as path from 'path';
import * as fs from 'fs';

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', err => console.log('PAGE ERROR:', err.message));

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

  console.log('3. Waiting for navigation to /admin...');
  await page.waitForURL('**/admin', { timeout: 15000 });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(screenshotsDir, '01_real_admin_dashboard.png'), fullPage: true });
  console.log('Saved 01_real_admin_dashboard.png');

  console.log('4. Navigating to Subscriptions page via link...');
  await page.click('a[href="/admin/subscriptions"]');
  await page.waitForURL('**/admin/subscriptions', { timeout: 10000 });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(screenshotsDir, '02_real_admin_subscriptions.png'), fullPage: true });
  console.log('Saved 02_real_admin_subscriptions.png');

  console.log('5. Checking for Edit button on Plan...');
  const editPlanBtn = page.locator('button:has-text("Edit Plan")').first();
  if (await editPlanBtn.isVisible()) {
    console.log('Edit Plan button is visible! Clicking it...');
    await editPlanBtn.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(screenshotsDir, '02b_real_edit_plan_modal.png'), fullPage: true });
    console.log('Saved 02b_real_edit_plan_modal.png');
    // Close modal
    const cancelBtn = page.locator('button:has-text("Cancel")').first();
    if (await cancelBtn.isVisible()) await cancelBtn.click();
  } else {
    console.log('WARNING: Edit Plan button NOT visible!');
  }

  console.log('6. Navigating to Coupons page via link...');
  await page.click('a[href="/admin/coupons"]');
  await page.waitForURL('**/admin/coupons', { timeout: 10000 });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(screenshotsDir, '03_real_admin_coupons.png'), fullPage: true });
  console.log('Saved 03_real_admin_coupons.png');

  console.log('7. Checking for Edit button on Coupon...');
  const editCouponBtn = page.locator('button:has-text("Edit")').first();
  if (await editCouponBtn.isVisible()) {
    console.log('Edit Coupon button is visible! Clicking it...');
    await editCouponBtn.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(screenshotsDir, '03b_real_edit_coupon_modal.png'), fullPage: true });
    console.log('Saved 03b_real_edit_coupon_modal.png');
    // Close modal
    const cancelBtn = page.locator('button:has-text("Cancel")').first();
    if (await cancelBtn.isVisible()) await cancelBtn.click();
  } else {
    console.log('WARNING: Edit Coupon button NOT visible!');
  }

  console.log('8. Navigating to Regional Pricing page via link...');
  await page.click('a[href="/admin/regions"]');
  await page.waitForURL('**/admin/regions', { timeout: 10000 });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(screenshotsDir, '04_real_admin_regions.png'), fullPage: true });
  console.log('Saved 04_real_admin_regions.png');

  await browser.close();
  console.log('Live UI flow capture complete.');
}

main().catch(err => {
  console.error('Flow failed:', err);
  process.exit(1);
});
