import { expect, test, type Page } from "@playwright/test";

const email = () => `e2e-${Date.now()}-${Math.floor(Math.random() * 1e6)}@gigbid.dev`;

async function onboard(page: Page) {
  await page.goto("/login");
  await page.getByRole("tab", { name: "Create account" }).click();
  await page.getByLabel("Email").fill(email());
  await page.getByLabel("Password").fill("password-123");
  await page.getByLabel("Saved searches (comma separated)").fill("python");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/inbox/);
}

async function draftReady(page: Page) {
  await onboard(page);
  await page.getByRole("button", { name: "Check for new jobs" }).click();
  await expect(page.getByText("Needs your approval")).toBeVisible({ timeout: 40_000 });
  await page.getByText("Build a customer churn prediction baseline").click();
  await expect(page.getByTestId("letter")).toBeVisible();
}

test("onboarding creates an account and lands on an empty inbox", async ({ page }) => {
  await onboard(page);
  await expect(page.getByRole("heading", { name: "Inbox", exact: true })).toBeVisible();
  await expect(page.getByText("Your inbox is empty")).toBeVisible();
});

test("approving a proposal sends it and moves it to Submitted", async ({ page }) => {
  await draftReady(page);
  await expect(page.locator("mark.claim").first()).toBeVisible();
  await expect(page.getByText(/Sends a \$\d+/)).toBeVisible();
  await page.getByRole("button", { name: "Approve and send" }).click();
  await expect(page.getByText("Sent to the marketplace as a draft.")).toBeVisible({ timeout: 30_000 });
  await page.getByRole("link", { name: "Pipeline" }).click();
  await expect(page.getByRole("region", { name: "Submitted" }).getByText("Build a customer churn")).toBeVisible();
});

test("rejecting requires a reason", async ({ page }) => {
  await draftReady(page);
  await page.getByRole("button", { name: "Reject" }).click();
  const confirm = page.getByRole("button", { name: "Reject draft" });
  await expect(confirm).toBeDisabled();
  await page.getByTestId("reject-reason").fill("Client wants on-site work");
  await confirm.click();
  await expect(page.getByText("You rejected this draft.")).toBeVisible({ timeout: 30_000 });
});

test("editing a draft re-checks it and asks for approval again", async ({ page }) => {
  await draftReady(page);
  await page.getByRole("button", { name: "Edit" }).click();
  const box = page.getByTestId("edit-box");
  await box.fill((await box.inputValue()) + "\n\nI can start this week.");
  await page.getByRole("button", { name: "Save and re-check" }).click();
  await expect(page.getByTestId("letter")).toContainText("I can start this week.", { timeout: 30_000 });
  await expect(page.getByRole("button", { name: "Approve and send" })).toBeVisible();
});

test("shows a degraded-mode banner when the marketplace is down", async ({ page }) => {
  await page.route("**/api/health", (r) => r.fulfill({ json: { api: true, mcp: { portfolio: true, marketplace: false, workspace: true }, degraded: true } }));
  await onboard(page);
  await expect(page.getByTestId("degraded-banner")).toContainText("Marketplace connection is down");
});
