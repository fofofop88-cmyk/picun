from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Хранилище комнат и пользователей
rooms = {}  # format: {room_id: {user_id: username}}
users = {}  # format: {user_id: {room: room_id, username: username}}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    user_id = request.sid
    if user_id in users:
        room = users[user_id]['room']
        username = users[user_id]['username']
        
        leave_room(room)
        if room in rooms and user_id in rooms[room]:
            del rooms[room][user_id]
            if not rooms[room]:
                del rooms[room]
        
        del users[user_id]
        
        print(f"Пользователь {username} покинул комнату {room}")
        
        emit('user_left', {
            'user_id': user_id,
            'username': username
        }, room=room)
    
    print(f'Client disconnected: {request.sid}')

@socketio.on('join_room')
def handle_join_room(data):
    room = data.get('room', 'default')
    username = data.get('username', 'Anonymous')
    
    print(f"Пользователь {username} присоединяется к комнате {room}")
    
    join_room(room)
    users[request.sid] = {
        'room': room,
        'username': username
    }
    
    if room not in rooms:
        rooms[room] = {}
    
    # Сохраняем пользователя с его именем
    rooms[room][request.sid] = username
    
    # Уведомляем других участников
    emit('user_joined', {
        'user_id': request.sid,
        'username': username,
        'users_count': len(rooms[room])
    }, room=room)
    
    # Отправляем текущих пользователей новому участнику
    current_users = []
    for user_id, user_name in rooms[room].items():
        if user_id != request.sid:
            current_users.append({
                'user_id': user_id, 
                'username': user_name
            })
    
    print(f"Текущие пользователи в комнате {room}: {list(rooms[room].values())}")
    
    emit('current_users', {'users': current_users})

@socketio.on('webrtc_offer')
def handle_webrtc_offer(data):
    target_user = data.get('target_user')
    if target_user and target_user in users:
        emit('webrtc_offer', {
            'offer': data['offer'],
            'from_user': request.sid,
            'username': users[request.sid]['username']
        }, room=target_user)

@socketio.on('webrtc_answer')
def handle_webrtc_answer(data):
    target_user = data.get('target_user')
    if target_user and target_user in users:
        emit('webrtc_answer', {
            'answer': data['answer'],
            'from_user': request.sid,
            'username': users[request.sid]['username']
        }, room=target_user)

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    target_user = data.get('target_user')
    if target_user and target_user in users:
        emit('ice_candidate', {
            'candidate': data['candidate'],
            'from_user': request.sid,
            'username': users[request.sid]['username']
        }, room=target_user)

@socketio.on('toggle_audio')
def handle_toggle_audio(data):
    room = users.get(request.sid, {}).get('room')
    if room:
        emit('user_audio_toggle', {
            'user_id': request.sid,
            'username': users[request.sid]['username'],
            'audio_enabled': data.get('enabled', True)
        }, room=room)

@socketio.on('toggle_video')
def handle_toggle_video(data):
    room = users.get(request.sid, {}).get('room')
    if room:
        emit('user_video_toggle', {
            'user_id': request.sid,
            'username': users[request.sid]['username'],
            'video_enabled': data.get('enabled', True)
        }, room=room)

@socketio.on('chat_message')
def handle_chat_message(data):
    room = users.get(request.sid, {}).get('room')
    if room and 'message' in data:
        emit('chat_message', {
            'user_id': request.sid,
            'username': users[request.sid]['username'],
            'message': data['message'],
            'timestamp': data.get('timestamp', '')
        }, room=room)

@socketio.on('get_room_info')
def handle_get_room_info():
    if request.sid in users:
        room = users[request.sid]['room']
        if room in rooms:
            print(f"Информация о комнате {room}: {rooms[room]}")
            emit('room_info', {
                'room': room,
                'users': rooms[room]
            })

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
