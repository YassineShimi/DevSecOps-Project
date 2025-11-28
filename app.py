from flask import Flask, request, render_template_string
import sqlite3

app = Flask(__name__)

# Page d'accueil avec formulaire
@app.route('/')
def home():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>DevSecOps Demo App</title>
        <style>
            body { font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px; }
            input, button { padding: 10px; margin: 5px; }
            .container { border: 1px solid #ddd; padding: 20px; border-radius: 8px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1> Application DevSecOps</h1>
            <h3>Test 1: Formulaire de salutation</h3>
            <form action="/greet" method="post">
                <input type="text" name="username" placeholder="Entrez votre nom">
                <button type="submit">Envoyer</button>
            </form>
            
            <hr>
            
            <h3>Test 2: Recherche utilisateur</h3>
            <form action="/search" method="post">
                <input type="text" name="user_id" placeholder="ID utilisateur">
                <button type="submit">Rechercher</button>
            </form>
        </div>
    </body>
    </html>
    ''')

# Route vulnérable au XSS (Cross-Site Scripting)
@app.route('/greet', methods=['POST'])
def greet():
    username = request.form.get('username', '')
    # VULNÉRABILITÉ: Pas d'échappement HTML
    return f'<h1>Bonjour {username}!</h1><a href="/">Retour</a>'

# Route vulnérable à l'injection SQL
@app.route('/search', methods=['POST'])
def search():
    user_id = request.form.get('user_id', '')
    # VULNÉRABILITÉ: Injection SQL directe
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id = {user_id}"
    try:
        cursor.execute(query)
        result = cursor.fetchall()
        return f'<p>Résultat: {result}</p><a href="/">Retour</a>'
    except Exception as e:
        return f'<p>Erreur: {str(e)}</p><a href="/">Retour</a>'

# Secret exposé (VULNÉRABILITÉ)
API_KEY = "sk-1234567890abcdefghijklmnopqrstuvwxyz"
SECRET_TOKEN = "ghp_SecretGitHubTokenExample123456789"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
