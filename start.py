from app.main import app, settings

app.run(port=settings.port, host=settings.host, debug=settings.debug)
