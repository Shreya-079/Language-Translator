import os
from flask import Flask, render_template, request, redirect, session, url_for
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from pymongo import MongoClient
from datetime import datetime
from googletrans import Translator
import uuid
from googletrans import LANGUAGES
    
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret")

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")    
 # or use your MongoDB Atlas URI    
db = client["language_app"]
auth_users = db["auth_users"]
user_profiles = db["user_profiles"]
user_activity = db["user_activity"]
translation_history = db["translation_history"]

translator = Translator()

# ----------- Routes ------------

@app.route('/')
def home():
    if "username" in session:
        return redirect('/translate')
    return redirect('/login')


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        data = request.form.to_dict()
        
        # Final backend check for duplicate username
        if auth_users.find_one({"username": data["username"]}):
            flash("Username already exists, choose a different one.")
            return redirect("/signup")
        
        # Password confirmation check
        if data["password"] != data["confirm_password"]:
            flash("Passwords do not match.")
            return redirect("/signup")
        
        # Save auth details
        auth_users.insert_one({
            "username": data["username"],
            "password": data["password"]
        })

        # Save additional user details
        user_profiles.insert_one({
            "name": data["name"],
            "email": data["email"],
            "username": data["username"],
            "age": data["age"],
            "gender": data["gender"]
        })

        flash("User registered successfully! Please log in.")
        return redirect("/login")

    return render_template("signup.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = auth_users.find_one({
            'username': request.form['username'],
            'password': request.form['password']
        })
        if user:
            session['username'] = user['username']
            log_activity(user['username'], "Login")
            return redirect('/translate')
        else:
            return "Invalid credentials!"
    return render_template('login.html')

@app.route('/logout')
def logout():
    log_activity(session['username'], "Logout")
    session.pop('username', None)
    return redirect('/login')

@app.route('/translate', methods=['GET', 'POST'])
def translate():
    if "username" not in session:
        return redirect('/login')
    translated = ""
    from_lang = "auto"
    to_lang = "en"
    original_text = ""

    if request.method == 'POST':
        original_text = request.form['text']
        to_lang = request.form['lang']
        result = translator.translate(original_text, dest=to_lang)
        translated = result.text

        # Store translation history
        translation_history.insert_one({
            "username": session["username"],
            "from": result.src,
            "to": to_lang,
            "original_text": original_text,
            "translated_text": translated,
            "time": str(datetime.now())
        })

        log_activity(session["username"], f"Translated text from {result.src} to {to_lang}")

    # 🛠️ FIX: Pass LANGUAGES to the template
    return render_template('translate.html', translated=translated, original=original_text, languages=LANGUAGES)

@app.route('/history')
def history():
    if "username" not in session:
        return redirect('/login')
    history = list(translation_history.find({"username": session["username"]}))
    return render_template("history.html", history=history)

# ----------- Helper ------------

def log_activity(username, action):
    user_activity.insert_one({
        "username": username,
        "action": action,
        "timestamp": str(datetime.now())
    })
@app.route('/check_username')
def check_username():
    username = request.args.get('username')
    user = auth_users.find_one({'username': username})
    return jsonify({'exists': bool(user)})

# ----------- Run Server ------------
if __name__ == '__main__':
    app.run(debug=True)
