# OpenCode Zen 直接 API 配置核对

核对日期：2026-08-24。

## 结论

- MiMo-V2.5 Free 的直接 API 模型 ID 是 `mimo-v2.5-free`。OpenCode 官方把它列为 OpenAI-compatible 模型，完整请求端点是 `https://opencode.ai/zen/v1/chat/completions`（[OpenCode Zen：Endpoints](https://opencode.ai/docs/zen/#endpoints)）。
- 如果客户端会自行在 Base URL 后追加 `/chat/completions`，Base URL 应配置为 `https://opencode.ai/zen/v1`，不能填完整请求端点，否则会重复拼接路径。这是根据官方公布的完整端点作出的客户端配置推论。
- 直接调用 HTTP API 时，请求体中的模型应写 `mimo-v2.5-free`。`opencode/mimo-v2.5-free` 只用于 OpenCode 自身的模型配置或 `--model` 参数：OpenCode 的完整模型名采用 `provider_id/model_id` 格式，其中 Zen 的 provider ID 是 `opencode`（[OpenCode：Models](https://opencode.ai/docs/models/#set-a-default)，[OpenCode Zen：Endpoints](https://opencode.ai/docs/zen/#endpoints)）。因此不要把 `opencode/` 前缀发送给 Zen 的直接 API。
- OpenCode 表示其提供商通常遵循零保留且不使用数据训练模型，但 MiMo-V2.5 Free 是明确例外：免费期间，收集的数据可能被用于改进模型。官方同时说明 Zen 模型托管在美国；因此不应向该免费模型提交密钥、个人信息或其他敏感数据（[OpenCode Zen：Privacy](https://opencode.ai/docs/zen/#privacy)）。

## 本地冒烟测试记录

2026-08-24 的本地真实 API 冒烟测试成功：生成 5 个问题，耗时 41,669 ms，总计 817 tokens。记录不包含测试提示、模型输出、API Key 或私有配置。
