import os
import subprocess
import logging
from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime
import sys
import time
import threading

app = Flask(__name__)

# Создаем папки, если их нет
os.makedirs('logs', exist_ok=True)
os.makedirs('output', exist_ok=True)

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='logs/app.log',
    filemode='a'
)

# Логирование в консоль
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)

# Путь к папке со скриптами
SCRIPTS_DIR = os.path.join(os.getcwd(), 'scripts')

# Путь к папке с результатами
OUTPUT_DIR = os.path.join(os.getcwd(), 'output')

# Глобальная переменная для хранения логов
script_logs = []

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
        for line in process.stderr:
            script_logs.append(line.strip())
        process.wait()
    except Exception as e:
        script_logs.append(f"Ошибка при выполнении скрипта {script_name}: {str(e)}")

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
    return render_template('index.html')

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
    app.run(debug=True)