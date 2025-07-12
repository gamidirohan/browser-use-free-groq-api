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

module.exports = {
  replaceSensitiveData,
  PlaywrightActionError,
  tryLocateAndAct
};
