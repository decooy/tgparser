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
import nest_asyncio
import gevent.monkey
import logging
import eventlet

parsing_now = False

nest_asyncio.apply()

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


app = Flask(__name__)
app.secret_key = 'parse'
client = TelegramClient('anon', api_id=15279225, api_hash='78667b8dc90a39ecc1060b1c2d2a42cd')
loop = asyncio.get_event_loop()
db = database.database()

socketio = SocketIO(app, async_mode='eventlet')
eventlet.monkey_patch()


def show_message(title, text, status):
    if status:
        status = 'success'
    else:
        status = 'error'
    socketio.emit('show_message', {'title': title, 'text': text, 'status': status})


@app.route("/spamer/")
def spmer():
    db2 = database.database()
    accounts = db2.get_accounts_count()
    chats = db2.get_chats_count()
    me = loop.run_until_complete(getme())
    me = [me.first_name, ('@' + str(me.username)).replace('@None', ''), '+' + str(me.phone)]
    return render_template('spamer.html', count=accounts, chatcount=chats, me=me)


@app.route("/")
def home():
    try:
        name = loop.run_until_complete(getme()).first_name
    except:
        name = 'ОШИБКА АККАУНТА'
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
    global parsing_now
    if parsing_now:
        show_message('Парсер занят...', 'Необходимо дождаться конца предыдущей операции.', False)
        return
    parsing_now = True
    show_message('Парсим...', 'Это может занять некоторое время.', True)
    db2 = database.database()
    result = await client(functions.contacts.SearchRequest(
        q=query,
        limit=100
    ))
    chats = 0
    for chat in result.chats:
        if chat.megagroup or chat.gigagroup:
            chats += 1
            db2.add_parsed_chat(chat.id, chat.title, chat.access_hash, chat.username, chat.participants_count)
            title = chat.title
            if len(title) > 30:
                title = title[0:30] + '...'
            socketio.emit('parsed_chat', {'id': chat.id, 'title': title, 'access_hash': chat.access_hash,
                                          'username': chat.username, 'participants_count': chat.participants_count})
            socketio.emit('found_chats', {'count': chats})
    if chats == 0:
        socketio.emit('found_chats', {'count': chats})
    parsing_now = False


@app.route("/delete_record", methods=["POST"])
def del_record():
    db2 = database.database()
    res = request.form.get('delet')
    db2.delete_parsed_chat(res)
    return 'ok'


@app.route("/search", methods=["POST"])
def search():
    query = request.form.get('query')
    loop.run_until_complete(search_chats(query))
    return 'ok'


async def getentity(query):
    global parsing_now
    if parsing_now:
        show_message('Парсер занят...', 'Необходимо дождаться конца предыдущей операции.', False)
        return
    parsing_now = True
    show_message('Парсим...', 'Это может занять некоторое время.', True)
    db2 = database.database()
    re = await client.get_entity(telethon.tl.types.InputPeerChannel(int(query[0]), int(query[2])))
    users = 0
    result = client.iter_participants(re, aggressive=True)
    try:
        async for r in result:
            time.sleep(0.05)
            users += 1
            db2.add_parsed_user(r, query)
            socketio.emit('found_users', {'count': users})
        show_message('Готово.', 'Парсер окончил работу. Собрано аккаунтов: ' + str(users), True)
    except:
        show_message('Ошибка.', 'Парсер окончил работу с ошибкой флуда (FloodWaitError). Повторите попытку через пару мин.'
                                'Удалось собрать аккаунтов: ' + str(users), False)
    parsing_now = False

    return re


def parse_users(query):
    db2 = database.database()
    loop.run_until_complete(getentity(db2.get_channel_by_id(query)))
    return


@app.route("/parse", methods=["POST"])
def parse():
    parsing_now = True
    query = request.form.get('id')
    threading.Thread(target=lambda: parse_users(query)).start()
    return 'ok'


if __name__ == '__main__':
    client.start()
    socketio.run(app, host='0.0.0.0', port=8888)