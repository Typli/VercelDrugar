import os
import subprocess
import logging
from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime
import sys
import time  # Добавляем модуль для задержки

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

def run_pipeline():
    """Запускает конвейер скриптов."""
    try:
        # Шаг 1: Запуск parse.py
        logging.info("Запуск parse.py...")
        subprocess.run(['python3', os.path.join(SCRIPTS_DIR, 'parse.py')], check=True)

        # Шаг 2: Запуск imagemaker.py
        logging.info("Запуск imagemaker.py...")
        subprocess.run(['python3', os.path.join(SCRIPTS_DIR, 'imagemaker.py')], check=True)

        # Шаг 3: Запуск slideshowmaker.py
        logging.info("Запуск slideshowmaker.py...")
        today_date = datetime.now().strftime("%Y-%m-%d")
        subprocess.run(['python3', os.path.join(SCRIPTS_DIR, 'slideshowmaker.py'), today_date], check=True)

        # Возвращаем путь к готовому слайд-шоу
        output_video = os.path.join(OUTPUT_DIR, f"{today_date}.mp4")

        # Проверяем, существует ли файл
        if os.path.exists(output_video):
            logging.info(f"Слайд-шоу успешно создано: {output_video}")
            return output_video
        else:
            logging.error(f"Файл слайд-шоу не найден: {output_video}")
            return None
    except subprocess.CalledProcessError as e:
        logging.error(f"Ошибка при выполнении скрипта: {e}")
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

if __name__ == '__main__':
    app.run(debug=True)