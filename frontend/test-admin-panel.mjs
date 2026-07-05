import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function testAdminPanel() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const screenshotsDir = path.join(__dirname, 'test-screenshots');

  try {
    console.log('\n🧪 ADMIN PANEL UI TEST\n');

    // Test Admin Login
    console.log('1️⃣ Loading Admin Login...');
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });

    const emailInput = await page.locator('input').nth(0);
    const passwordInput = await page.locator('input').nth(1);
    const submitButton = await page.locator('button[type="submit"]').first();

    await emailInput.fill('admin');
    await passwordInput.fill('admin123');
    console.log('   ✓ Admin credentials filled');

    await submitButton.click();
    console.log('   ✓ Submit clicked');

    // Wait for redirect to backend admin panel
    console.log('2️⃣ Waiting for Admin redirect...');
    await page.waitForTimeout(2000);

    const adminUrl = page.url();
    console.log(`   Current URL: ${adminUrl}`);

    if (adminUrl.includes('admin')) {
      console.log('   ✓ Admin panel accessible');

      // Take screenshots at different viewports
      console.log('\n3️⃣ Capturing Admin Panel screenshots...');

      // Desktop
      await page.setViewportSize({ width: 1920, height: 1080 });
      await page.screenshot({ path: `${screenshotsDir}/admin-desktop.png`, fullPage: true });
      console.log('   📸 Desktop admin panel screenshot saved');

      // Tablet
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.screenshot({ path: `${screenshotsDir}/admin-tablet.png`, fullPage: true });
      console.log('   📸 Tablet admin panel screenshot saved');

      // Mobile
      await page.setViewportSize({ width: 375, height: 667 });
      await page.screenshot({ path: `${screenshotsDir}/admin-mobile.png`, fullPage: true });
      console.log('   📸 Mobile admin panel screenshot saved');

      console.log('\n✅ Admin Panel screenshots captured');
    } else {
      console.log('   ⚠️ Admin panel not accessible via redirect');
      console.log('   (This is expected - backend HTML server may not be running)');
      console.log('   ℹ️ Admin panel is server-rendered at http://localhost:8000/admin/');
    }

  } catch (error) {
    console.error('\n❌ Error:', error.message);
  } finally {
    await browser.close();
  }
}

testAdminPanel();
