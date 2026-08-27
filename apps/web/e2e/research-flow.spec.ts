import { expect, test } from "@playwright/test";

test("用户可以创建研究、看到完成报告并刷新恢复", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("textbox").fill(
    "验证浏览器端到端流程能够创建研究任务完成报告并在刷新后恢复",
  );
  await page.getByRole("button", { name: "开始研究" }).click();

  await expect(page).toHaveURL(/\/research\/[0-9a-f-]+/);
  await expect(page.getByRole("heading", { name: "研究结果" })).toBeVisible();
  await expect(page.getByText("模拟结果", { exact: false })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("引用覆盖")).toBeVisible();

  await page.reload();
  await expect(page.getByText("模拟结果", { exact: false })).toBeVisible();
  await expect(page.getByText("已结束")).toBeVisible();
});
