from flask import Flask, jsonify, request
from server import app  # Import the Flask app from your main file (app.py)

# Create a lambda function to handle requests
def handler(event, context):
    with app.app_context():
        response = app.full_dispatch_request()
    return {
        "statusCode": 200,
        "body": response.data.decode("utf-8"),
        "headers": {"Content-Type": "application/json"}
    }
