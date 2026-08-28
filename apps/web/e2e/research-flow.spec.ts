import { expect, test } from "@playwright/test";

test("用户可以创建研究、看到完成报告并刷新恢复", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("演示访问码").fill("e2e-portfolio-access");
  await page.getByRole("button", { name: "进入演示" }).click();
  await expect(page.getByRole("heading", { name: "你想研究什么？" })).toBeVisible();

  await page.getByRole("textbox").fill(
    "验证浏览器端到端流程能够创建研究任务完成报告并在刷新后恢复",
  );
  await page.getByRole("button", { name: "开始研究" }).click();

  await expect(page).toHaveURL(/\/research\/[0-9a-f-]+/);
  const runId = page.url().split("/").at(-1);
  expect(runId).toBeTruthy();
  await expect(page.getByRole("heading", { name: "研究结果" })).toBeVisible();
  await expect(page.getByText("模拟结果", { exact: false })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("引用覆盖")).toBeVisible();

  await page.reload();
  await expect(page.getByText("模拟结果", { exact: false })).toBeVisible();
  await expect(page.getByText("已结束")).toBeVisible();

  await page.goto("/");
  let nativeDialogOpened = false;
  page.on("dialog", async (dialog) => {
    nativeDialogOpened = true;
    await dialog.dismiss();
  });
  const runCard = page
    .locator(`a[href="/research/${runId}"]`)
    .locator("xpath=ancestor::article");
  await runCard.getByRole("button", { name: "重命名" }).click();
  await expect(page.getByRole("dialog", { name: "重命名研究记录" })).toBeVisible();
  expect(nativeDialogOpened).toBe(false);
  await page.getByLabel("新的研究记录标题").fill("浏览器端到端研究记录");
  await page.getByRole("button", { name: "保存" }).click();
  const renamedRunLink = page.locator(`a[href="/research/${runId}"]`);
  await expect(renamedRunLink).toHaveText("浏览器端到端研究记录");

  const renamedCard = renamedRunLink.locator("xpath=ancestor::article");
  await renamedCard.getByRole("button", { name: "归档", exact: true }).click();
  await expect(page.locator(`a[href="/research/${runId}"]`)).toHaveCount(0);

  await page.getByLabel("显示归档").check();
  const archivedCard = page
    .locator(`a[href="/research/${runId}"]`)
    .locator("xpath=ancestor::article");
  await expect(archivedCard.getByText("已归档", { exact: true })).toBeVisible();
  await archivedCard.getByRole("button", { name: "取消归档" }).click();
  await expect(archivedCard.getByText("已完成", { exact: true })).toBeVisible();
});
