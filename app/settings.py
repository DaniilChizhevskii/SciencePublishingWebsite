import os

# File Settings
home_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')
static_folder = os.path.join(home_folder, 'static')
template_folder = os.path.join(home_folder, 'templates')
books_folder = os.path.join(home_folder, 'books')
db_path = os.path.join(home_folder, 'app/app.db')

# Worker Settings
host = 'localhost'
port = 5000
debug = True

# Security Settings
secret_key = '12345678'
max_content_length = 64 * 1024 * 1024
templates_auto_reload = True
