import argparse
import ctypes
from ctypes import wintypes
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
CACHE = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'TeamsAIAssistant' / 'token.bin'
SCOPES = ['offline_access', 'User.Read', 'User.ReadBasic.All', 'Chat.Create', 'Chat.ReadBasic', 'ChatMessage.Send']
AI_LABEL = '🤖 AI 助手代发\n'


class Blob(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_byte))]


def protect(data, decrypt=False):
    if sys.platform != 'win32':
        raise ValueError('令牌缓存仅支持 Windows 当前用户。')
    buf = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))
    target = Blob()
    crypt = ctypes.windll.crypt32
    kernel = ctypes.windll.kernel32
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    if decrypt:
        ok = crypt.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target))
    else:
        ok = crypt.CryptProtectData(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target))
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel.LocalFree(target.data)


def save_token(result, client, tenant):
    refresh = result.get('refresh_token')
    if not refresh:
        raise ValueError('微软未返回刷新令牌，无法保存登录状态。')
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    temp = CACHE.with_suffix('.tmp')
    temp.write_bytes(protect(json.dumps({'client': client, 'tenant': tenant, 'refresh_token': refresh}).encode('utf-8')))
    os.replace(temp, CACHE)


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
    client = os.environ.get('TEAMS_CLIENT_ID')
    tenant = os.environ.get('TEAMS_TENANT_ID')
    if not client or not tenant:
        raise ValueError('请设置 TEAMS_CLIENT_ID 和 TEAMS_TENANT_ID。')
    base = 'https://login.microsoftonline.com/' + urllib.parse.quote(tenant, safe='') + '/oauth2/v2.0/'
    scopes = SCOPES
    stored = {}
    if CACHE.exists():
        try:
            stored = json.loads(protect(CACHE.read_bytes(), decrypt=True).decode('utf-8'))
        except (OSError, ValueError, UnicodeDecodeError):
            print('无法读取已保存的登录，需要重新验证。', file=sys.stderr)
    if stored:
        if stored.get('client') == client and stored.get('tenant') == tenant:
            try:
                result = request(base + 'token', {'grant_type': 'refresh_token', 'client_id': client, 'refresh_token': stored['refresh_token'], 'scope': ' '.join(scopes)})
                save_token(result, client, tenant)
                return result['access_token']
            except ApiError as exc:
                if exc.payload.get('error') not in ('invalid_grant', 'interaction_required'):
                    raise
                print('已保存的登录需要重新验证。', file=sys.stderr)
    device = request(base + 'devicecode', {'client_id': client, 'scope': ' '.join(scopes)})
    print(device['message'], file=sys.stderr, flush=True)
    deadline = time.monotonic() + device['expires_in']
    interval = device.get('interval', 5)
    while time.monotonic() < deadline:
        time.sleep(interval)
        try:
            result = request(base + 'token', {'grant_type': 'urn:ietf:params:oauth:grant-type:device_code', 'client_id': client, 'device_code': device['device_code']})
            save_token(result, client, tenant)
            return result['access_token']
        except ApiError as exc:
            error = exc.payload.get('error')
            if error == 'slow_down':
                interval += 5
            elif error != 'authorization_pending':
                raise
    raise ValueError('设备代码已过期，请重试。')


def main():
    parser = argparse.ArgumentParser(description='Microsoft Teams Graph 命令行工具')
    sub = parser.add_subparsers(dest='command', required=True)
    users = sub.add_parser('users', help='按名称或邮箱查找用户')
    users.add_argument('--query', required=True)
    sub.add_parser('login', help='登录或验证已保存的登录')
    sub.add_parser('chats', help='列出已加入的聊天')
    send = sub.add_parser('send', help='发送单聊或群聊消息')
    target = send.add_mutually_exclusive_group(required=True)
    target.add_argument('--user-id', help='新建或取得与该用户的一对一聊天')
    target.add_argument('--chat-id', help='现有单聊或群聊的 ID')
    send.add_argument('--message', required=True)
    args = parser.parse_args()
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
