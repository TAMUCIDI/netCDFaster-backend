# wsgi.py （新建在项目根目录）
from .app import create_app

application = create_app()  # Gunicorn 需要名为 application 的变量

if __name__ == "__main__":
    application.run()