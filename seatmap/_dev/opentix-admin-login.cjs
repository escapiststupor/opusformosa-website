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

async function pageDiagnostic(page) {
  return page.evaluate(() => ({
    url: window.location.href,
    title: document.title,
    text: document.body.innerText.slice(0, 1200),
    inputs: [...document.querySelectorAll("input")].map((input) => ({
      type: input.type,
      name: input.name,
      placeholder: input.placeholder,
      visible: Boolean(input.offsetWidth || input.offsetHeight || input.getClientRects().length),
    })),
    buttons: [...document.querySelectorAll("button")].map((button) => ({
      text: button.innerText.trim(),
      className: String(button.className || ""),
      visible: Boolean(button.offsetWidth || button.offsetHeight || button.getClientRects().length),
    })),
    scripts: [...document.querySelectorAll("script[src]")].map((script) => script.src).slice(-12),
  }));
}

function printDiagnostic(label, diagnostic, extras = {}) {
  console.error(`[diagnostic] ${label}`);
  console.error(
    JSON.stringify(
      {
        ...extras,
        ...diagnostic,
      },
      null,
      2
    )
  );
}

async function waitForLoginForm(page, loginUrl, diagnostics) {
  const usernameLocator = page.locator('input[name="username"], input[placeholder*="帳號"], input[type="email"], input[type="text"]').first();
  const passwordLocator = page.locator('input[name="password"], input[type="password"], input[placeholder*="密碼"]').first();

  for (let attempt = 1; attempt <= 2; attempt += 1) {
    try {
      await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
      await usernameLocator.waitFor({ state: "visible", timeout: 60000 });
      await passwordLocator.waitFor({ state: "visible", timeout: 60000 });
      return { usernameInput: usernameLocator, passwordInput: passwordLocator };
    } catch (error) {
      diagnostics.formErrors.push(String(error.message || error));
      const diagnostic = await pageDiagnostic(page).catch((diagError) => ({ diagnosticError: String(diagError.message || diagError) }));
      printDiagnostic(`login form not ready, attempt ${attempt}`, diagnostic, { formErrors: diagnostics.formErrors });
      if (attempt === 2) {
        throw error;
      }
      await page.goto(loginUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
    }
  }
  throw new Error("Could not find OPENTIX login form.");
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

    const diagnostics = {
      consoleErrors: [],
      failedRequests: [],
      cognitoMessages: [],
      formErrors: [],
    };
    page.on("console", (message) => {
      if (["error", "warning"].includes(message.type())) {
        diagnostics.consoleErrors.push(`${message.type()}: ${message.text()}`.slice(0, 500));
      }
    });
    page.on("pageerror", (error) => {
      diagnostics.consoleErrors.push(`pageerror: ${String(error.message || error).slice(0, 500)}`);
    });
    page.on("requestfailed", (request) => {
      diagnostics.failedRequests.push(`${request.failure()?.errorText || "failed"} ${request.url()}`.slice(0, 500));
    });

    await page.goto(loginUrl, { waitUntil: "domcontentloaded", timeout: 60000 });

    const { usernameInput, passwordInput } = await waitForLoginForm(page, loginUrl, diagnostics);

    await usernameInput.fill(username);
    await passwordInput.fill(password);

    const authPromise = new Promise((resolve, reject) => {
      const timeout = setTimeout(async () => {
        const diagnostic = await pageDiagnostic(page).catch((error) => ({ diagnosticError: String(error.message || error) }));
        printDiagnostic("timed out waiting for Cognito AuthenticationResult", diagnostic, diagnostics);
        reject(new Error("Timed out waiting for Cognito AuthenticationResult."));
      }, 90000);
      page.on("response", async (response) => {
        try {
          if (!response.url().includes("cognito-idp.ap-northeast-1.amazonaws.com")) return;
          if (response.request().method() !== "POST") return;
          const payload = await response.json();
          if (payload && (payload.message || payload.__type)) {
            diagnostics.cognitoMessages.push(`${payload.__type || "Cognito"}: ${payload.message || ""}`.slice(0, 500));
          }
          if (payload && payload.AuthenticationResult && payload.AuthenticationResult.AccessToken) {
            clearTimeout(timeout);
            resolve(payload.AuthenticationResult);
          }
        } catch (_error) {
          // Ignore non-JSON or partial Cognito responses.
        }
      });
    });

    const loginButton = await firstVisible(page.getByRole("button", { name: /登\s*入|login/i }));
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
