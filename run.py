# run.py
from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    # Use socketio.run() to start a WebSocket-aware server.
    # The standard 'flask run' command does not work with Flask-SocketIO.
    # allow_unsafe_werkzeug=True is needed for debug mode with recent Werkzeug versions.
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
