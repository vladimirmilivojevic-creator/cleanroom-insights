import { expect, test } from "@playwright/test";
import { loginAs } from "./helpers";

test("wrong password shows an error", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("trainer@alpine.demo");
  await page.getByLabel("Password").fill("wrong-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Incorrect email or password")).toBeVisible();
});

test("pages need a login", async ({ page }) => {
  await page.goto("/analytics");
  await expect(page).toHaveURL(/\/login$/);
});

test("trainee only sees own progress", async ({ page }) => {
  await loginAs(page, "Trainee");
  await expect(page).toHaveURL(/\/trainees\/\d+$/);
  await expect(page.getByRole("heading", { name: "Lukas Gruber" })).toBeVisible();
  await expect(page.getByRole("link", { name: "My progress" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Audit trail" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Analytics" })).toHaveCount(0);
});

test("trainer cannot see admin pages", async ({ page }) => {
  await loginAs(page, "Trainer");
  await expect(page.getByRole("link", { name: "Analytics" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Audit trail" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Users" })).toHaveCount(0);
});
