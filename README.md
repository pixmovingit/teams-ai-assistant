# Teams AI Assistant

使用 Microsoft Graph 委托权限，以登录用户身份读取 Teams 单聊或已有群聊消息，并向聊天发送消息。每条发送的消息自动以「🤖 AI 助手代发」开头。

## 让 AI 安装

把以下提示词发送给具有本机操作权限的 AI 助手：

> 请帮我从 https://github.com/pixmovingit/teams-ai-assistant 安装或更新 Teams AI Assistant 技能。请根据当前 AI 工具和操作系统确定技能安装位置，检查并配置运行环境，阅读仓库中的安装说明和脚本，完成安装并确保当前工具能发现该技能；如已安装，请保留本地修改和登录缓存，再更新技能及依赖。安装后验证登录：如果需要，请提供微软设备登录网址和一次性代码，由我用自己的公司账号完成登录。完成后告诉我结果；如需重新加载或重启当前工具，请提醒我。请勿读取或分享密码、令牌，也不要发送测试消息。

仓库访问需要相应 GitHub 权限。仓库自带安装脚本默认安装到 Codex 技能目录，不会覆盖已有同名技能。其他 AI 工具需要将技能文件安装到该工具支持的位置，并根据其加载方式配置；能否发现和执行该技能取决于工具自身的能力。更新时先检查并保留本地修改，替换技能目录的源码及依赖文件，并使用该目录虚拟环境运行 `python -m pip install -r requirements.txt`。默认应用配置属于本公司，其他组织可设置 `TEAMS_CLIENT_ID` 和 `TEAMS_TENANT_ID` 环境变量覆盖。

## 环境与管理员配置

- Windows、macOS 或 Linux，以及 Python 3.9 或更高版本和 Git。安装脚本在技能目录创建虚拟环境并安装 MSAL 依赖。
- Linux 需要可用且已解锁的 Secret Service（如 GNOME Keyring）和用户 D-Bus 会话；无桌面或无密钥服务的服务器需先配置安全存储。不会降级为明文令牌。
- 在 Microsoft Entra 注册单租户公共客户端应用，启用公共客户端流。
- 配置 Microsoft Graph **委托权限**：`User.Read`、`User.ReadBasic.All`、`Chat.Create`、`Chat.ReadBasic`、`Chat.Read`、`ChatMessage.Send`，按组织策略授予同意。`Chat.Read` 用于读取当前用户可访问的聊天消息，`offline_access` 用于刷新令牌。增加权限后，已有用户可能需要重新登录或同意。
- 用户需拥有 Teams 访问权限，且只能以自己有权访问的身份和聊天操作。企业应用若要求分配，请先分配用户或组。

## 使用

安装：在克隆的仓库中，Windows 运行 `./install.ps1`，macOS/Linux 运行 `sh install.sh`。安装后重启 Codex。命令行使用时，Windows 调用技能目录的 `.venv/Scripts/python.exe`，macOS/Linux 调用 `.venv/bin/python`，例如：

```sh
~/.codex/skills/teams-ai-assistant/.venv/bin/python ~/.codex/skills/teams-ai-assistant/scripts/teams.py login
```

首次运行时，在微软设备登录页面输入代码并用自己的账号登录。MSAL 使用 Windows DPAPI、macOS 钥匙串或 Linux Secret Service 加密存储令牌；后续调用自动续期。组织策略、撤销授权或令牌失效仍可能要求重新登录。**从旧版升级后需重新登录一次**，旧版缓存不会自动迁移。不要共享或提交令牌缓存。退出时应在系统安全存储中删除对应凭据，并按需在微软账户或管理员中心撤销授权。

```powershell
<技能虚拟环境的python> scripts/teams.py users --query '姓名或邮箱前缀'
<技能虚拟环境的python> scripts/teams.py chats
<技能虚拟环境的python> scripts/teams.py messages --chat-id '<聊天ID>' --limit 20
<技能虚拟环境的python> scripts/teams.py send --user-id '<用户ID>' --message '你好'
<技能虚拟环境的python> scripts/teams.py send --chat-id '<已有群聊ID>' --message '大家好'
```

`users` 最多返回 25 条；`chats` 返回所有分页的聊天信息。`messages` 默认读取最近 20 条，`--limit` 可设为 1 至 200；输出为 Graph 原始消息，正文可能包含 HTML，`hasMore` 表示还有未读取的消息。读取范围受登录用户的 Teams 访问权限限制。请核对目标后发送。单聊命令会创建或取得一对一聊天；群聊命令发送到指定的已有聊天。暂不支持创建群聊、频道消息或下载附件。请勿向程序传入不可信的消息目标。首次申请权限或租户策略变化时，可能需要管理员再次同意。

这是供授权用户主动操作的工具，不会自行监控消息或自动回复。AI 标识是消息文字的一部分，不是 Teams 的原生标记。
