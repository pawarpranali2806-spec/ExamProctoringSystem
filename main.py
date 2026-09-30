# Main entrypoint alias for Railway/PaaS platforms that default to 'main:app'
from wsgi import app

if __name__ == '__main__':
    app.run()
