# -*- coding: utf-8 -*-

#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

from __future__ import unicode_literals

import errno
import os
from linebot.models.sources import SourceUser
import requests
import sys
import tempfile

from argparse import ArgumentParser

from dhooks import Webhook, File, Embed

from flask import Flask, request, abort, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix

from io import BytesIO

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    LineBotApiError, InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    SourceGroup, PostbackEvent, StickerMessage, 
    LocationMessage, ImageMessage, VideoMessage, 
    AudioMessage, FileMessage, UnfollowEvent, 
    FollowEvent, JoinEvent, LeaveEvent, 
    BeaconEvent, MemberJoinedEvent, MemberLeftEvent
)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1, x_proto=1)

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
webhook_link = os.getenv('DISCORD_WEBHOOK', None)
webhook_log_link = os.getenv('DISCORD_WEBHOOK_LOG', None)

if (channel_secret is None or channel_access_token is None or webhook_link is None):
    print('Environment variable is missing!')
    sys.exit(1)

if webhook_log_link is None :
    print('fakyu')

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)
hook = Webhook(webhook_link)
log = Webhook(webhook_log_link)

static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

# fungsi mengirim log ke webhook discord
def log_event_to_discord(event):
    if isinstance(event, MessageEvent):
        userId = event.source.user_id
        messageId = event.message.id
        contentType = event.message.type

        userdata = line_bot_api.get_profile(userId).as_json_dict()

        sendEmbed = Embed(timestamp='now')

        if isinstance(event.source, SourceGroup):
            groupId = event.source.group_id
            groupdata = line_bot_api.get_group_summary(groupId).as_json_dict()

            sendEmbed.set_author(
                name = userdata['displayName'] + " @ " + groupdata['groupName']
            )
            sendEmbed.color = 0x0FF00
            sendEmbed.add_field(name='Grup ID', value = groupId)
        else :
            sendEmbed.set_author(
                name = userdata['displayName']
            )
            sendEmbed.color = 0x0FFFF

        if contentType == 'text':
            sendEmbed.description = event.message.text
        elif contentType == 'location':
            sendEmbed.description = event.message.title
            sendEmbed.add_field('latitude',event.message.latitude)
            sendEmbed.add_field('longitude',event.message.longitude,False)
        elif contentType == 'sticker':
            sendEmbed.description = event.message.keywords[0]
            sendEmbed.add_field('package id',event.message.package_id)
            sendEmbed.add_field('sticker_id',event.message.sticker_id)
            sendEmbed.add_field('keywords',event.message.keywords)
        else:
            sendEmbed.description = event.message.type
        


        sendEmbed.set_thumbnail(userdata['pictureUrl'])
        sendEmbed.add_field(name='ID User', value=userId)
        sendEmbed.add_field(name="Content Type", value=contentType)
        sendEmbed.add_field(name="Message ID", value=messageId)
        sendEmbed.set_footer(text=event.source.type)

        log.send(embed = sendEmbed)


# function for create tmp dir for download content
def make_static_tmp_dir():
    try:
        os.makedirs(static_tmp_path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(static_tmp_path):
            pass
        else:
            raise


# fungsi untuk membandingkan id grup yang di cek dengan gitulah
watchedgroupid = 'C88526b654cefff9a2fe7c041df20b066'
def isFromWatchedLineGroup(event):
    if isinstance(event.source,SourceGroup):
        if event.source.group_id == watchedgroupid:
            return True
        else:  
            return False
    else:  
        return False


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except LineBotApiError as e:
        print("Got exception from LINE Messaging API: %s\n" % e.message)
        embedLog = Embed(
            color = 0xff0000,
            timestamp = 'now'
        )
        embedLog.set_author(name ="Got exception from LINE Messaging API: %s\n" % e.message)
        for m in e.error.details:
            print("  %s: %s" % (m.property, m.message))
            embedLog.description = '%s: %s" % (m.property, m.message)'
        print("\n")
        log.send(embed=embedLog)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    if isFromWatchedLineGroup(event):
        hook.send(event.message.text)
    if not isinstance(event.source, SourceGroup):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text = event.message.text))
    log_event_to_discord(event)
            


@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    if isFromWatchedLineGroup(event):
        hook.send(event.message.address)
    log_event_to_discord(event)



@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    if isFromWatchedLineGroup(event):
        hook.send(event.message.keywords[0])
    log_event_to_discord(event)


# Other Message Type
@handler.add(MessageEvent, message=(ImageMessage, VideoMessage, AudioMessage))
def handle_content_message(event):
    if isinstance(event.message, ImageMessage):
        ext = 'jpg'
    elif isinstance(event.message, VideoMessage):
        ext = 'mp4'
    elif isinstance(event.message, AudioMessage):
        ext = 'm4a'
    else:
        return

    message_content = line_bot_api.get_message_content(event.message.id)
    with tempfile.NamedTemporaryFile(dir=static_tmp_path, prefix=ext + '-', delete=False) as tf:
        for chunk in message_content.iter_content():
            tf.write(chunk)
        tempfile_path = tf.name

    dist_path = tempfile_path + '.' + ext
    dist_name = os.path.basename(dist_path)
    os.rename(tempfile_path, dist_path)

    link = request.host_url + os.path.join('static', 'tmp', dist_name)
    response = requests.get(link)
    file = File(BytesIO(response.content), name=dist_name)

    hook.send(file=file)
    log.send(file=file)
    log_event_to_discord(event)


@handler.add(MessageEvent, message=FileMessage)
def handle_file_message(event):
    message_content = line_bot_api.get_message_content(event.message.id)
    with tempfile.NamedTemporaryFile(dir=static_tmp_path, prefix='file-', delete=False) as tf:
        for chunk in message_content.iter_content():
            tf.write(chunk)
        tempfile_path = tf.name

    dist_path = tempfile_path + '-' + event.message.file_name
    dist_name = os.path.basename(dist_path)
    os.rename(tempfile_path, dist_path)

    link = request.host_url + os.path.join('static', 'tmp', dist_name)
    response = requests.get(link)
    file = File(BytesIO(response.content), name=event.message.file_name)
    
    hook.send(file=file)
    log.send(file=file)
    log_event_to_discord(event)


@handler.add(FollowEvent)
def handle_follow(event):
    log_event_to_discord(event)


@handler.add(UnfollowEvent)
def handle_unfollow(event):
    log_event_to_discord(event)


@handler.add(JoinEvent)
def handle_join(event):
    log_event_to_discord(event)


@handler.add(LeaveEvent)
def handle_leave(event):
    log_event_to_discord(event)


@handler.add(PostbackEvent)
def handle_postback(event):
    log_event_to_discord(event)


@handler.add(BeaconEvent)
def handle_beacon(event):
    log_event_to_discord(event)


@handler.add(MemberJoinedEvent)
def handle_member_joined(event):
    log_event_to_discord(event)


@handler.add(MemberLeftEvent)
def handle_member_left(event):
    log_event_to_discord(event)


@app.route('/static/<path:path>')
def send_static_content(path):
    return send_from_directory('static', path)

port = int(os.environ.get("PORT", 33507))

if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', type=int, default=8000, help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    # create tmp dir for download content
    make_static_tmp_dir()

    app.run(host='0.0.0.0',debug=options.debug, port=port)