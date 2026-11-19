import argparse
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

GRAPH = 'https://graph.microsoft.com/v1.0'
CACHE = Path(os.environ.get('TEAMS_CACHE_DIR', Path.home() / '.local' / 'share' / 'teams-ai-assistant')) / 'msal-cache.bin'
SCOPES = ['User.Read', 'User.ReadBasic.All', 'Chat.Create', 'Chat.ReadBasic', 'Chat.Read', 'ChatMessage.Send']
AI_LABEL = '🤖 AI 助手代发\n'


def request(url, data=None, token=None):
    headers = {'Accept': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    if data is not None:
        if token:
            data = json.dumps(data).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        else:
            data = urllib.parse.urlencode(data).encode('utf-8')
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            payload = {'error': 'http_error', 'error_description': str(exc)}
        raise ApiError(payload) from exc


class ApiError(Exception):
    def __init__(self, payload):
        self.payload = payload
        super().__init__(json.dumps(payload, ensure_ascii=False))


def login():
    client = os.environ.get('TEAMS_CLIENT_ID', 'e8907370-77d6-4c55-917c-e177de591b07')
    tenant = os.environ.get('TEAMS_TENANT_ID', '93acd104-0887-4c59-bb44-885eb0e256ba')
    if not client or not tenant:
        raise ValueError('请设置 TEAMS_CLIENT_ID 和 TEAMS_TENANT_ID。')
    try:
        import msal
        from msal_extensions import PersistedTokenCache, build_encrypted_persistence
    except ImportError as exc:
        raise ValueError('请使用安装脚本创建的 Python 虚拟环境，或安装 requirements.txt 中的依赖。') from exc
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    try:
        persistence = build_encrypted_persistence(str(CACHE))
        cache = PersistedTokenCache(persistence)
        app = msal.PublicClientApplication(client, authority='https://login.microsoftonline.com/' + tenant, token_cache=cache)
        accounts = app.get_accounts()
        if len(accounts) > 1:
            raise ValueError('缓存中有多个账户，请清理缓存后选择一个账户登录。')
        if accounts:
            result = app.acquire_token_silent(SCOPES, account=accounts[0])
            if result and 'access_token' in result:
                return result['access_token']
        flow = app.initiate_device_flow(scopes=SCOPES)
        if 'user_code' not in flow:
            raise ValueError('无法启动设备登录：' + flow.get('error_description', '未知错误'))
        print(flow['message'], file=sys.stderr, flush=True)
        result = app.acquire_token_by_device_flow(flow)
        if 'access_token' not in result:
            raise ValueError('登录失败：' + result.get('error_description', result.get('error', '未知错误')))
        return result['access_token']
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('安全令牌存储或登录失败：' + str(exc)) from exc


def main():
    parser = argparse.ArgumentParser(description='Microsoft Teams Graph 命令行工具')
    sub = parser.add_subparsers(dest='command', required=True)
    users = sub.add_parser('users', help='按名称或邮箱查找用户')
    users.add_argument('--query', required=True)
    sub.add_parser('login', help='登录或验证已保存的登录')
    sub.add_parser('chats', help='列出已加入的聊天')
    messages = sub.add_parser('messages', help='读取指定单聊或群聊的近期消息')
    messages.add_argument('--chat-id', required=True, help='聊天 ID，可通过 chats 查询')
    messages.add_argument('--limit', type=int, default=20, help='最多读取的消息数（1–200，默认 20）')
    send = sub.add_parser('send', help='发送单聊或群聊消息')
    target = send.add_mutually_exclusive_group(required=True)
    target.add_argument('--user-id', help='新建或取得与该用户的一对一聊天')
    target.add_argument('--chat-id', help='现有单聊或群聊的 ID')
    send.add_argument('--message', required=True)
    args = parser.parse_args()
    if args.command == 'messages' and not 1 <= args.limit <= 200:
        parser.error('--limit 必须在 1 到 200 之间')
    token = login()
    if args.command == 'login':
        me = request(GRAPH + '/me?$select=id,displayName,userPrincipalName', token=token)
        print(json.dumps(me, ensure_ascii=False, indent=2))
        return
    if args.command == 'users':
        term = args.query.replace("'", "''")
        params = {'$filter': f"startswith(displayName,'{term}') or startswith(mail,'{term}') or startswith(userPrincipalName,'{term}')", '$select': 'id,displayName,mail,userPrincipalName', '$top': '25'}
        result = request(GRAPH + '/users?' + urllib.parse.urlencode(params), token=token)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == 'chats':
        url = GRAPH + '/me/chats?$top=50'
        while url:
            result = request(url, token=token)
            print(json.dumps(result.get('value', []), ensure_ascii=False, indent=2))
            url = result.get('@odata.nextLink')
    elif args.command == 'messages':
        url = GRAPH + '/chats/' + urllib.parse.quote(args.chat_id, safe='') + '/messages?' + urllib.parse.urlencode({'$top': min(args.limit, 50)})
        collected = []
        has_more = False
        while url and len(collected) < args.limit:
            parsed = urllib.parse.urlsplit(url)
            if parsed.scheme != 'https' or parsed.netloc != 'graph.microsoft.com':
                raise ValueError('Microsoft Graph 返回了不受信任的分页地址。')
            page = request(url, token=token)
            values = page.get('value', [])
            remaining = args.limit - len(collected)
            collected.extend(values[:remaining])
            url = page.get('@odata.nextLink')
            has_more = len(values) > remaining or bool(url)
        print(json.dumps({'chatId': args.chat_id, 'messages': collected, 'hasMore': has_more}, ensure_ascii=False, indent=2))
    elif args.command == 'send':
        if not args.message.strip():
            raise ValueError('消息不能为空。')
        if args.user_id:
            uid = str(uuid.UUID(args.user_id))
            me = request(GRAPH + '/me?$select=id', token=token)
            members = [{'@odata.type': '#microsoft.graph.aadUserConversationMember', 'roles': ['owner'], 'user@odata.bind': GRAPH + "/users('" + member_id + "')"} for member_id in (me['id'], uid)]
            chat_id = request(GRAPH + '/chats', {'chatType': 'oneOnOne', 'members': members}, token)['id']
        else:
            chat_id = args.chat_id
        result = request(GRAPH + '/chats/' + urllib.parse.quote(chat_id, safe='') + '/messages', {'body': {'contentType': 'text', 'content': AI_LABEL + args.message}}, token)
        print(json.dumps({'chatId': chat_id, 'messageId': result['id'], 'createdDateTime': result.get('createdDateTime')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ApiError, ValueError, OSError, urllib.error.URLError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
