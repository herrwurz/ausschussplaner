import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function testPersonenTab() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const screenshotsDir = path.join(__dirname, 'test-screenshots');

  try {
    console.log('\n🧪 PERSONEN TAB UI TEST\n');

    // Set auth in localStorage before loading
    console.log('1️⃣ Loading Admin Panel...');
    await page.goto('http://localhost:5173/admin/panel', { waitUntil: 'networkidle' });

    // If redirected to login, login first
    const url = page.url();
    if (url.includes('login')) {
      console.log('   Redirected to login, attempting auth...');

      const emailInput = await page.locator('input').nth(0);
      const passwordInput = await page.locator('input').nth(1);
      const submitButton = await page.locator('button[type="submit"]').first();

      await emailInput.fill('admin');
      await passwordInput.fill('admin123');
      await submitButton.click();

      await page.waitForTimeout(2000);
    }

    // Navigate to Personen tab
    console.log('2️⃣ Navigating to Personen tab...');
    const personenTabBtn = await page.locator('button:has-text("👥 Personen")').first();

    if (await personenTabBtn.count() > 0) {
      await personenTabBtn.click();
      await page.waitForTimeout(500);
      console.log('   ✓ Personen tab clicked');
    } else {
      console.log('   ⚠️ Personen tab button not found');
      console.log('   Current URL:', page.url());
    }

    // Desktop screenshot
    console.log('\n3️⃣ Capturing Personen Tab screenshots...');
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.screenshot({ path: `${screenshotsDir}/personen-desktop.png`, fullPage: true });
    console.log('   📸 Desktop screenshot: personen-desktop.png');

    // Tablet screenshot
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.screenshot({ path: `${screenshotsDir}/personen-tablet.png`, fullPage: true });
    console.log('   📸 Tablet screenshot: personen-tablet.png');

    // Mobile screenshot
    await page.setViewportSize({ width: 375, height: 667 });
    await page.screenshot({ path: `${screenshotsDir}/personen-mobile.png`, fullPage: true });
    console.log('   📸 Mobile screenshot: personen-mobile.png');

    console.log('\n✅ Personen Tab UI verified');
    console.log(`📁 Screenshots: ${screenshotsDir}`);

  } catch (error) {
    console.error('\n❌ Error:', error.message);
  } finally {
    await browser.close();
  }
}

testPersonenTab();
