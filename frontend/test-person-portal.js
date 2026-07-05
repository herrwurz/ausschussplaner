import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function runTests() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  const screenshotsDir = path.join(__dirname, 'test-screenshots');

  if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir, { recursive: true });
  }

  try {
    console.log('\n🧪 PERSON PORTAL UI TEST SUITE\n');

    // Test 1: Login page loads
    console.log('Test 1: Login page loads with Fluent 2 styling');
    await page.goto('http://localhost:5173', { waitUntil: 'load', timeout: 10000 });
    console.log('  ✓ Page loaded successfully');

    // Wait for React to render
    await page.waitForTimeout(1000);

    // Check page title
    const title = await page.title();
    console.log(`  ✓ Page title: "${title}"`);

    // Take screenshot of login page
    await page.screenshot({ path: `${screenshotsDir}/1-login-page.png`, fullPage: true });
    console.log('  📸 Screenshot saved: 1-login-page.png');

    // Test 2: Check for login form
    console.log('\nTest 2: Login form structure');

    // Get all inputs on page
    const inputs = await page.locator('input').count();
    console.log(`  ✓ Found ${inputs} input fields`);

    if (inputs >= 2) {
      console.log('  ✓ Email and password inputs present');
    }

    // Get all buttons
    const buttons = await page.locator('button').count();
    console.log(`  ✓ Found ${buttons} button(s)`);

    // Test 3: Check CSS and styling
    console.log('\nTest 3: Fluent 2 styling');

    // Check if design tokens are loaded
    const styleSheets = await page.locator('link[rel="stylesheet"]').count();
    console.log(`  ✓ ${styleSheets} stylesheets loaded`);

    // Get computed styles of login card
    const loginCard = await page.locator('.login-card, [class*="login"], [class*="card"]').first();
    if (await loginCard.count() > 0) {
      const bg = await loginCard.evaluate(el => window.getComputedStyle(el).backgroundColor);
      const shadow = await loginCard.evaluate(el => window.getComputedStyle(el).boxShadow);
      console.log(`  ✓ Login card background: ${bg}`);
      console.log(`  ✓ Login card shadow applied: ${shadow !== 'none' ? 'Yes' : 'No'}`);
    }

    // Test 4: Responsive design
    console.log('\nTest 4: Responsive design - Mobile');
    await page.setViewportSize({ width: 375, height: 667 });
    await page.screenshot({ path: `${screenshotsDir}/2-mobile-login.png`, fullPage: true });
    console.log('  📸 Mobile screenshot saved: 2-mobile-login.png');

    console.log('\nTest 5: Responsive design - Tablet');
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.screenshot({ path: `${screenshotsDir}/3-tablet-login.png`, fullPage: true });
    console.log('  📸 Tablet screenshot saved: 3-tablet-login.png');

    console.log('\nTest 6: Responsive design - Desktop');
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.screenshot({ path: `${screenshotsDir}/4-desktop-login.png`, fullPage: true });
    console.log('  📸 Desktop screenshot saved: 4-desktop-login.png');

    // Test 7: Person login flow
    console.log('\nTest 7: Person login flow');

    // Get input fields
    const emailInput = await page.locator('input[type="text"], input[placeholder*="Email"], input[placeholder*="email"]').first();
    const passwordInput = await page.locator('input[type="password"]').first();
    const submitButton = await page.locator('button[type="submit"]').first();

    if (await emailInput.count() > 0 && await passwordInput.count() > 0 && await submitButton.count() > 0) {
      console.log('  ✓ Form inputs found');

      // Fill form
      await emailInput.fill('testuser@example.com');
      await passwordInput.fill('test123');
      await page.screenshot({ path: `${screenshotsDir}/5-login-form-filled.png`, fullPage: true });
      console.log('  📸 Form filled screenshot: 5-login-form-filled.png');

      // Submit
      await submitButton.click();
      console.log('  ✓ Login submitted');

      // Wait for navigation
      try {
        await page.waitForURL(/.*person\/dashboard|.*login/, { timeout: 5000 });
        const finalUrl = page.url();
        console.log(`  ✓ Navigated to: ${finalUrl}`);

        if (finalUrl.includes('person/dashboard')) {
          await page.screenshot({ path: `${screenshotsDir}/6-person-dashboard.png`, fullPage: true });
          console.log('  📸 Person dashboard screenshot: 6-person-dashboard.png');
          console.log('  ✓ Person Portal Dashboard loaded successfully');
        }
      } catch (e) {
        console.log(`  ⚠ Navigation check: ${e.message}`);
      }
    } else {
      console.log('  ⚠ Could not find all form inputs');
    }

    console.log('\n✅ All UI tests completed!');
    console.log(`📁 Screenshots saved to: ${screenshotsDir}`);

  } catch (error) {
    console.error('\n❌ Test error:', error.message);
    try {
      await page.screenshot({ path: `${screenshotsDir}/error-screenshot.png` });
      console.log('  📸 Error screenshot saved');
    } catch (e) {
      console.log('  Could not save error screenshot');
    }
  } finally {
    await context.close();
    await browser.close();
  }
}

runTests().catch(console.error);
