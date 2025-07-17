from flask import Flask, request, render_template_string, redirect, url_for, session
import os
from dotenv import load_dotenv
from twilio.rest import Client
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_number = os.getenv('TWILIO_PHONE_NUMBER')
admin_password = os.getenv('ADMIN_PASSWORD')  # Password for admin actions

client = Client(account_sid, auth_token)
LOG_FILE = "sms_log.txt"

html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Professional SMS App</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: #f4f7f8;
            color: #333;
        }
        header {
            background-color: #2d4059;
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 24px;
        }
        .container {
            max-width: 900px;
            margin: auto;
            padding: 20px;
            background: white;
            box-shadow: 0px 0px 10px rgba(0,0,0,0.1);
            margin-top: 30px;
            border-radius: 8px;
        }
        input, textarea {
            width: 100%;
            padding: 10px;
            margin: 8px 0;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 16px;
        }
        button {
            background-color: #1f4068;
            color: white;
            padding: 10px 20px;
            margin-top: 10px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #162f4a;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }
        th {
            background-color: #2d4059;
            color: white;
        }
        .success { color: green; }
        .error { color: red; }
        pre {
            background-color: #f1f1f1;
            padding: 10px;
            overflow-x: auto;
            max-height: 300px;
            border: 1px solid #ccc;
        }
        h3 {
            border-bottom: 2px solid #ccc;
            padding-bottom: 5px;
        }
    </style>
</head>
<body>
    <header>📨 SMS Management Dashboard</header>
    <div class="container">
        <h3>Send SMS</h3>
        <form method="POST" action="/send-sms">
            <input name="to" placeholder="Recipient Number" required><br>
            <textarea name="message" placeholder="Enter your message here..." required></textarea><br>
            <button type="submit">Send SMS</button>
        </form>

        {% if sms_log %}
            <h3>Session SMS Log</h3>
            <table>
                <tr><th>To</th><th>Message</th><th>Status</th><th>Time</th></tr>
                {% for log in sms_log %}
                <tr>
                    <td>{{ log.to }}</td>
                    <td>{{ log.message }}</td>
                    <td>{{ log.status }}</td>
                    <td>{{ log.time }}</td>
                </tr>
                {% endfor %}
            </table>
        {% endif %}

        <h3>Admin Panel</h3>
        <form method="POST" action="/delete-log-file">
            <input name="admin_pass" placeholder="Admin Password" type="password" required>
            <button type="submit">🧹 Clear All Log File</button>
        </form>

        <form method="POST" action="/delete-line">
            <input name="admin_pass" placeholder="Admin Password" type="password" required><br>
            <input name="line_number" placeholder="Line number to delete" required>
            <button type="submit">❌ Delete Specific Line</button>
        </form>

        <form method="POST" action="/view-log">
            <input name="admin_pass" placeholder="Admin Password" type="password" required>
            <button type="submit">📄 View Log File</button>
        </form>

        {% if admin_message %}<p class="{{ 'success' if admin_success else 'error' }}">{{ admin_message }}</p>{% endif %}
        {% if log_content %}<pre>{{ log_content }}</pre>{% endif %}
    </div>
</body>
</html>
"""

def save_to_file(to, message, status):
    time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{time_str} | TO: {to} | MESSAGE: {message} | STATUS: {status}\n")

@app.route('/', methods=['GET'])
def home():
    return render_template_string(html_template, sms_log=session.get('sms_log', []), admin_message=None, admin_success=None, log_content=None)

@app.route('/send-sms', methods=['POST'])
def send_sms():
    to = request.form.get('to')
    message = request.form.get('message')
    time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        client.messages.create(to=to, from_=twilio_number, body=message)
        status = '✅ Sent'
    except Exception as e:
        status = f'❌ {str(e)}'

    sms_log = session.get('sms_log', [])
    sms_log.append({'to': to, 'message': message, 'status': status, 'time': time_str})
    session['sms_log'] = sms_log

    save_to_file(to, message, status)

    return redirect(url_for('home'))

@app.route('/delete-log-file', methods=['POST'])
def delete_log_file():
    if request.form.get('admin_pass') != admin_password:
        return render_template_string(html_template, sms_log=session.get('sms_log', []), admin_message="Wrong password", admin_success=False, log_content=None)

    open(LOG_FILE, 'w').close()
    return render_template_string(html_template, sms_log=session.get('sms_log', []), admin_message="All logs cleared", admin_success=True, log_content=None)

@app.route('/delete-line', methods=['POST'])
def delete_line():
    if request.form.get('admin_pass') != admin_password:
        return render_template_string(html_template, sms_log=session.get('sms_log', []), admin_message="Wrong password", admin_success=False, log_content=None)

    try:
        line_number = int(request.form.get('line_number'))
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if 1 <= line_number <= len(lines):
            del lines[line_number - 1]
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            message = f"Line {line_number} deleted"
            success = True
        else:
            message = "Invalid line number"
            success = False

    except Exception as e:
        message = f"Error: {str(e)}"
        success = False

    return render_template_string(html_template, sms_log=session.get('sms_log', []), admin_message=message, admin_success=success, log_content=None)

@app.route('/view-log', methods=['POST'])
def view_log():
    if request.form.get('admin_pass') != admin_password:
        return render_template_string(html_template, sms_log=session.get('sms_log', []), admin_message="Wrong password", admin_success=False, log_content=None)

    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        content = "Log file not found."

    return render_template_string(html_template, sms_log=session.get('sms_log', []), admin_message="Log file loaded", admin_success=True, log_content=content)

if __name__ == '__main__':
    app.run(debug=True)