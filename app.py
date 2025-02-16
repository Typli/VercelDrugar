import os
import subprocess
import logging
from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime
import sys
import time
import json
import asyncio

app = Flask(__name__)

# Создаем папки, если их нет
os.makedirs('logs', exist_ok=True)
os.makedirs('output', exist_ok=True)

# Настройка логов Flask
logging.getLogger('werkzeug').setLevel(logging.DEBUG)  # Включаем логи Flask для запуска сервера

# Логирование в файл и консоль
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),  # Логи в файл
        logging.StreamHandler(sys.stdout)     # Логи в консоль
    ]
)

# Путь к папке со скриптами
SCRIPTS_DIR = os.path.join(os.getcwd(), 'scripts')

# Путь к папке с результатами
OUTPUT_DIR = os.path.join(os.getcwd(), 'output')

# Глобальная переменная для хранения логов
script_logs = []

# Загрузка конфигурации
def load_config():
    if os.path.exists('config.json'):
        with open('config.json', 'r') as f:
            return json.load(f)
    return {}

# Сохранение конфигурации
def save_config(api_key, user_id):
    with open('config.json', 'w') as f:
        json.dump({'api_key': api_key, 'user_id': user_id}, f)

def run_script(script_name, args=None):
    """Запускает скрипт и захватывает его вывод."""
    global script_logs
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    try:
        process = subprocess.Popen(
            ['python3', script_path] + (args if args else []),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        for line in process.stdout:
            script_logs.append(line.strip())
            logging.info(line.strip())  # Логируем вывод скрипта
        for line in process.stderr:
            script_logs.append(line.strip())
            logging.error(line.strip())  # Логируем ошибки скрипта
        process.wait()
    except Exception as e:
        error_msg = f"Ошибка при выполнении скрипта {script_name}: {str(e)}"
        script_logs.append(error_msg)
        logging.error(error_msg)

def run_pipeline():
    """Запускает конвейер скриптов."""
    global script_logs
    script_logs = []  # Очищаем логи перед запуском
    try:
        # Шаг 1: Запуск parse.py
        logging.info("Запуск parse.py...")
        run_script('parse.py')

        # Шаг 2: Запуск imagemaker.py
        logging.info("Запуск imagemaker.py...")
        run_script('imagemaker.py')

        # Шаг 3: Запуск slideshowmaker.py
        logging.info("Запуск slideshowmaker.py...")
        today_date = datetime.now().strftime("%Y-%m-%d")
        run_script('slideshowmaker.py', [today_date])

        # Возвращаем путь к готовому слайд-шоу
        output_video = os.path.join(OUTPUT_DIR, f"{today_date}.mp4")

        # Проверяем, существует ли файл
        if os.path.exists(output_video):
            logging.info(f"Слайд-шоу успешно создано: {output_video}")
            return output_video
        else:
            logging.error(f"Файл слайд-шоу не найден: {output_video}")
            return None
    except Exception as e:
        logging.error(f"Ошибка при выполнении конвейера: {e}")
        return None

@app.route('/')
def index():
    """Главная страница."""
    config = load_config()
    if not config:
        return render_template('setup.html')
    return render_template('index.html')

@app.route('/setup', methods=['POST'])
def setup():
    """Сохранение конфигурации Telegram."""
    api_key = request.form.get('api_key')
    user_id = request.form.get('user_id')
    if api_key and user_id:
        save_config(api_key, user_id)
        return jsonify({'status': 'success', 'message': 'Конфигурация сохранена.'})
    return jsonify({'status': 'error', 'message': 'Неверные данные.'}), 400

@app.route('/start', methods=['POST'])
def start_pipeline():
    """Запускает конвейер и возвращает статус."""
    logging.info("Запуск конвейера...")
    output_video = run_pipeline()

    if output_video:
        # Добавляем небольшую задержку перед проверкой
        time.sleep(2)  # 2 секунды задержки

        if os.path.exists(output_video):
            logging.info("Конвейер успешно завершен.")
            # Отправляем видео в Telegram
            from bot import send_video_to_user
            asyncio.run(send_video_to_user(output_video))
            return jsonify({
                'status': 'success',
                'message': 'Конвейер успешно завершен.',
                'download_link': f'/download/{os.path.basename(output_video)}'
            })
        else:
            logging.error("Файл слайд-шоу не найден после завершения конвейера.")
            return jsonify({
                'status': 'error',
                'message': 'Файл слайд-шоу не найден.'
            }), 500
    else:
        logging.error("Ошибка при выполнении конвейера.")
        return jsonify({
            'status': 'error',
            'message': 'Ошибка при выполнении конвейера.'
        }), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Отдает файл для скачивания."""
    file_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "Файл не найден.", 404

@app.route('/logs')
def get_logs():
    """Возвращает текущие логи скриптов."""
    global script_logs
    return jsonify({'log': '\n'.join(script_logs)})

if __name__ == '__main__':
    # Логирование запуска сервера
    logging.info("Запуск Flask-приложения...")
    logging.info(f"Сервер доступен по адресу: http://127.0.0.1:5000")
    app.run(debug=True)