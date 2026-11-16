import { expect, type Page } from "@playwright/test";

export async function loginAs(page: Page, role: "Trainer" | "Admin" | "Trainee") {
  await page.goto("/login");
  await page.getByRole("button", { name: new RegExp(`Log in as ${role}`) }).click();
  await expect(page.getByTestId("current-user")).toBeVisible();
}
