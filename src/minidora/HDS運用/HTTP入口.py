"""HDS運用のローカルHTTP入口。画面と読取APIは既存製品を再利用する。"""
from __future__ import annotations
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse
from ..製品版.api import APIHandler, _json
from .契約 import JSONを読む, 名前を検査


class HDS運用HTTPハンドラ(APIHandler):
    def do_GET(self):
        if urlparse(self.path).path == '/health':
            if not self._入口許可():
                return
            from .契約 import 運用版
            return _json(self, 200, {'ok': True, 'service': 'HDS-MINIDORA',
                '実行方式': 'HDS-FIRST', '版': 運用版})
        return super().do_GET()

    def do_POST(self):
        if not self._入口許可():
            return
        if urlparse(self.path).path != '/api/chat':
            return _json(self, 404, {'error': 'not_found'})
        try:
            長さ = int(self.headers.get('Content-Length', '0'))
            if not 0 < 長さ <= self.max_body:
                return _json(self, 413, {'error': 'invalid_body_size'})
            値 = JSONを読む(self.rfile.read(長さ).decode('utf-8'), 上限=self.max_body)
            if type(値) is not dict or not {'message'} <= set(値) <= {'message', 'session_id'}:
                raise ValueError('messageとsession_id以外は受け付けない')
            if type(値['message']) is not str or not 値['message'].strip():
                raise ValueError('空でない文字列messageが必要')
            名 = 名前を検査(値.get('session_id', 'default'))
            結果 = self.app.応答(値['message'], セッションID=名)
        except (ValueError, TypeError, UnicodeError) as exc:
            return _json(self, 400, {'error': str(exc)})
        except RuntimeError as exc:
            return _json(self, 409, {'error': str(exc)})
        except OSError:
            return _json(self, 500, {'error': '監査又は保存に失敗。未実行とはみなさず状態を確認してください'})
        return _json(self, 200, 結果.辞書化())


def サーバを構成(製品, *, ポート=8080):
    if type(ポート) is not int or not 0 <= ポート <= 65535:
        raise ValueError('ポート範囲不正')
    サーバ = ThreadingHTTPServer(('127.0.0.1', ポート), HDS運用HTTPハンドラ)
    サーバ.app = 製品
    サーバ.同一生成元限定 = True
    return サーバ
