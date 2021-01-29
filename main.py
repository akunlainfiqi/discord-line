import os
from typing import Text
import wsgiref.simple_server
from argparse import ArgumentParser
from dhooks import Webhook, Embed

from builtins import bytes
from linebot import (
    LineBotApi, WebhookParser
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    TextMessage, SourceUser, SourceGroup, TextSendMessage,
    Sender, MessageEvent
)
from linebot.utils import PY3

#ini diisi semua
line_bot_api = LineBotApi('channel_access_token') #line
parser = WebhookParser('channel_secret') #line
dev = Webhook('link webhook discord tes') #discord
hook = Webhook('webhook discord rilis') #discord

def application(environ, start_response):
    # check request path
    if environ['PATH_INFO'] != '/callback':
        start_response('404 Not Found', [])
        return create_body('Not Found')

    # check request method
    if environ['REQUEST_METHOD'] != 'POST':
        start_response('405 Method Not Allowed', [])
        return create_body('Method Not Allowed')

    # get X-Line-Signature header value
    signature = environ['HTTP_X_LINE_SIGNATURE']

    # get request body as text
    wsgi_input = environ['wsgi.input']
    content_length = int(environ['CONTENT_LENGTH'])
    body = wsgi_input.read(content_length).decode('utf-8')

    # parse webhook body
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        start_response('400 Bad Request', [])
        return create_body('Bad Request')

    # if event is MessageEvent and message is TextMessage, then echo text
    for event in events:
        if not isinstance(event,MessageEvent):
            continue
        if isinstance(event.source, SourceUser):
            line_bot_api.reply_message(
                event.reply_token,TextSendMessage(text="Maaf salah sambung.")
            )
            dev.send("tipe pesan = {}\npengirim = {}\nid pengirim={}\npesan={}".format(event.message.type,event.source.type,event.source.user_id,event.message.text))
        if isinstance(event.source, SourceGroup):
            if isinstance(event.message, TextMessage):
                dev.send(event.message.text)
                hook.send(event.message.text)
            else:
                dev.send("\nfiqi tampan\n")
            dev.send("tipe pesan = {}\npengirim = {}\nid pengirim={}\ngrup={}\nid grup={}\nPesan={}".format(event.message.type,event.source.type,event.source.user_id,event.source.sender_id,event.source.sender_id,event.message.text))

    start_response('200 OK', [])
    return create_body('OK')


def create_body(text):
    if PY3:
        return [bytes(text, 'utf-8')]
    else:
        return text

port = int(os.environ.get("PORT", 33507))

if __name__ == '__main__':
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', type=int, default=8000, help='port')
    options = arg_parser.parse_args()

    httpd = wsgiref.simple_server.make_server('0.0.0.0', port, application)
    httpd.serve_forever()
    