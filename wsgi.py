"""WSGI entry point for Gunicorn"""
from app import create_app

application = create_app()  # Gunicorn requires a variable named 'application'

if __name__ == "__main__":
    application.run()