// Test thread unrollers with Playwright headless Chromium
import { chromium } from 'playwright';

const TWEET_IDS = [
  '1851665654073753610',  // Karpathy
  '1725636940029157828',  // popular tech thread
];

async function testUnrollNow(browser, tweetId) {
  const page = await browser.newPage();
  const start = Date.now();
  try {
    // Try direct URL first
    const url = `https://unrollnow.com/status/${tweetId}`;
    console.log(`\n[UnrollNow] Fetching ${url}`);
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000); // extra time for JS

    const text = await page.evaluate(() => document.body.innerText);
    const wordCount = text.split(/\s+/).filter(w => w.length > 0).length;
    const elapsed = Date.now() - start;

    console.log(`[UnrollNow] Status: loaded in ${elapsed}ms`);
    console.log(`[UnrollNow] Word count: ${wordCount}`);
    console.log(`[UnrollNow] First 500 chars: ${text.substring(0, 500)}`);
    console.log(`[UnrollNow] Contains tweet-like content: ${wordCount > 50}`);

    return { service: 'UnrollNow', url, wordCount, elapsed, success: wordCount > 50 };
  } catch (e) {
    console.log(`[UnrollNow] ERROR: ${e.message}`);
    return { service: 'UnrollNow', error: e.message, success: false };
  } finally {
    await page.close();
  }
}

async function testUnrollNowForm(browser, tweetId) {
  const page = await browser.newPage();
  const start = Date.now();
  try {
    // Go to homepage and use the form
    console.log(`\n[UnrollNow-Form] Going to homepage, will paste tweet URL`);
    await page.goto('https://unrollnow.com', { waitUntil: 'networkidle', timeout: 30000 });

    // Find input field and submit
    const input = await page.$('input[type="text"], input[type="url"], input[placeholder*="tweet"], input[placeholder*="url"], input[placeholder*="URL"], textarea');
    if (!input) {
      // Try to find any input
      const inputs = await page.$$('input');
      console.log(`[UnrollNow-Form] Found ${inputs.length} inputs on page`);
      const html = await page.content();
      console.log(`[UnrollNow-Form] Page HTML (first 1000): ${html.substring(0, 1000)}`);
      return { service: 'UnrollNow-Form', error: 'No input field found', success: false };
    }

    const tweetUrl = `https://x.com/karpathy/status/${tweetId}`;
    await input.fill(tweetUrl);

    // Look for submit button
    const button = await page.$('button[type="submit"], button:has-text("Unroll"), button:has-text("Read"), button:has-text("Go")');
    if (button) {
      await button.click();
    } else {
      await input.press('Enter');
    }

    // Wait for content to load
    await page.waitForTimeout(10000);

    const text = await page.evaluate(() => document.body.innerText);
    const wordCount = text.split(/\s+/).filter(w => w.length > 0).length;
    const elapsed = Date.now() - start;

    console.log(`[UnrollNow-Form] Status: loaded in ${elapsed}ms`);
    console.log(`[UnrollNow-Form] Word count: ${wordCount}`);
    console.log(`[UnrollNow-Form] First 500 chars: ${text.substring(0, 500)}`);

    return { service: 'UnrollNow-Form', wordCount, elapsed, success: wordCount > 50 };
  } catch (e) {
    console.log(`[UnrollNow-Form] ERROR: ${e.message}`);
    return { service: 'UnrollNow-Form', error: e.message, success: false };
  } finally {
    await page.close();
  }
}

async function testXBeast(browser, tweetId) {
  const page = await browser.newPage();
  const start = Date.now();
  try {
    console.log(`\n[XBeast] Going to thread unroller page`);
    await page.goto('https://xbeast.io/tools/thread-unroller', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    // Find input and submit
    const input = await page.$('input[type="text"], input[type="url"], textarea');
    if (!input) {
      const html = await page.content();
      console.log(`[XBeast] Page HTML (first 1000): ${html.substring(0, 1000)}`);
      return { service: 'XBeast', error: 'No input field found', success: false };
    }

    const tweetUrl = `https://x.com/karpathy/status/${tweetId}`;
    await input.fill(tweetUrl);

    const button = await page.$('button[type="submit"], button:has-text("Unroll"), button:has-text("Read"), button:has-text("Get")');
    if (button) {
      await button.click();
    } else {
      await input.press('Enter');
    }

    await page.waitForTimeout(10000);

    const text = await page.evaluate(() => document.body.innerText);
    const wordCount = text.split(/\s+/).filter(w => w.length > 0).length;
    const elapsed = Date.now() - start;

    console.log(`[XBeast] Status: loaded in ${elapsed}ms`);
    console.log(`[XBeast] Word count: ${wordCount}`);
    console.log(`[XBeast] First 500 chars: ${text.substring(0, 500)}`);

    return { service: 'XBeast', wordCount, elapsed, success: wordCount > 50 };
  } catch (e) {
    console.log(`[XBeast] ERROR: ${e.message}`);
    return { service: 'XBeast', error: e.message, success: false };
  } finally {
    await page.close();
  }
}

async function testThreadNavigator(browser, tweetId) {
  const page = await browser.newPage();
  const start = Date.now();
  try {
    console.log(`\n[ThreadNavigator] Going to homepage`);
    await page.goto('https://threadnavigator.com', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    const text = await page.evaluate(() => document.body.innerText);
    const wordCount = text.split(/\s+/).filter(w => w.length > 0).length;
    const elapsed = Date.now() - start;

    console.log(`[ThreadNavigator] Status: loaded in ${elapsed}ms`);
    console.log(`[ThreadNavigator] Word count: ${wordCount}`);
    console.log(`[ThreadNavigator] First 500 chars: ${text.substring(0, 500)}`);

    // Try to find and use form
    const input = await page.$('input[type="text"], input[type="url"], textarea');
    if (input) {
      console.log(`[ThreadNavigator] Found input, attempting to submit tweet URL`);
      await input.fill(`https://x.com/karpathy/status/${tweetId}`);
      const button = await page.$('button[type="submit"], button:has-text("Unroll"), button:has-text("Read")');
      if (button) await button.click();
      else await input.press('Enter');
      await page.waitForTimeout(10000);

      const text2 = await page.evaluate(() => document.body.innerText);
      const wc2 = text2.split(/\s+/).filter(w => w.length > 0).length;
      console.log(`[ThreadNavigator] After submit - Word count: ${wc2}`);
      console.log(`[ThreadNavigator] After submit - First 500 chars: ${text2.substring(0, 500)}`);
      return { service: 'ThreadNavigator', wordCount: wc2, elapsed: Date.now() - start, success: wc2 > 50 };
    }

    return { service: 'ThreadNavigator', wordCount, elapsed, success: false };
  } catch (e) {
    console.log(`[ThreadNavigator] ERROR: ${e.message}`);
    return { service: 'ThreadNavigator', error: e.message, success: false };
  } finally {
    await page.close();
  }
}

async function main() {
  console.log('Launching headless Chromium...');
  const launchStart = Date.now();
  const browser = await chromium.launch({
    headless: true,
    executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
  });
  console.log(`Browser launched in ${Date.now() - launchStart}ms`);

  const tweetId = TWEET_IDS[0];

  const results = [];
  results.push(await testUnrollNow(browser, tweetId));
  results.push(await testUnrollNowForm(browser, tweetId));
  results.push(await testXBeast(browser, tweetId));
  results.push(await testThreadNavigator(browser, tweetId));

  console.log('\n\n=== SUMMARY ===');
  for (const r of results) {
    console.log(`${r.service}: ${r.success ? 'SUCCESS' : 'FAIL'} | Words: ${r.wordCount || 0} | Time: ${r.elapsed || 'N/A'}ms | Error: ${r.error || 'none'}`);
  }

  await browser.close();
}

main().catch(console.error);
