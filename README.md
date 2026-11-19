# Teams AI Assistant

使用 Microsoft Graph 委托权限，以登录用户身份向 Teams 单聊或已有群聊发送消息。每条消息自动以「🤖 AI 助手代发」开头。

## 让 AI 安装

把以下提示词发送给具有本机操作权限的 Codex：

> 请从 https://github.com/pixmovingit/teams-ai-assistant 安装 Teams AI Assistant 技能。先检查 Windows、Git 和 Python 3.9+，再克隆仓库并检查 install.ps1；运行该脚本将技能安装到当前用户的 Codex 技能目录，并配置脚本内的公司客户端 ID 和租户 ID。若已有同名技能，请先检查并保留本地修改。安装完成后，将用户环境变量 TEAMS_CLIENT_ID 和 TEAMS_TENANT_ID 加载到当前进程，启动设备代码登录，将登录网址和代码告诉我，由我用自己的公司账号完成登录；验证登录后提醒我重启 Codex 以加载技能。不要读取或分享令牌，也不要发送任何测试消息。

仓库访问需要相应 GitHub 权限。安装脚本不会覆盖已有同名技能；若需更新，先检查本地修改，再将仓库新版本的 `SKILL.md`、`README.md` 和 `scripts/teams.py` 复制到技能目录。默认应用配置属于本公司，其他组织可向 `install.ps1` 传入 `-ClientId` 和 `-TenantId`。

## 环境与管理员配置

- Windows 和 Python 3.9 或更高版本；不需要额外 Python 包。
- 在 Microsoft Entra 注册单租户公共客户端应用，启用公共客户端流。
- 配置 Microsoft Graph **委托权限**：`User.Read`、`User.ReadBasic.All`、`Chat.Create`、`Chat.ReadBasic`、`ChatMessage.Send`，按组织策略授予同意。`offline_access` 用于刷新令牌。
- 用户需拥有 Teams 访问权限，且只能以自己有权访问的身份和聊天操作。企业应用若要求分配，请先分配用户或组。

## 使用

PowerShell 中设置应用配置（替换为管理员提供的 ID）：

```powershell
$env:TEAMS_CLIENT_ID = '<应用程序客户端ID>'
$env:TEAMS_TENANT_ID = '<目录租户ID>'
python scripts/teams.py login
```

首次运行时，打开命令提示中的微软设备登录网址并输入代码。每个使用者都必须使用自己的账号登录。刷新令牌使用 Windows DPAPI 以当前用户身份加密，保存在 `%LOCALAPPDATA%\TeamsAIAssistant\token.bin`。后续调用会自动刷新，无需每次登录；组织策略、撤销授权或令牌失效等情况仍可能要求重新登录。不要共享缓存，也不要将其提交到版本库。要退出可删除该缓存文件并按需在微软账户或管理员中心撤销授权。

```powershell
python scripts/teams.py users --query '姓名或邮箱前缀'
python scripts/teams.py chats
python scripts/teams.py send --user-id '<用户ID>' --message '你好'
python scripts/teams.py send --chat-id '<已有群聊ID>' --message '大家好'
```

`users` 最多返回 25 条；`chats` 返回所有分页的聊天信息。请核对目标后发送。单聊命令会创建或取得一对一聊天；群聊命令发送到指定的已有聊天。暂不支持创建群聊、频道消息、附件或读取消息正文。请勿向程序传入不可信的消息目标。首次申请权限或租户策略变化时，可能需要管理员再次同意。

这是供授权用户主动操作的工具，不会自行监控消息或自动回复。AI 标识是消息文字的一部分，不是 Teams 的原生标记。
