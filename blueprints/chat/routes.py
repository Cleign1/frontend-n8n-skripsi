from flask import Blueprint, render_template, request, jsonify
import os
import requests

chat_bp = Blueprint('chat', __name__, template_folder='templates', static_folder='static')

@chat_bp.route('/chat')
def chat():
    """Renders the chat page."""
    return render_template('chat.html')

@chat_bp.route('/chat/send', methods=['POST'])
def send_message():
    """Receives a message from the user, sends it to the n8n agent, and returns the response."""
    user_message = request.json.get('message')
    webhook_url = os.getenv("N8N_CHAT_WEBHOOK_URL")

    if not webhook_url:
        return jsonify({'error': 'N8N_CHAT_WEBHOOK_URL not configured'}), 500

    try:
        response = requests.post(webhook_url, json={'message': user_message})
        response.raise_for_status()  # Raise an exception for bad status codes
        agent_response = response.json().get('response', 'Sorry, I could not get a response.')
    except requests.exceptions.RequestException as e:
        agent_response = f"Error communicating with n8n: {e}"

    return jsonify({'response': agent_response})
