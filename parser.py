import requests
from bs4 import BeautifulSoup
import datetime
import re

# Ваша рабочая ссылка — её больше не трогаем
URL = "https://www.ztoe.com.ua/unhooking-search.php"

def parse_ztoe():
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    try:
        response = requests.get(URL, headers=headers, timeout=25)
        response.encoding = 'windows-1251' 
        
        if response.status_code != 200:
            print(f"Сайт облэнерго недоступен: {response.status_code}")
            return

        raw_html = response.text

        # 1. Извлекаем и чистим объявление Укренерго (из блока h3)
        soup = BeautifulSoup(raw_html, "html.parser")
        alert_text = "Важная информация на сайте отсутствует."
        alert_div = soup.find("h3")
        if alert_div:
            alert_html = str(alert_div).replace("<br/>", "\n").replace("<br>", "\n")
            raw_text = BeautifulSoup(alert_html, "html.parser").get_text()
            clean_lines = [line.strip() for line in raw_text.split("\n") if line.strip() and "Пошук черги" not in line and "</div>" not in line]
            alert_text = "\n".join(clean_lines)

        # =========================================================================
        # ЛОГИКА ВАШЕГО JAVA-ПАРСЕРА (ПЕРЕНОС 1 в 1)
        # =========================================================================
        if "Графіки погодинних відключень" not in raw_html:
            print("Маркер графиков не найден на странице.")
            return

        # String[] partsGraff = split(inp, "Графіки погодинних відключень");
        parts_graff = raw_html.split("Графіки погодинних відключень")
        
        # String[] mis = split(partsGraff[1], "width:30pt");
        mis = parts_graff[1].split("width:30pt")
        
        schedule_html = ""

        # Первый день: tableDraw(mis[5], 2); -> индекс 5 соответствует Очереди 3.1
        if len(mis) > 5:
            schedule_html += "<h4>График на текущие сутки:</h4>"
            schedule_html += "<ul>" + table_draw_logic(mis[5]) + "</ul>"
            
        # Второй день (если есть в массиве): if (mis.length > 15) { tableDraw(mis[5+12], 5); }
        if len(mis) > 17: # 5 + 12 = 17 индекс в массиве
            schedule_html += "<h4 style='margin-top:25px;'>График на следующие сутки:</h4>"
            schedule_html += "<ul>" + table_draw_logic(mis[17]) + "</ul>"
        # =========================================================================

        # 3. Собираем страницу вывода
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
                h4 {{ margin-bottom: 10px; color: #333; border-bottom: 2px solid #ebedf0; padding-bottom: 5px; }}
                .alert-box {{ background: #fff3cd; color: #856404; padding: 15px; border-radius: 8px; font-size: 13.5px; margin-bottom: 20px; border: 1px solid #ffeeba; line-height: 1.5; white-space: pre-line; }}
                .update-time {{ font-size: 11px; color: #8d949e; text-align: center; margin-bottom: 15px; }}
                ul {{ list-style: none; padding: 0; margin: 0; }}
                li {{ padding: 8px 0; border-bottom: 1px solid #ebedf0; font-size: 14px; display: flex; justify-content: space-between; align-items: center; }}
                li:last-child {{ border-bottom: none; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>График для Очереди 3.1</h1>
                <div class="update-time">Синхронизировано: {now} (каждый час)</div>
                
                <div class="alert-box"><strong>Официально от Укренерго:</strong><br>{alert_text}</div>
                
                {schedule_html}
            </div>
        </body>
        </html>
        """
        
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html_output)
        print("Успех! index.html сгенерирован по алгоритму Java-парсера.")

    except Exception as e:
        print(f"Критическая ошибка парсинга: {e}")

def table_draw_logic(inp_chunk):
    """
    Аналог вашей функции void tableDraw(String inp).
    Ищет цвета фонов, определяет интервалы времени и формирует строчки для сайта.
    """
    # String[][] misaca = matchAll(inp, "background: #(.*?)\">");
    misaca = re.findall(r'background:\s*#([a-fA-A0-9]{6})', inp_chunk, re.IGNORECASE)
    
    if not misaca:
        return "<li>Свет есть постоянно (интервалы отключений отсутствуют)</li>"
        
    lines = []
    is_light_old = "ffffff" in misaca[0].lower()
    
    # Чтобы вывести первый интервал (например, с 00:00)
    start_time_str = "00:00"
    
    # Проходим по всем 48 полугодиям (24 часа * 2 получаса)
    for i in range(len(misaca)):
        color = misaca[i].lower()
        is_light_current = "ffffff" in color
        
        # Если статус изменился или это самый последний получас суток (i == 47)
        if is_light_current != is_light_old or i == len(misaca) - 1:
            # Вычисляем текущее время (аналог вашего i/2 и проверок на 30 минут)
            hour = i // 2
            minute = "30" if (i % 2 != 0) else "00"
            
            # Обработка финальной точки суток
            if i == len(misaca) - 1:
                end_time_str = "24:00"
            else:
                end_time_str = f"{hour:02d}:{minute}"
            
            # Определяем текстовый статус для завершившегося интервала
            status_text = "<span style='color: #1e7e34;'>⚪ Есть свет</span>" if is_light_old else "<span style='color: #d93025; font-weight: bold;'>🔴 Отключение</span>"
            
            # Добавляем красивую строчку в список
            lines.append(f"<li><span><b>{start_time_str} - {end_time_str}</b></span> <span>{status_text}</span></li>")
            
            # Переключаем флаги для отслеживания следующего интервала
            is_light_old = is_light_current
            start_time_str = end_time_str
            
    return "".join(lines)

if __name__ == "__main__":
    parse_ztoe()
