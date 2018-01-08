from flask import Flask
import settings

app = Flask(__name__)
app.secret_key = settings.APP_SECRET
app.config['SQLALCHEMY_DATABASE_URI'] = settings.DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

