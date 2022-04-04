import threading
import asyncio
import time
import flask
import telethon.tl.types
from flask import Flask, request
from flask import render_template
from telethon.sync import TelegramClient
from telethon.tl import functions
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.types import InputPeerEmpty, InputMessagesFilterEmpty
import database
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = 'parse'
client = TelegramClient('anon', api_id=15279225, api_hash='78667b8dc90a39ecc1060b1c2d2a42cd')
loop = asyncio.get_event_loop()
db = database.database()
socketio = SocketIO(app, async_mode='threading')


@app.route("/")
def home():
    name = loop.run_until_complete(getme()).first_name
    _data = db.get_parsed_chats()
    data = []
    for i in _data:
        title = i[1]
        if len(i[1]) > 30:
            title = str(i[1][0:30] + '...')
        data.append([i[0], title, i[2], i[3], i[4]])
    return render_template('index.html', name=name, data=data)


async def getme():
    return await client.get_me()


async def search_chats(query):
    result = await client(functions.contacts.SearchRequest(
        q=query,
        limit=100
    ))
    chats = 0
    for chat in result.chats:
        if chat.megagroup or chat.gigagroup:
            chats += 1
            db.add_parsed_chat(chat.id, chat.title, chat.access_hash, chat.username, chat.participants_count)
            title = chat.title
            if len(title) > 30:
                title = title[0:30] + '...'
            socketio.emit('parsed_chat', {'id': chat.id, 'title': title, 'access_hash': chat.access_hash,
                                          'username': chat.username, 'participants_count': chat.participants_count})
            socketio.emit('found_chats', {'count': chats})


@app.route("/delete_record", methods=["POST"])
def del_record():
    res = request.form.get('delet')
    db.delete_parsed_chat(res)
    return 'ok'


@app.route("/search", methods=["POST"])
def search():
    query = request.form.get('query')
    loop.run_until_complete(search_chats(query))
    return 'ok'


async def getentity(query):
    asyncio.set_event_loop(asyncio.new_event_loop())
    print(1)
    re = await client.get_entity(telethon.tl.types.InputPeerChannel(int(query[0]), int(query[2])))
    print(2)
    re = client.iter_participants(re, aggressive=True)
    async for r in re:
        time.sleep(0.05)
        db.add_parsed_user(r, query)
    return re


def parse_users(query):
    print(3)

    asyncio.run(getentity(db.get_channel_by_id(query)))
    print(4)

    return


@app.route("/parse", methods=["POST"])
def parse():
    query = request.form.get('id')
    threading.Thread(target=lambda: parse_users(query)).start()
    return 'ok'


if __name__ == '__main__':
    client.start()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8888, debug=True, use_reloader=False)).start()