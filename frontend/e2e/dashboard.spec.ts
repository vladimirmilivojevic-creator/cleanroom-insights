import { expect, test } from "@playwright/test";
import { loginAs } from "./helpers";

test("trainer watches a simulated session live", async ({ page }) => {
  await loginAs(page, "Trainer");
  await expect(page.getByRole("heading", { name: "Training dashboard" })).toBeVisible();
  await expect(page.getByTestId("stat-Trainees")).toHaveText("6");

  await page.getByRole("button", { name: "Start simulated session" }).click();
  await expect(page).toHaveURL(/\/sessions\/\d+$/);

  // events arrive over the WebSocket while the simulation runs
  await expect(page.getByTestId("event-stream").locator("li").first()).not.toHaveText(/Waiting/);
  await expect(page.getByText(/^(passed|failed)$/)).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("Final score")).toBeVisible();
});

test("analytics shows the heatmap and the DuckDB report", async ({ page }) => {
  await loginAs(page, "Trainer");
  await page.getByRole("link", { name: "Analytics" }).click();
  await expect(page.getByTestId("heatmap")).toBeVisible();
  await expect(page.getByTestId("etl-last-run")).toContainText("Last ETL run");
});

test("admin sees an intact audit chain", async ({ page }) => {
  await loginAs(page, "Admin");
  await page.getByRole("link", { name: "Audit trail" }).click();
  await expect(page.getByTestId("chain-status")).toContainText("Chain intact");
  await expect(page.getByText("user.login").first()).toBeVisible();
});

test("certificate page is public and printable", async ({ page }) => {
  await loginAs(page, "Trainee");
  await page.locator('a[href^="/certificates/"]').first().click();
  await expect(page.getByTestId("certificate-name")).toHaveText("Lukas Gruber");
  await expect(page.getByRole("button", { name: /Print/ })).toBeVisible();
});
