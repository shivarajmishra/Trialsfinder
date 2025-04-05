from app import app  # assuming your Flask app is in app.py

def handler(event, context):
    from serverless_wsgi import handle_request
    return handle_request(app, event, context)
