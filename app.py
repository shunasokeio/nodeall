from flask import Flask, request, abort, jsonify
# from flask import render_template, session  # Commented out - website not used
import os
import openai
# from flask_cors import CORS  # Commented out - website not used
import time
import random
import logging
from dotenv import load_dotenv
from openai import APIConnectionError, APIError, APITimeoutError
import re
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

load_dotenv()
app = Flask(__name__)
# CORS(app)  # Commented out - website not used

# Initialize LINE Bot API with environment variables
line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', ''))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET', ''))

@app.route("/", methods=['GET', 'POST'])
def health_check():
    """Health check endpoint for Render"""
    if request.method == 'POST':
        # Log POST requests to root for debugging
        logging.warning(f"POST request received at root endpoint. Headers: {dict(request.headers)}")
    return jsonify({"status": "ok"}), 200

@app.route("/callback", methods=['POST', 'GET'])
def callback():
    """LINE webhook callback endpoint"""
    if request.method == 'GET':
        # Allow GET for webhook verification
        return jsonify({"status": "ok"}), 200
    
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
    logging.info(f"Callback received. Method: {request.method}, Has signature: {bool(signature)}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError as e:
        logging.error(f"Invalid signature error: {e}")
        abort(400)

    return jsonify({"status": "ok"}), 200

# --- Dorm Rules Chatbot Logic ---
# Load the rulebook at startup
with open('dorm_rules.txt', encoding='utf-8') as f:
    dorm_rules = f.read()

def build_dorm_prompt(user_question, dorm_rules):
    prompt = (
        "You are a helpful assistant for a student dormitory. Answer the student's question using the dorm rules provided. "
        "If the answer is not in the rules, say you don't know.\n\n"
        "# Dorm Rules (full):\n"
        + dorm_rules + '\n\n'
        + f"# Student's Question:\n{user_question}\n\n# Your Answer:"
    )
    return prompt

def call_gpt(model: str, prompt: str, sys_prompt: str, api_key: str) -> str:
    client = openai.OpenAI(api_key=api_key)
    max_retries = 5
    delay = 2
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=1024,
            )
            return response.choices[0].message.content
        except (APIConnectionError, APIError, APITimeoutError) as e:
            logging.warning(f"OpenAI API error: {e}. Retrying in {delay:.1f} seconds...")
            time.sleep(delay * (1 + random.random()))
            delay *= 2
        except Exception as e:
            raise e
    raise Exception("Failed to get response from OpenAI API after multiple retries.")

# Website routes commented out - not using website functionality
# @app.route('/')
# def home():
#     return render_template('chat.html', chat_title="NODE GROWTH Dorm Rules Chatbot", initial_question="寮のルールについて質問してください。例: ゴミ出しのルールは？")

# @app.route('/chat', methods=['POST'])
# def chat():
#     data = request.json
#     user_input = data.get('message', '')
#     # Always use the full rulebook
#     prompt = build_dorm_prompt(user_input, dorm_rules)
#     api_key = os.environ.get('OPENAI_API_KEY', '')
#     model = 'gpt-4.1-mini-2025-04-14'
#     system_prompt = "You are a helpful assistant for a student dormitory. Answer questions using the provided rules."
#     try:
#         ai_response = call_gpt(model, prompt, system_prompt, api_key)
#         return jsonify({'response': ai_response})
#     except Exception as e:
#         return jsonify({'response': f"Sorry, there was an error: {str(e)}"}), 500

# LINE Bot message handler
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    
    # Build prompt using the same function as web chat
    prompt = build_dorm_prompt(user_message, dorm_rules)
    api_key = os.environ.get('OPENAI_API_KEY', '')
    model = 'gpt-4.1-mini-2025-04-14'
    system_prompt = "You are a helpful assistant for a student dormitory. Answer questions using the provided rules."
    
    try:
        # Get AI response using the same call_gpt function
        ai_response = call_gpt(model, prompt, system_prompt, api_key)
        
        # Send response back to LINE
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=ai_response)
        )
    except Exception as e:
        # Send error message to user
        error_message = f"申し訳ございませんが、エラーが発生しました: {str(e)}"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=error_message)
        )

if __name__ == '__main__':
    app.run(debug=True) 