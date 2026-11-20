import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { after, before, test } from "node:test";

const require = createRequire(import.meta.url);
const { chromium, devices } = require(process.env.BOKEBI_PLAYWRIGHT_MODULE ?? "playwright");
const baseURL = process.env.BOKEBI_BASE_URL ?? "http://127.0.0.1:8000";
const phone = devices["Pixel 7"];
let browser;

before(async () => {
  browser = await chromium.launch({ executablePath: process.env.BOKEBI_CHROMIUM_PATH });
});

after(async () => {
  await browser?.close();
});

test("desktop keyboard help flow, optional poll, undistinguished votes and return by bookmark", async () => {
  const creator = await browser.newContext({ baseURL, permissions: ["clipboard-read", "clipboard-write"] });
  const errors = [];
  const desktop = await creator.newPage();
  desktop.on("pageerror", (error) => errors.push(error.message));
  await desktop.goto("/");
  await desktop.getByRole("link", { name: "Confidentialité", exact: true }).first().focus();
  await desktop.keyboard.press("Tab");
  const helpLink = desktop.getByRole("link", { name: "Recevoir de l’aide", exact: true }).first();
  assert.equal(await helpLink.evaluate((link) => document.activeElement === link), true);
  assert.equal(await helpLink.evaluate((link) => getComputedStyle(link).outlineStyle), "solid");
  await desktop.keyboard.press("Enter");
  await desktop.waitForURL("**/aide/");
  assert.match(desktop.url(), /\/aide\/$/);
  await desktop.getByLabel("Ton adresse e-mail").fill("creator@example.com");
  await desktop.getByRole("button", { name: "Envoyer ma demande" }).click();
  await desktop.getByRole("link", { name: "Partager avec tes collègues" }).click();
  await desktop.getByLabel("Nom de code").fill("Équipe framboise");
  await desktop.getByRole("button", { name: "Créer le lien de partage" }).click();

  const pollURL = await desktop.getByLabel("Lien du sondage").inputValue();
  assert.match(pollURL, /\/s\/[a-f0-9]{32}\/$/);
  assert.equal(await desktop.getByText("Partager sur WhatsApp", { exact: true }).isVisible(), false);
  await desktop.getByRole("button", { name: "Copier le lien" }).click();
  await desktop.getByText("Lien copié.", { exact: true }).waitFor();
  assert.equal(await desktop.getByRole("status").textContent(), "Lien copié.");
  assert.equal(await desktop.evaluate(() => navigator.clipboard.readText()), pollURL);
  const resultsPath = await desktop.getByRole("link", { name: "Voir les résultats" }).getAttribute("href");
  assert.match(resultsPath, /\/results\/$/);

  for (let count = 1; count <= 3; count += 1) {
    const visitor = await browser.newContext({ baseURL, javaScriptEnabled: count !== 1 });
    const page = await visitor.newPage();
    await page.goto(pollURL);
    assert.equal(await page.locator('input[type="email"]').count(), 0);
    const none = page.getByLabel("Aucune de ces situations ne me concerne");
    if (count === 2) {
      const choice = page.getByLabel("Mes heures supplémentaires");
      await choice.check();
      await none.check();
      assert.equal(await choice.isChecked(), false);
      await choice.check();
      assert.equal(await none.isChecked(), false);
    } else {
      await none.check();
    }
    await page.getByRole("button", { name: "Envoyer mes réponses" }).click();
    await page.waitForURL(`**${resultsPath}`);
    assert.equal(await page.locator("meter").count(), count === 3 ? 5 : 0);
    if (count === 1) {
      assert.equal(await page.getByLabel("Lien du sondage").inputValue(), pollURL);
      await page.getByRole("link", { name: "Recevoir de l’aide" }).click();
      await page.getByLabel("Ton adresse e-mail").fill("colleague@example.com");
      await page.getByRole("button", { name: "Envoyer ma demande" }).click();
      await page.getByRole("link", { name: "Retourner aux résultats" }).click();
      await page.waitForURL(`**${resultsPath}`);
      assert.match(page.url(), /\/results\/$/);
    }
    await visitor.close();
  }
  await desktop.goto(resultsPath);
  assert.equal(await desktop.locator("meter").count(), 5);
  assert.deepEqual(errors, []);
  await creator.close();
});

test("smartphone exposes an editable WhatsApp draft and preserves a usable narrow layout", async () => {
  const mobile = await browser.newContext({ ...phone, baseURL });
  const page = await mobile.newPage();
  await page.goto("/aide/");
  await page.getByLabel("Ton adresse e-mail").fill("mobile@example.com");
  await page.getByRole("button", { name: "Envoyer ma demande" }).click();
  await page.getByRole("link", { name: "Partager avec tes collègues" }).click();
  await page.getByRole("button", { name: "Créer le lien de partage" }).click();
  const share = page.getByRole("link", { name: "Partager sur WhatsApp" });
  assert.equal(await share.isVisible(), true);
  const draft = new URL(await share.getAttribute("href"));
  const pollURL = await page.getByLabel("Lien du sondage").inputValue();
  assert.equal(draft.origin, "https://wa.me");
  assert.equal(draft.searchParams.get("text"), `Salut ! Voici un petit sondage sur nos conditions de travail. Si tu veux y répondre : ${pollURL}`);
  await page.setViewportSize({ width: 842, height: 390 });
  assert.equal(await share.isVisible(), true);
  await page.setViewportSize({ width: 320, height: 650 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), 320);
  const input = page.getByLabel("Lien du sondage");
  assert.equal(await input.evaluate((field) => getComputedStyle(field).borderRadius), "0px");
  const copy = page.getByRole("button", { name: "Copier le lien" });
  assert.equal(await copy.evaluate((button) => getComputedStyle(button).backgroundColor), "rgba(0, 0, 0, 0)");
  const desktop = await browser.newContext({ baseURL, viewport: { width: 390, height: 650 } });
  const narrowDesktop = await desktop.newPage();
  await narrowDesktop.goto(`${pollURL}results/`);
  assert.equal(await narrowDesktop.getByText("Partager sur WhatsApp", { exact: true }).isVisible(), false);
  await desktop.close();
  await mobile.close();
});
