import threading
import asyncio
import time
import flask
import telethon.tl.types
from flask import Flask, request
from flask import render_template
from telethon import events
from telethon.sync import TelegramClient
from telethon.tl import functions
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.messages import SearchGlobalRequest, AddChatUserRequest
from telethon.tl.types import InputPeerEmpty, InputMessagesFilterEmpty
import database
from flask_socketio import SocketIO, emit
import nest_asyncio
import gevent.monkey
import logging
import eventlet
from smsactivateru import Sms, SmsTypes, SmsService, GetBalance, GetFreeSlots, GetNumber

wrapper = Sms('cA0945343eb0cc37e2327d14d3d38581')
needstop = False
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
        user = loop.run_until_complete(getme())
        name = user.first_name
        username = user.username
        phone = user.phone
    except:
        name = 'Аккаунт отсутствует'
        username = ''
        phone = ''
    _data = db2.get_parsed_chats()
    data = []
    for i in _data:
        title = i[1]
        if len(i[1]) > 30:
            title = str(i[1][0:30] + '...')
        data.append([i[0], title, i[2], i[3], i[4]])
    accounts = db2.get_accounts_count()
    chats = db2.get_chats_count()
    if name == 'Аккаунт отсутствует':
        me = [name, username, phone]
    else:
        me = [name, ('@' + str(username)).replace('@None', ''), '+' + str(phone)]
    return render_template('index.html', name=name, data=data, count=accounts, chatcount=chats, me=me)


async def getme():
    if await client.is_user_authorized():
        return await client.get_me()
    else:
        return None


async def search_chats(query):
    global needstop
    if not await client.is_user_authorized():
        show_message('Отсутствует аккаунт.', 'Необходимо добавить активный аккаунт.', False)
        return
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
        if needstop:
            needstop = False
            show_message('Готово.', 'Парсинг остановлен', True)
            break
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
    global needstop
    if not await client.is_user_authorized():
        show_message('Отсутствует аккаунт.', 'Необходимо добавить активный аккаунт.', False)
        return
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
        print(e)
        if str(e).find('pass the right types') >= 0:
            show_message('Ошибка',
                         'Похоже, эта база парсилась с другого аккаунта. Необходимо удалить и спарсить заново.', False)
            parsing_now = False
            return
    users = 0
    result = client.iter_participants(re, aggressive=True)
    try:
        async for r in result:
            if needstop:
                needstop = False
                break
            time.sleep(0.05)
            users += 1
            db2.add_parsed_user(r, query)
            socketio.emit('found_users', {'count': users})
            socketio.emit('total_users', {'count': db2.get_accounts_count()})
        show_message('Готово.', 'Парсер окончил работу. Собрано аккаунтов: ' + str(users), True)
    except:
        show_message('Ошибка.',
                     'Парсер окончил работу с ошибкой флуда (FloodWaitError). Повторите попытку через пару мин.'
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
    global needstop
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
            if needstop:
                show_message('Готово.', 'Спаммер остановлен', True)
                needstop = False
                break
            entity = telethon.tl.types.InputPeerUser(int(user[0]), int(user[1]))
            client.action(entity=entity, action='typing')
            time.sleep(0.5)
            await client.send_message(entity=entity, message=query)
            if deletebox:
                db.delete_user(int(user[0]))
                socketio.emit('total_users', {'count': db2.get_accounts_count()})
        except Exception as e:
            if str(e).find('many requests') >= 0:
                show_message('Ошибка',
                             'Слишком много запросов телеграм. Попробуйте через несколько минут.',
                             False)
                parsing_now = False
                break
            if str(e).find("invalid Peer") >= 0:
                show_message('Ошибка',
                             'Похоже, эта база парсилась с другого аккаунта. Необходимо удалить и спарсить заново.',
                             False)
                parsing_now = False
                break
            print(e)
            send_notification('Произошла ошибка отправки. Повтор через 5 минут.', False)
            for i in range(0, 300):
                time.sleep(1)
                if needstop:
                    show_message('Готово.', 'Спаммер остановлен', True)
                    needstop = False
                    return
        sended += 1
        socketio.emit('updateprogress',
                      {'percent': int(sended / len(users) * 100), 'sended': sended, 'total': len(users)})
        time.sleep(int(delay))
    parsing_now = False


def spam(query, delay, deletebox):
    loop.run_until_complete(dospam(query, delay, deletebox))
    return


@client.on(events.NewMessage(incoming=True))
async def handlerw(event):
    print(event)


async def doinvite(link, delay, deletebox, channel):
    global needstop
    global parsing_now
    if parsing_now:
        show_message('Парсер занят...', 'Необходимо дождаться конца предыдущей операции.', False)
        return
    parsing_now = True
    db2 = database.database()
    channel = await client.get_entity(channel)
    socketio.emit('updateprogresstext', {'text': 'Инвайтинг в ' + str(link)})
    users = db2.get_all_accounts()
    sended = 0
    for user in users:
        try:
            if needstop:
                show_message('Готово.', 'Инвайтинг остановлен', True)
                needstop = False
                break
            await client(InviteToChannelRequest(channel=telethon.tl.types.InputChannel(channel.id, channel.access_hash),
                                                users=[telethon.tl.types.InputUser(int(user[0]), int(user[1]))]))
            if deletebox:
                db.delete_user(int(user[0]))
                socketio.emit('total_users', {'count': db2.get_accounts_count()})
        except Exception as e:
            if str(e).find('privacy settings') >= 0:
                sended += 1
                socketio.emit('updateprogress',
                              {'percent': int(sended / len(users) * 100), 'sended': sended, 'total': len(users)})
                time.sleep(int(delay))
                continue
            print(e)
            send_notification('Произошла ошибка инвайта. Повтор через 5 минут.', False)
            time.sleep(300)
            continue
        sended += 1
        socketio.emit('updateprogress',
                      {'percent': int(sended / len(users) * 100), 'sended': sended, 'total': len(users)})
        time.sleep(int(delay))
    parsing_now = False


def invite(link, delay, deletebox, channel):
    loop.run_until_complete(doinvite(link, delay, deletebox, channel))
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


@app.route("/clear", methods=["POST"])
def clear():
    global parsing_now
    if parsing_now:
        show_message('Ошибка.', 'Необходимо дождаться окончания предыдущей операции.', True)
        return 'not ok'
    parsing_now = True
    database.database().clear_base()
    show_message('Готово.', 'База была очищена.', True)
    parsing_now = False
    socketio.emit('clear_all')
    return 'ok'


def fuck_yeah(code):
    show_message('Telegram', 'СМС получено, регистрация может занять несколько минут.', True)
    global lastphone
    while True:
        try:
            client.start(phone=str(lastphone), code_callback=lambda: code, first_name='Lorem', last_name='Ipsum')
        except Exception as e:
            print(e)
            if str(e).find('wait of') >= 0:
                time.sleep(60)
                continue
            show_message('Ошибка', 'Произошла какая-то ошибка. Детали записаны в лог.', False)
            return 'ok'
        if client.is_user_authorized():
            socketio.emit('reboot_page')
        else:
            show_message('Ошибка', 'Не удалось авторизоваться.', False)
        return 'ok'


lastphone = 0


@app.route("/autoreg", methods=["POST"])
def areg():
    global lastphone
    show_message('Ожидание...:', 'Регистрация аккаунта...', True)
    try:
        activation = GetNumber(
            service=SmsService().Telegram,
            country=SmsTypes.Country.ID,
            operator=SmsTypes.Operator.any
        ).request(wrapper)
    except Exception as e:
        show_message('SMS-ACTIVATE:', e.args[0], False)
        return 'false'
    lastphone = activation.phone_number
    try:
        client.send_code_request(phone=str(activation.phone_number), force_sms=True)
    except telethon.errors.PhoneNumberBannedError:
        show_message('Telegram', 'Этот номер заблокирован телеграмом для регистрации. Отмена регистрации.', 'False')
        return 'ok'
    try:
        activation.was_sent()
        activation.wait_code(callback=fuck_yeah, wrapper=wrapper)
    except Exception as e:
        show_message('SMS-REG', e, False)
    return 'ok'


first_reg = True


async def logoutw():
    try:
        await client.log_out()
    except:
        pass
    return


def logout_loop():
    loop.run_until_complete(logoutw())


@app.route("/logout", methods=["POST"])
def logout():
    try:
        threading.Thread(target=logout_loop).start()
    except:
        pass
    socketio.emit('reboot_page')
    return 'ok'


@app.route("/reg", methods=["POST"])
def reg():
    global first_reg
    client.connect()
    phone = request.form.get('phone')
    code = request.form.get('code')
    if first_reg:
        try:
            client.send_code_request(phone=phone, force_sms=False)
        except telethon.errors.FloodWaitError:
            show_message('Anti fraud', 'Необходимо подождать перед отправкой смс.', False)
            return 'ok'
        socketio.emit('show_code')
        first_reg = False
        return 'ok'
    try:
        client.start(phone=phone, code_callback=lambda: code, first_name='Lorem', last_name='Ipsum')
    except:
        show_message('Ошибка', 'Произошла какая-то ошибка. Детали записаны в лог.', False)
        return 'ok'
    if client.is_user_authorized():
        socketio.emit('reboot_page')
        first_reg = True
    else:
        show_message('Ошибка', 'Не удалось авторизоваться.', False)
        first_reg = True
    return 'ok'


@app.route("/addchat", methods=["POST"])
def adchat():
    db2 = database.database()
    global parsing_now
    if parsing_now:
        show_message('Ошибка.', 'Необходимо дождаться окончания предыдущей операции.', True)
        return 'not ok'
    parsing_now = True
    query = request.form.get('query')
    chat = client.get_entity(query)
    if type(chat) is not telethon.tl.types.Channel:
        show_message('Ошибка.', 'Адрес не является чатом.', True)
        parsing_now = False
        return 'not ok'
    db2.add_parsed_chat(chat.id, chat.title, chat.access_hash, chat.username, chat.participants_count)
    title = chat.title
    socketio.emit('parsed_chat', {'id': chat.id, 'title': title, 'access_hash': chat.access_hash,
                                      'username': chat.username, 'participants_count': chat.participants_count})
    socketio.emit('total_chats', {'count': db2.get_chats_count()})
    parsing_now = False
    return 'ok'


@app.route("/invite", methods=["POST"])
def inviteqw():
    db2 = database.database()
    link = request.form.get('invitelink')
    try:
        channel = client.get_entity(link)
    except Exception as e:
        print(e)
        show_message('Ошибка', 'Указанный адрес не является чатом/каналом', False)
        return 'not ok'
    if type(channel) is not telethon.tl.types.Channel:
        show_message('Ошибка', 'Указанный адрес не является чатом/каналом', False)
        return 'not ok'
    deletebox = request.form.get('deletebox')
    if type(deletebox) is str:
        deletebox = True
    else:
        deletebox = False
    delay = int(request.form.get('delay'))
    threading.Thread(target=lambda: invite(link, delay, deletebox, link)).start()
    return 'ok'


if __name__ == '__main__':
    client.connect()
    if client.is_user_authorized():
        client.start()
    socketio.run(app, host='0.0.0.0', port=8888)
