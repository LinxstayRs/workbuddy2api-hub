# Zeabur 安全部署

本 fork 默认将容器视为公网部署：`WB_REQUIRE_PANEL_PASSWORD=1`。首次启动前必须在 Zeabur 服务的 Variables / Secrets 中配置强面板密码，否则进程会拒绝启动，不会带着默认 `admin` 裸露到公网。

## 1. 从 GitHub 部署

1. 在 Zeabur 新建服务，选择本仓库 `LinxstayRs/workbuddy2api-hub`。
2. 使用仓库内 `Dockerfile` 构建，不要改用上游 `latest` 镜像。
3. 暴露容器端口 `8788`，健康检查路径使用 `/health`。
4. 为 `/app/accounts` 与 `/app/usage` 分别挂载持久卷。

## 2. 必要环境变量

- `PANEL_PASSWORD`：必填，至少 12 字符，不能是 `admin`。使用 Zeabur Secret，不要写进仓库。
- `API_KEY`：强烈建议填入随机长字符串并作为 Secret；用于 `/v1/*` API 鉴权。
- `PORT=8788`
- `HOST=0.0.0.0`
- `WB_REQUIRE_PANEL_PASSWORD=1`
- `TZ=Asia/Shanghai`（按需要修改）

若没有显式设置 `API_KEY`，容器的 `--lan` 模式仍会生成高强度 Key，并写入持久化的 `accounts/settings.json`；公网部署更建议显式使用 Secret，方便客户端配置与轮换。

## 3. 持久化与权限

- `/app/accounts`：账号 OAuth 凭证、面板密码摘要与 API Key 配置。程序会尽力将目录设为 `0700`，JSON 凭证设为 `0600`。
- `/app/usage`：用量与活动日志。

Zeabur 卷在不同底层文件系统上可能不会完整呈现 POSIX mode bits；即使如此，也必须依赖平台服务隔离与 Secret 管理，绝不能将卷公开共享。

## 4. 首次验证

部署日志不应出现默认密码警告。依次验证：

1. `GET /health` 返回 200。
2. 面板只接受 `PANEL_PASSWORD`。
3. 不带 Key 请求 `GET /v1/models` 应返回 401；带 `Authorization: Bearer <API_KEY>` 后成功。
4. 先只导入一个测试账号，确认模型列表、非流式请求、流式请求及 `/v1/messages` 正常，再加入常用账号。

## 5. 安全说明

- 不要把面板密码放进 URL 的 `?pwd=`；公网代理与浏览器历史可能记录查询参数。
- 不建议开启 Watchtower 或自动追踪 `latest`。先审计 upstream 更新，再合并到此 fork。
- WorkBuddy / CodeBuddy 逆向接口可能触发上游风控；先用测试账号与低并发验证。