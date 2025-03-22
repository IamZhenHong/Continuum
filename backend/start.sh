#!/bin/bash

APP_DIR=$(pwd)
VENV_PATH="$APP_DIR/venv/bin/activate"

echo "🚀 Starting Hyperflow environment..."

osascript <<EOF
tell application "Terminal"
    activate

    # Tab 1: Redis (via Docker)
    do script "cd $APP_DIR && source $VENV_PATH && docker start redis || docker run -d --name redis -p 6379:6379 redis"

    delay 1

    # Tab 2: FastAPI
    tell application "System Events" to keystroke "t" using {command down}
    delay 1
    do script "cd $APP_DIR && source $VENV_PATH && uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload" in front window

    delay 1

    # Tab 3: Celery Worker
    tell application "System Events" to keystroke "t" using {command down}
    delay 1
    do script "cd $APP_DIR && source $VENV_PATH && celery -A src.config.celery_config.celery_app worker --loglevel=info --include=src.services.processing_tasks" in front window

    delay 1

    # Tab 4: Celery Beat
    tell application "System Events" to keystroke "t" using {command down}
    delay 1
    do script "cd $APP_DIR && source $VENV_PATH && celery -A src.config.celery_config.celery_app beat --loglevel=info" in front window
end tell
EOF

echo "✅ All services launched in tabs with virtualenv!"
