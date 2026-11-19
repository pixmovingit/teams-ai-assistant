import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('teams', Path(__file__).parents[1] / 'scripts' / 'teams.py')
teams = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teams)


class SendTests(unittest.TestCase):
    def run_send(self, args):
        calls = []

        def fake_request(url, data=None, token=None):
            calls.append((url, data))
            if url.endswith('/me?$select=id'):
                return {'id': '00000000-0000-0000-0000-000000000001'}
            if url.endswith('/chats'):
                return {'id': 'chat:id'}
            return {'id': 'message-id'}

        with patch.object(sys, 'argv', ['teams.py', 'send', *args]), patch.object(teams, 'login', return_value='token'), patch.object(teams, 'request', side_effect=fake_request), contextlib.redirect_stdout(io.StringIO()):
            teams.main()
        return calls

    def test_existing_group_receives_ai_label(self):
        calls = self.run_send(['--chat-id', '19:group/id', '--message', '你好'])
        self.assertEqual(len(calls), 1)
        self.assertIn('19%3Agroup%2Fid/messages', calls[0][0])
        self.assertEqual(calls[0][1]['body']['content'], '🤖 AI 助手代发\n你好')

    def test_direct_chat_creation_and_send(self):
        calls = self.run_send(['--user-id', '00000000-0000-0000-0000-000000000002', '--message', '你好'])
        self.assertEqual(calls[1][1]['chatType'], 'oneOnOne')
        self.assertIn("users('00000000-0000-0000-0000-000000000002')", calls[1][1]['members'][1]['user@odata.bind'])
        self.assertTrue(calls[2][1]['body']['content'].startswith(teams.AI_LABEL))

    @unittest.skipUnless(sys.platform == 'win32', 'Windows DPAPI required')
    def test_cache_encryption_round_trip(self):
        data = b'local test data'
        self.assertEqual(teams.protect(teams.protect(data), decrypt=True), data)


if __name__ == '__main__':
    unittest.main()
