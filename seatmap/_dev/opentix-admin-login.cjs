#!/usr/bin/env node
"use strict";

function loadPlaywright() {
  const candidates = [
    "playwright",
    process.env.PLAYWRIGHT_MODULE_PATH,
    "/Users/pyen/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright",
  ].filter(Boolean);
  for (const candidate of candidates) {
    try {
      return require(candidate);
    } catch (error) {
      if (candidate === candidates[candidates.length - 1]) {
        throw error;
      }
    }
  }
  throw new Error("Playwright is not available.");
}

async function firstVisible(locator) {
  const count = await locator.count();
  for (let index = 0; index < count; index += 1) {
    const item = locator.nth(index);
    if (await item.isVisible().catch(() => false)) {
      return item;
    }
  }
  return null;
}

async function main() {
  const username = process.env.OPENTIX_ADMIN_USERNAME;
  const password = process.env.OPENTIX_ADMIN_PASSWORD;
  const loginUrl = process.env.OPENTIX_ADMIN_LOGIN_URL || "https://opt.console.opentix.life/organizer/index.html#/login";

  if (!username || !password) {
    throw new Error("Missing OPENTIX_ADMIN_USERNAME or OPENTIX_ADMIN_PASSWORD.");
  }

  const { chromium } = loadPlaywright();
  const launchOptions = {
    headless: process.env.OPENTIX_HEADLESS !== "0",
  };
  if (process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE) {
    launchOptions.executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE;
  }

  const browser = await chromium.launch(launchOptions);
  try {
    const page = await browser.newPage({
      viewport: { width: 1440, height: 1000 },
      userAgent:
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    });

    const authPromise = new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error("Timed out waiting for Cognito AuthenticationResult.")), 90000);
      page.on("response", async (response) => {
        try {
          if (!response.url().includes("cognito-idp.ap-northeast-1.amazonaws.com")) return;
          if (response.request().method() !== "POST") return;
          const payload = await response.json();
          if (payload && payload.AuthenticationResult && payload.AuthenticationResult.AccessToken) {
            clearTimeout(timeout);
            resolve(payload.AuthenticationResult);
          }
        } catch (_error) {
          // Ignore non-JSON or partial Cognito responses.
        }
      });
    });

    await page.goto(loginUrl, { waitUntil: "domcontentloaded", timeout: 60000 });

    const passwordInput = page.locator('input[type="password"]').first();
    await passwordInput.waitFor({ state: "visible", timeout: 60000 });

    const usernameInput =
      (await firstVisible(page.locator('input[name="username"], input[name="account"], input[type="text"], input[type="email"], input:not([type])'))) ||
      (await firstVisible(page.locator("input").filter({ hasNot: passwordInput })));

    if (!usernameInput) {
      throw new Error("Could not find OPENTIX username input.");
    }

    await usernameInput.fill(username);
    await passwordInput.fill(password);

    const loginButton = await firstVisible(page.getByRole("button", { name: /登入|login/i }));
    if (loginButton) {
      await loginButton.click();
    } else {
      await passwordInput.press("Enter");
    }

    const result = await authPromise;
    process.stdout.write(
      JSON.stringify({
        accessToken: result.AccessToken,
        idToken: result.IdToken,
        refreshToken: result.RefreshToken,
        expiresIn: result.ExpiresIn,
        tokenType: result.TokenType,
      })
    );
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
