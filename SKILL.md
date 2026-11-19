---
name: teams-ai-assistant
description: 通过 Microsoft Graph 以用户身份查询 Teams 联系人和聊天，并向单聊或已有群聊发送带 AI 标识的消息。
---

# Teams AI Assistant

按 [README.md](README.md) 配置并运行 `scripts/teams.py`。先查询并核实目标，仅在用户授权发送时执行 `send`。发送命令自动添加 AI 标识，无需重复添加。首次登录需要用户在微软页面完成设备登录；不要读取、输出或分享加密缓存。登录或权限失败时报告错误，不要绕过。该工具不支持频道消息或读取聊天正文。
