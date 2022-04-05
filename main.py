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
    db2 = database.database()
    try:
        name = loop.run_until_complete(getme()).first_name
    except:
        name = 'ОШИБКА АККАУНТА'
    _data = db2.get_parsed_chats()
    data = []
    for i in _data:
        title = i[1]
        if len(i[1]) > 30:
            title = str(i[1][0:30] + '...')
        data.append([i[0], title, i[2], i[3], i[4]])
    accounts = db2.get_accounts_count()
    chats = db2.get_chats_count()
    me = loop.run_until_complete(getme())
    me = [me.first_name, ('@' + str(me.username)).replace('@None', ''), '+' + str(me.phone)]
    return render_template('index.html', name=name, data=data, count=accounts, chatcount=chats, me=me)


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
    socketio.emit('total_chats', {'count': db2.get_chats_count()})
    parsing_now = False


@app.route("/delete_record", methods=["POST"])
def del_record():
    db2 = database.database()
    res = request.form.get('delet')
    db2.delete_parsed_chat(res)
    socketio.emit('total_chats', {'count': db2.get_chats_count()})
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
    try:
        re = await client.get_entity(telethon.tl.types.InputPeerChannel(int(query[0]), int(query[2])))
    except Exception as e:
        if str(e).find('pass the right types'):
            show_message('Ошибка',
                         'Похоже, эта база парсилась с другого аккаунта. Необходимо удалить и спарсить заново.', False)
            parsing_now = False
            return
    users = 0
    result = client.iter_participants(re, aggressive=True)
    try:
        async for r in result:
            time.sleep(0.05)
            users += 1
            db2.add_parsed_user(r, query)
            socketio.emit('found_users', {'count': users})
            socketio.emit('total_users', {'count': db2.get_accounts_count()})
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
    query = request.form.get('id')
    threading.Thread(target=lambda: parse_users(query)).start()
    return 'ok'


async def dospam(query, delay, deletebox):
    global parsing_now
    if parsing_now:
        show_message('Парсер занят...', 'Необходимо дождаться конца предыдущей операции.', False)
        return
    parsing_now = True
    db2 = database.database()
    if len(query) > 40:
        qtext = str(query[0:40]) + '...'
    else:
        qtext = query
    socketio.emit('updateprogresstext', {'text': qtext})

    users = db2.get_all_accounts()
    sended = 1
    for user in users:
        try:
            entity = telethon.tl.types.InputPeerUser(int(user[0]), int(user[1]))
            client.action(entity=entity, action='typing')
            time.sleep(0.5)
            await client.send_message(entity=entity, message=query)
            if deletebox:
                db.delete_user(int(user[0]))
                socketio.emit('total_users', {'count': db2.get_accounts_count()})
        except Exception as e:
            if str(e).find("invalid Peer"):
                show_message('Ошибка', 'Похоже, эта база парсилась с другого аккаунта. Необходимо удалить и спарсить заново.', False)
                parsing_now = False

                break
            send_notification('Произошла ошибка отправки. Повтор через 5 минут.', False)
            time.sleep(300)
        sended += 1
        socketio.emit('updateprogress', {'percent': int(sended/len(users)*100), 'sended': sended, 'total': len(users)})
        time.sleep(int(delay))
    parsing_now = False


def spam(query, delay, deletebox):
    loop.run_until_complete(dospam(query, delay, deletebox))
    return


def send_notification(text, positive):
    if positive:
        socketio.emit('sendnotyfsuccess', {'text': text})
    else:
        socketio.emit('sendnotyferror', {'text': text})


@app.route("/spam", methods=["POST"])
def spamqw():
    db2 = database.database()
    query = request.form.get('spamtext')
    delay = request.form.get('delay')
    deletebox = request.form.get('deletebox')
    if type(deletebox) is str:
        deletebox = True
    else:
        deletebox = False
    if db2.get_accounts_count() == 0:
        show_message('Ошибка', 'Для начала необходимо спарсить аккаунты (выше)', False)
        return 'ok'
    threading.Thread(target=lambda: spam(query, delay, deletebox)).start()
    return 'ok'


@app.route("/invite", methods=["POST"])
def inviteqw():
    print(request.form.get('deletebox'))
    print(request.form.get('invitelink'))
    print(request.form.get('delay'))
    return 'ok'

if __name__ == '__main__':
    client.start()
    socketio.run(app, host='0.0.0.0', port=8888)