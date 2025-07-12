const { chromium, firefox, webkit } = require('playwright');
const fs = require('fs');
const path = require('path');
require('dotenv').config({ override: true });

// Load sensitive data from environment variables
const SENSITIVE_DATA = {};

// Helper function for replacing sensitive data
function replaceSensitiveData(text, sensitiveMap) {
  if (typeof text !== 'string') return text;
  for (const [placeholder, value] of Object.entries(sensitiveMap)) {
    const searchPattern = `<secret>${placeholder}</secret>`;
    const replacementValue = value || '';
    text = text.replace(new RegExp(searchPattern, 'g'), replacementValue);
  }
  return text;
}

// Custom error class
class PlaywrightActionError extends Error {
  constructor(message) {
    super(message);
    this.name = 'PlaywrightActionError';
  }
}

// Helper function for robust action execution
async function tryLocateAndAct(page, selector, actionType, text = null, stepInfo = '') {
  console.log(`Attempting ${actionType} (${stepInfo}) using selector: ${JSON.stringify(selector)}`);
  const originalSelector = selector;
  const MAX_FALLBACKS = 50;
  const INITIAL_TIMEOUT = 10000; // 10 seconds
  const FALLBACK_TIMEOUT = 1000; // 1 second

  try {
    const locator = page.locator(selector).first();
    if (actionType === 'click') {
      await locator.click({ timeout: INITIAL_TIMEOUT });
    } else if (actionType === 'fill' && text !== null) {
      await locator.fill(text, { timeout: INITIAL_TIMEOUT });
    } else {
      throw new PlaywrightActionError(`Invalid actionType '${actionType}' or missing text for fill. (${stepInfo})`);
    }
    console.log(`  Action '${actionType}' successful with original selector.`);
    await page.waitForTimeout(500);
    return;
  } catch (e) {
    console.log(`  Warning: Action '${actionType}' failed with original selector (${JSON.stringify(selector)}): ${e}. Starting fallback...`);

    if (!selector.startsWith('xpath=')) {
      throw new PlaywrightActionError(`Action '${actionType}' failed. Fallback not possible for non-XPath selector: ${JSON.stringify(selector)}. (${stepInfo})`);
    }

    const xpathParts = selector.split('=');
    if (xpathParts.length < 2) {
      throw new PlaywrightActionError(`Action '${actionType}' failed. Could not extract XPath string from selector: ${JSON.stringify(selector)}. (${stepInfo})`);
    }
    const xpath = xpathParts[1];
    const segments = xpath.split('/').filter(seg => seg);

    for (let i = 1; i <= Math.min(MAX_FALLBACKS, segments.length - 1); i++) {
      const trimmedXpathRaw = segments.slice(i).join('/');
      const fallbackXpath = `xpath=//${trimmedXpathRaw}`;

      console.log(`    Fallback attempt ${i}/${MAX_FALLBACKS}: Trying selector: ${JSON.stringify(fallbackXpath)}`);
      try {
        const locator = page.locator(fallbackXpath).first();
        if (actionType === 'click') {
          await locator.click({ timeout: FALLBACK_TIMEOUT });
        } else if (actionType === 'fill' && text !== null) {
          try {
            await locator.clear({ timeout: FALLBACK_TIMEOUT });
            await page.waitForTimeout(100);
          } catch (clearError) {
            console.log(`    Warning: Failed to clear field during fallback (${stepInfo}): ${clearError}`);
          }
          await locator.fill(text, { timeout: FALLBACK_TIMEOUT });
        }

        console.log(`    Action '${actionType}' successful with fallback selector: ${JSON.stringify(fallbackXpath)}`);
        await page.waitForTimeout(500);
        return;
      } catch (fallbackError) {
        console.log(`    Fallback attempt ${i} failed: ${fallbackError}`);
        if (i === MAX_FALLBACKS) {
          throw new PlaywrightActionError(`Action '${actionType}' failed after ${MAX_FALLBACKS} fallback attempts. Original selector: ${JSON.stringify(originalSelector)}. (${stepInfo})`);
        }
      }
    }
  }

  throw new PlaywrightActionError(`Action '${actionType}' failed unexpectedly for ${JSON.stringify(originalSelector)}. (${stepInfo})`);
}

async function runGeneratedScript() {
  let browser = null;
  let context = null;
  let page = null;
  let exitCode = 0; // Default success exit code
  try {
    console.log('Launching chromium browser...');
    browser = await chromium.launch({ headless: false });
    context = await browser.newContext({});
    console.log('Browser context created.');
    // Initial page handling
    if (context.pages().length > 0) {
      page = context.pages()[0];
      console.log('Using initial page provided by context.');
    } else {
      page = await context.newPage();
      console.log('Created a new page as none existed.');
    }
    console.log('\n--- Starting Generated Script Execution ---');

    // --- Step 1 ---
    // Action 1
    console.log(`Navigating to: https://www.wikipedia.org (Step 1, Action 1)`);
    await page.goto("https://www.wikipedia.org", { timeout: 5000 });
    await page.waitForLoadState('load', { timeout: 5000 });
    await page.waitForTimeout(1000);

    // --- Step 2 ---
    // Action 2
    await tryLocateAndAct(page, "xpath=html/body/main/div[2]/form/fieldset/div/input", 'fill', replaceSensitiveData("Python programming", SENSITIVE_DATA), "Step 2, Action 1");
    // Action 3
    // Invalid action format: {} (Step 2, Action 2)

    // --- Step 3 ---
    // Action 4
    await tryLocateAndAct(page, "xpath=html/body/main/div[2]/form/fieldset/button", 'click', null, "Step 3, Action 1");

    // --- Step 4 ---
    // Action 5
    console.log(`Scrolling down by 500 pixels (Step 4, Action 1)`);
    await page.evaluate(() => window.scrollBy(0, 500));
    await page.waitForTimeout(500);

    // --- Step 5 ---
    // Action 6
    console.log('\n--- Task marked as Done by agent (Step 5, Action 1) ---');
    console.log(`Agent reported success: true`);
    // Final Message from agent (may contain placeholders):
    const finalMessage = replaceSensitiveData("I have successfully navigated to the Wikipedia page for 'Python programming', searched for the topic, and scrolled down the page. The task is complete.", SENSITIVE_DATA);
    console.log(finalMessage);
  } catch (pae) {
    if (pae instanceof PlaywrightActionError) {
      console.error(`\n--- Playwright Action Error: ${pae.message} ---`);
      exitCode = 1;
    } else {
      console.error(`\n--- An unexpected error occurred: ${pae} ---`);
      console.error(pae.stack);
      exitCode = 1;
    }
  } finally {
    console.log('\n--- Generated Script Execution Finished ---');
    console.log('Closing browser/context...');
    if (context) {
      try { await context.close(); }
      catch (ctxCloseErr) { console.error(`  Warning: could not close context: ${ctxCloseErr}`); }
    }
    if (browser) {
      try { await browser.close(); }
      catch (browserCloseErr) { console.error(`  Warning: could not close browser: ${browserCloseErr}`); }
    }
    console.log('Browser/context closed.');
    if (exitCode !== 0) {
      console.error(`Script finished with errors (exit code ${exitCode}).`);
      process.exit(exitCode);
    }
  }
}

// Script Entry Point
runGeneratedScript().catch(console.error);