import os
import sqlite3
from flask import Flask
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'h_chat_secret_key_999'
socketio = SocketIO(app, cors_allowed_origins="*")

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('h_chat.db')
    cur = conn.cursor()
    # Таблица пользователей
    cur.execute('''CREATE TABLE IF NOT EXISTS users 
                   (username TEXT PRIMARY KEY, password TEXT)''')
    # Таблица сообщений
    cur.execute('''CREATE TABLE IF NOT EXISTS messages 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    sender TEXT, receiver TEXT, msg TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# --- ОБРАБОТКА АВТОРИЗАЦИИ ---

@socketio.on('register')
def handle_register(data):
    user = data.get('user')
    pw = data.get('pw')
    conn = sqlite3.connect('h_chat.db')
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO users (username, password) VALUES (?, ?)', (user, pw))
        conn.commit()
        emit('auth_status', {'status': 'success', 'msg': 'Регистрация успешна! Теперь войдите.'})
        print(f"[REG] New user: {user}")
    except sqlite3.IntegrityError:
        emit('auth_status', {'status': 'error', 'msg': 'Этот ник уже занят!'})
    finally:
        conn.close()

@socketio.on('login')
def handle_login(data):
    user = data.get('user')
    pw = data.get('pw')
    conn = sqlite3.connect('h_chat.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE username=? AND password=?', (user, pw))
    result = cur.fetchone()
    if result:
        emit('auth_status', {'status': 'success', 'msg': f'Добро пожаловать, {user}!', 'user': user})
        print(f"[LOGIN] User {user} connected.")
    else:
        emit('auth_status', {'status': 'error', 'msg': 'Неверный ник или пароль!'})
    conn.close()

# --- ОБРАБОТКА СООБЩЕНИЙ И ИСТОРИИ ---

@socketio.on('get_history')
def handle_history(data):
    me = data.get('me')
    to = data.get('to')
    conn = sqlite3.connect('h_chat.db')
    cur = conn.cursor()
    # Выбираем сообщения между двумя конкретными людьми
    cur.execute('''SELECT sender, msg FROM messages 
                   WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)
                   ORDER BY timestamp ASC''', (me, to, to, me))
    history = cur.fetchall()
    emit('history_res', {'history': history})
    conn.close()

@socketio.on('send_dm')
def handle_dm(data):
    sender = data.get('from')
    receiver = data.get('to')
    msg = data.get('msg')
    
    # Сохраняем в базу
    conn = sqlite3.connect('h_chat.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO messages (sender, receiver, msg) VALUES (?, ?, ?)', (sender, receiver, msg))
    conn.commit()
    conn.close()
    
    # Рассылаем сообщение (в простом варианте - всем, клиент сам отфильтрует своё)
    emit('receive_dm', data, broadcast=True)
    print(f"[MSG] {sender} -> {receiver}: {msg}")

if __name__ == '__main__':
    init_db()
    # Render использует переменную окружения PORT
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
