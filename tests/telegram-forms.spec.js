// @ts-check
const { test, expect } = require('@playwright/test');

const BASE_URL = 'https://shinsetsu-hair.shop';

/** Minimal 1x1 PNG for required photo upload */
const TEST_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  'base64'
);

test.describe('Заявки на shinsetsu-hair.shop', () => {
  test('форма оценки волос — POST /api/calculate успешен', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });

    await page.locator('#color-select').selectOption('blonde');
    await page.locator('#length-select').selectOption('50-60');
    await page.locator('#structure-select').selectOption('straight');
    await page.locator('#condition-select').selectOption('slavic');
    await page.locator('#name-input').fill('Playwright Test');
    await page.locator('#phone-input').fill('+79991234567');
    await page.locator('#city-input').fill('Москва');
    await page.locator('#email-input').fill('playwright-test@example.com');
    await page.locator('#message-input').fill('Автотест Playwright — можно удалить');

    await page.locator('input[name="photo1"]').setInputFiles({
      name: 'test-hair.png',
      mimeType: 'image/png',
      buffer: TEST_PNG,
    });

    const [response] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes('/api/calculate') && r.request().method() === 'POST'
      ),
      page.locator('#calcForm button[type="submit"]').click(),
    ]);

    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.success).toBe(true);
    expect(typeof body.price).toBe('number');
    expect(body.price).toBeGreaterThan(0);

    await expect(page.locator('#customModal')).toHaveClass(/show/);
    await expect(page.locator('#modalTitle')).toHaveText('Успешно!');
  });

  test('форма обратного звонка — POST /api/callback успешен', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });

    await page.locator('#footer-fullname').fill('Playwright Callback');
    await page.locator('#footer-phone').fill('+79997654321');

    const [response] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes('/api/callback') && r.request().method() === 'POST'
      ),
      page.locator('#footerForm button[type="submit"]').click(),
    ]);

    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.success).toBe(true);

    await expect(page.locator('#customModal')).toHaveClass(/show/);
    await expect(page.locator('#modalTitle')).toHaveText('Заявка принята');
  });
});
