import requests
from bs4 import BeautifulSoup
import datetime

URL = "https://www.ztoe.com.ua/unhooking-search.php"

def parse_ztoe():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(URL, headers=headers, timeout=20)
        response.encoding = 'windows-1251' # Сайт использует кодировку кодировку Windows-1251
        
        if response.status_code != 200:
            print(f"Ошибка доступа к сайту: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, "html.parser")
        
        # 1. Парсим глобальное объявление от Укренерго (верхний баннер)
        alert_text = "Важная информация на сайте отсутствует."
        alert_div = soup.find("h3") # Текст предупреждения обычно в h3 или блоке alert
        if alert_div:
            alert_text = alert_div.get_text(strip=True)
            
        # 2. Ищем таблицу графиков
        tables = soup.find_all("table")
        if not tables:
            print("Таблица графиков не найдена на странице.")
            return
            
        # Выбираем целевую таблицу (обычно она самая большая или содержит строки времени)
        target_table = tables[0]
        rows = target_table.find_all("tr")
        
        # Определяем индекс столбца "3.1"
        target_col_idx = None
        header_cells = []
        
        # Ищем строку с заголовками очередей (1, 1.1, 1.2, 2, ... 3, 3.1 ...)
        for row in rows:
            cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
            if "3.1" in cells:
                header_cells = cells
                target_col_idx = cells.index("3.1")
                break
                
        if target_col_idx is None:
            # Если точная строка заголовков не определилась, ставим индекс по умолчанию (для сетки ZTOE)
            target_col_idx = 8 # Примерная позиция колонки 3.1 в стандартной верстке
            
        schedule_list = []
        current_date_str = ""
        
        # Собираем строки расписания
        for row in rows:
            cells = row.find_all(["td", "th"])
            cell_texts = [c.get_text(strip=True) for c in cells]
            
            if not cell_texts:
                continue
                
            # Если строка содержит дату (например, "13.10.2026")
            if len(cell_texts) == 1 and ("." in cell_texts[0] or "202" in cell_texts[0]):
                current_date_str = cell_texts[0]
                continue
                
            # Обрабатываем строки с временными интервалами (например, 08:00-08:30)
            if len(cell_texts) > target_col_idx and "-" in cell_texts[0] and cell_texts[0][0].isdigit():
                time_range = cell_texts[0]
                status_cell = cells[target_col_idx]
                
                # Проверяем цвет ячейки (Облэнерго кодирует цветом фона или классами)
                style = status_cell.get("style", "").lower()
                bg_color = ""
                
                if "red" in style or "cc0000" in style or "ff0000" in style:
                    status = "🔴 Отключение"
                elif "white" in style or "ffffff" in style:
                    status = "⚪ Есть свет"
                else:
                    # Попытка определить по тексту или наличию символов
                    text = status_cell.get_text(strip=True)
                    if text == "I" or text == "І" or "відкл" in text.lower():
                        status = "🔴 Отключение"
                    else:
                        status = "⚪ Есть свет / Возможная серая зона"
                        
                date_prefix = f"[{current_date_str}] " if current_date_str else ""
                schedule_list.append(f"<li><b>{date_prefix}{time_range}</b> — {status}</li>")

        # Если расписание пустое, даем базовый вывод
        schedule_html = "".join(schedule_list) if schedule_list else "<li>График на ближайшие часы не сгенерирован или свет есть постоянно.</li>"

        # 3. Генерируем чистую и легкую HTML страницу
        now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        html_output = f"""
        <!DOCTYPE html>
        <html lang="uk">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Очередь 3.1 — Житомироблэнерго</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 15px; background: #f0f2f5; color: #1c1e21; }}
                .card {{ max-width: 500px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
                h1 {{ font-size: 20px; color: #0056b3; margin-top: 0; text-align: center; }}
                .badge {{ display: block; background: #e7f3ff; color: #1877f2; padding: 10px; border-radius: 8px; font-size: 13px; font-weight: bold; margin-bottom: 15px; text-align: center; border-left: 4px solid #1877f2; }}
                .alert-box {{ background: #fff3cd; color: #856404; padding: 12px; border-radius: 8px; font-size: 13px; margin-bottom: 20px; border: 1px solid #ffeeba; line-height: 1.4; }}
                .update-time {{ font-size: 11px; color: #8d949e; text-align: center; margin-bottom: 15px; }}
                ul {{ list-style: none; padding: 0; margin: 0; }}
                li {{ padding: 10px 0; border-bottom: 1px solid #ebedf0; font-size: 14px; display: flex; justify-content: space-between; }}
                li:last-child {{ border-bottom: none; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>График для Очереди 3.1</h1>
                <div class="update-time">Данные обновлены: {now}</div>
                
                <div class="badge">Статус вашей очереди фильтруется автоматически</div>
                
                <div class="alert-box">
                    <strong>Официально от Укренерго:</strong><br>{alert_text}
                </div>
                
                <h3>Планируемые часы:</h3>
                <ul>
                    {schedule_html}
                </ul>
            </div>
        </body>
        </html>
        """
        
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html_output)
        print("index.html успешно перезаписан для очереди 3.1!")

    except Exception as e:
        print(f"Ошибка парсинга: {e}")

if __name__ == "__main__":
    parse_ztoe()
