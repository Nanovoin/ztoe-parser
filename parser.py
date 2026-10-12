import requests
from bs4 import BeautifulSoup
import datetime
import re

# Используем прямой адрес интерактивной карты, откуда можно забрать ВСЁ и сразу
URL_MAP = "https://ztoe.com.ua"

def parse_ztoe():
    # Имитируем реальный браузер на мобильном телефоне, чтобы сайт не выдавал пустую инфу
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://ztoe.com.ua",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    try:
        # Делаем один точечный запрос методом POST, как это делает сам сайт
        payload = {"action": "get_map"}
        response = requests.post(URL_MAP, headers=headers, data=payload, timeout=25)
        response.encoding = 'windows-1251'
        
        if response.status_code != 200:
            print(f"Сайт временно недоступен. Статус: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, "html.parser")
        
        # 1. Извлекаем глобальный текст объявлений (он дублируется вверху карты в h3)
        alert_text = "Официальный график или важные объявления на сервере отсутствуют."
        alert_div = soup.find("h3")
        if alert_div:
            alert_html = str(alert_div)
            alert_html = alert_html.replace("<br/>", "\n").replace("<br>", "\n")
            alert_text = BeautifulSoup(alert_html, "html.parser").get_text().strip()
            # Форматируем переносы строк для читаемости
            alert_text = re.sub(r'(з \d{2}:\d{2})', r'\n\1', alert_text)
            alert_text = alert_text.replace("Пошук черги та підчерги за адресою", "")

        # 2. Ищем таблицу графиков
        tables = soup.find_all("table")
        if not tables:
            print("Блокировка или пустой ответ: сайт не отдал таблицу.")
            return # Прерываем скрипт, чтобы не перезаписывать работающий index.html пустой заглушкой
            
        target_table = tables[0]
        rows = target_table.find_all("tr")
        
        target_col_idx = None
        schedule_list = []
        current_date_str = ""
        
        # Динамически ищем колонку 3.1
        for row in rows:
            cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
            if "3.1" in cells:
                target_col_idx = cells.index("3.1")
                break
                
        if target_col_idx is None:
            target_col_idx = 8 # Позиция по умолчанию в сетке Житомироблэнерго
            
        for row in rows:
            cells = row.find_all(["td", "th"])
            cell_texts = [c.get_text(strip=True) for c in cells]
            
            if not cell_texts:
                continue
                
            # Извлекаем дату (например, 13.10.2026)
            if len(cell_texts) == 1 and ("." in cell_texts or "202" in cell_texts):
                current_date_str = cell_texts.replace("Графік погодинних відключень", "").strip()
                continue
                
            # Проверяем строки с временными интервалами
            if len(cell_texts) > target_col_idx and "-" in cell_texts[0]:
                time_range = cell_texts[0]
                status_cell = cells[target_col_idx]
                
                cell_class = "".join(status_cell.get("class", []))
                cell_style = status_cell.get("style", "").lower()
                cell_text = status_cell.get_text(strip=True)
                
                # Распознаем статус отключения по цветам или меткам Облэнерго
                if "red" in cell_style or "red" in cell_class or "cc0000" in cell_style or cell_text in ["I", "І"]:
                    status = "<span style='color: #d93025; font-weight: bold;'>🔴 Отключение</span>"
                elif "yellow" in cell_style or "yellow" in cell_class or "maybe" in cell_class or cell_text in ["II", "ІІ"]:
                    status = "<span style='color: #b06000; font-weight: bold;'>🟡 Возможная серая зона</span>"
                else:
                    status = "<span style='color: #1e7e34;'>⚪ Есть свет</span>"
                    
                date_prefix = f"<small style='color:#666;'>{current_date_str}</small> " if current_date_str else ""
                schedule_list.append(f"<li><span>{date_prefix}<b>{time_range}</b></span> <span>{status}</span></li>")

        if not schedule_list:
            print("Расписание не удалось распарсить.")
            return

        schedule_html = "".join(schedule_list)

        # 3. Генерируем финальную страницу
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
                .alert-box {{ background: #fff3cd; color: #856404; padding: 15px; border-radius: 8px; font-size: 13.5px; margin-bottom: 20px; border: 1px solid #ffeeba; line-height: 1.5; white-space: pre-line; }}
                .update-time {{ font-size: 11px; color: #8d949e; text-align: center; margin-bottom: 15px; }}
                ul {{ list-style: none; padding: 0; margin: 0; }}
                li {{ padding: 10px 0; border-bottom: 1px solid #ebedf0; font-size: 14px; display: flex; justify-content: space-between; align-items: center; }}
                li:last-child {{ border-bottom: none; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>График для Очереди 3.1</h1>
                <div class="update-time">Синхронизировано: {now} (каждый час)</div>
                
                <div class="alert-box"><strong>Официально от Укренерго:</strong><br>{alert_text}</div>
                
                <h3 style="font-size: 16px; color: #333;">Почасовой статус:</h3>
                <ul>
                    {schedule_html}
                </ul>
            </div>
        </body>
        </html>
        """
        
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html_output)
        print("index.html успешно обновлен с новыми маскировками запросов!")

    except Exception as e:
        print(f"Ошибка парсинга: {e}")

if __name__ == "__main__":
    parse_ztoe()
