import { chromium } from 'playwright';

async function testLoginFlow() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    console.log('🧪 Testing Person Login Flow\n');

    // Load login page
    console.log('1️⃣ Loading CentralLogin...');
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
    console.log('   ✓ Page loaded');

    // Get form elements
    const emailInput = await page.locator('input').nth(0);
    const passwordInput = await page.locator('input').nth(1);
    const submitButton = await page.locator('button[type="submit"]').first();

    console.log('\n2️⃣ Filling login form...');
    await emailInput.fill('testuser@example.com');
    console.log('   ✓ Email filled: testuser@example.com');

    await passwordInput.fill('test123');
    console.log('   ✓ Password filled: test123');

    console.log('\n3️⃣ Submitting form...');
    await submitButton.click();

    // Wait for navigation or error
    console.log('4️⃣ Waiting for navigation...');
    const navigationPromise = page.waitForNavigation({ waitUntil: 'networkidle' }).catch(() => null);
    const timeoutPromise = new Promise(resolve => setTimeout(() => resolve('timeout'), 5000));

    const result = await Promise.race([navigationPromise, timeoutPromise]);

    const currentUrl = page.url();
    console.log(`   Current URL: ${currentUrl}`);

    if (currentUrl.includes('person/dashboard')) {
      console.log('\n✅ SUCCESS: Person Portal Dashboard loaded!');
      console.log('   Dashboard is accessible');
    } else if (currentUrl.includes('login')) {
      console.log('\n⚠️ Still on login page - checking for error messages...');
      const errorMsg = await page.locator('.error-message, [role="alert"]').first().textContent().catch(() => null);
      if (errorMsg) {
        console.log(`   Error: ${errorMsg.trim()}`);
      }
    } else {
      console.log(`\n✓ Navigated to: ${currentUrl}`);
    }

  } catch (error) {
    console.error('\n❌ Error:', error.message);
  } finally {
    await browser.close();
  }
}

testLoginFlow();
