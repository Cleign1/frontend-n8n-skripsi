# blueprints/chat/routes.py
from flask import Blueprint, render_template, request, jsonify, current_app # Import current_app
import os
import requests

chat_bp = Blueprint('chat', __name__, template_folder='templates', static_folder='static')

@chat_bp.route('/chat')
def chat():
    """Renders the chat page and passes the webhook URL."""
    # Get the URL from the Flask app's configuration
    webhook_url = current_app.config.get("N8N_CHAT_WEBHOOK_URL")
    # Pass the URL to the template context
    return render_template('chat.html', chat_webhook_url=webhook_url) # Pass the URL here

@chat_bp.route('/chat/send', methods=['POST'])
def send_message():
    """Receives a message from the user, sends it to the n8n agent, and returns the response."""
    user_message = request.json.get('message')
    # Use current_app.config here too for consistency
    webhook_url = current_app.config.get("N8N_CHAT_WEBHOOK_URL") # Use config here too

    if not webhook_url:
        # Use current_app.logger for better logging practice if available, otherwise print
        log_message = 'N8N_CHAT_WEBHOOK_URL not configured'
        try:
            current_app.logger.error(log_message)
        except AttributeError:
            print(f"ERROR: {log_message}")
        return jsonify({'error': log_message}), 500

    try:
        response = requests.post(webhook_url, json={'message': user_message})
        response.raise_for_status()  # Raise an exception for bad status codes
        # Handle potential JSON decoding errors
        try:
            agent_response = response.json().get('response', 'Sorry, I could not parse the response.')
        except requests.exceptions.JSONDecodeError:
             agent_response = 'Error: Received an invalid response format from the chat agent.'
             try:
                 current_app.logger.error(f"Invalid JSON received from {webhook_url}: {response.text}")
             except AttributeError:
                 print(f"ERROR: Invalid JSON received from {webhook_url}: {response.text}")

    except requests.exceptions.RequestException as e:
        error_message = f"Error communicating with n8n: {e}"
        try:
            current_app.logger.error(error_message)
        except AttributeError:
            print(f"ERROR: {error_message}")
        agent_response = error_message # Return the error message

    return jsonify({'response': agent_response})