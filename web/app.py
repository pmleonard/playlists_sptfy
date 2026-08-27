from flask import Flask, send_from_directory
from routes.config_routes import bp as config_bp
from routes.export_routes import bp as export_bp
from routes.grouped_songs_routes import bp as grouped_songs_bp
from routes.ignore_duplicates_routes import bp as ignore_duplicates_bp
from routes.import_routes import bp as import_bp
from routes.possible_duplicates_routes import bp as possible_duplicates_bp
from routes.settings_routes import bp as settings_bp
from routes.songs_routes import bp as songs_bp
from routes.update_routes import bp as update_bp

app = Flask(__name__, static_folder="static", static_url_path="/static")

app.register_blueprint(import_bp)
app.register_blueprint(songs_bp)
app.register_blueprint(update_bp)
app.register_blueprint(export_bp)
app.register_blueprint(grouped_songs_bp)
app.register_blueprint(ignore_duplicates_bp)
app.register_blueprint(possible_duplicates_bp)
app.register_blueprint(config_bp)
app.register_blueprint(settings_bp)


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
