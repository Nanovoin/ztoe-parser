import requests
from bs4 import BeautifulSoup
import datetime
import re

URL_PAGE = "https://ztoe.com.ua"
# Внутренний системный URL, который отдает чистую таблицу без JS-магии
URL_API = "https://ztoe.com.ua" 

def parse_ztoe():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    try:
        # 1. Сначала берем красивый текст Укренерго с главной страницы
        res_page = requests.get(URL_PAGE, headers=headers, timeout=20)
        res_page.encoding = 'windows-1251'
        
        alert_text = "Важная информация на сайте отсутствует."
        if res_page.status_code == 200:
            soup_page = BeautifulSoup(res_page.text, "html.parser")
            alert_div = soup_page.find("h3")
            if alert_div:
                # Берем HTML, заменяем теги <br> на переносы строк, удаляем остальные теги
                alert_html = str(alert_div)
                alert_html = alert_html.replace("<br/>", "\n").replace("<br>", "\n")
                alert_text = BeautifulSoup(alert_html, "html.parser").get_text()
                
                # Делаем красивые переносы перед "з 00:00", "з 06:00" и т.д.
                alert_text = re.sub(r'(з \d{2}:\d{2})', r'\n\1', alert_text)
                # Убираем фразу поиска в конце, если она слиплась
                alert_text = alert_text.replace("Пошук черги та підчерги за адресою", "")

        # 2. Теперь делаем POST-запрос к скрытому графику, чтобы получить саму сетку
        # Передаем параметры, как это делает сам сайт при загрузке таблицы
        payload = {"action": "get_map"} 
        res_api = requests.post(URL_API, headers=headers, data=payload, timeout=20)
        res_api.encoding = 'windows-1251'
        
        if res_api.status_code != 200:
            print(f"Ошибка доступа к API графиков: {res_api.status_code}")
            return

        soup = BeautifulSoup(res_api.text, "html.parser")
        tables = soup.find_all("table")
        
        if not tables:
            print("Таблица графиков во внутреннем API не найдена.")
            return
            
        target_table = tables[0]
        rows = target_table.find_all("tr")
        
        target_col_idx = None
        schedule_list = []
        current_date_str = ""
        
        # Определяем, в какой колонке находится очередь 3.1
        for row in rows:
            cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
            if "3.1" in cells:
                target_col_idx = cells.index("3.1")
                break
                
        if target_col_idx is None:
            # Резервный индекс, если шапка изменится
            target_col_idx = 8 
            
        for row in rows:
            cells = row.find_all(["td", "th"])
            cell_texts = [c.get_text(strip=True) for c in cells]
            
            if not cell_texts:
                continue
                
            # Фиксируем дату
            if len(cell_texts) == 1 and ("." in cell_texts[0] or "202" in cell_texts[0]):
                current_date_str = cell_texts[0].replace("Графік погодинних відключень", "").strip()
                continue
                
            # Проверяем, что строка — это интервал времени (например, 06:00-06:30)
            if len(cell_texts) > target_col_idx and "-" in cell_texts[0] and cell_texts[0][0].isdigit():
                time_range = cell_texts[0]
                status_cell = cells[target_col_idx]
                
                # Проверяем статус по цвету фона (классы или инлайн-стили Житомироблэнерго)
                cell_class = status_cell.get("class", [])
                cell_style = status_cell.get("style", "").lower()
                cell_text = status_cell.get_text(strip=True)
                
                # Логика определения отключения (красный цвет или символ 'I'/'І')
                if "red" in cell_style or "red" in cell_class or "cc0000" in cell_style or cell_text in ["I", "І"]:
                    status = "<span style='color: #d93025; font-weight: bold;'>🔴 Отключение</span>"
                elif "yellow" in cell_style or "yellow" in cell_class or "maybe" in cell_class:
                    status = "<span style='color: #b06000; font-weight: bold;'>🟡 Возможная серая зона</span>"
                else:
                    status = "<span style='color: #1e7e34;'>⚪ Есть свет</span>"
                    
                date_prefix = f"<small style='color:#666;'>{current_date_str}</small> " if current_date_str else ""
                schedule_list.append(f"<li><span>{date_prefix}<b>{time_range}</b></span> <span>{status}</span></li>")

        schedule_html = "".join(schedule_list) if schedule_list else "<li>График пуст. Похоже, ограничений для 3.1 на этот час нет.</li>"

        # 3. Собираем итоговую страницу
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
                <div class="update-time">Синхронизировано: {now}</div>
                
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
        print("Всё исправлено! index.html успешно обновлен.")

    except Exception as e:
        print(f"Критическая ошибка парсинга: {e}")

if __name__ == "__main__":
    parse_ztoe()
