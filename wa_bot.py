from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
from selenium.webdriver.common.by import By
from collections import OrderedDict

orders = OrderedDict()  # ключ = имя сотрудника, значение = словарь с блюдом и количеством




options = webdriver.ChromeOptions()
options.add_argument('user-data-dir=./whatsapp-session')
options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

driver.get('https://web.whatsapp.com')
print('Откройте whatsapp web и дождитесь полной загрузки')
time.sleep(15)


def get_last_massages():
    messages = driver.find_elements(By.CSS_SELECTOR, "div.message-in, div.message-out")
    extracted = []

    for m in messages[-10:]:  # последние 10 сообщений
        try:
            text_el = m.find_element(By.CSS_SELECTOR, "span.selectable-text")
            text = text_el.text
        except:
            continue
        try:
            name_el = m.find_element(By.CSS_SELECTOR, "span._11JPr")
            name = name_el.text
        except:
            name = "Unknown"
        extracted.append((name, text))
    return extracted


def parse_order_multiline(text):
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    if len(lines) < 2:
        return None
    name = lines[-1]
    dish_line = lines[-2]
    if "-" not in dish_line:
        return None
    dish_part, qty_part = dish_line.split("-", 1)
    dish = dish_part.strip()
    match = re.search(r"\d+", qty_part)
    if not match:
        return None
    qty = int(match.group())
    return {"name": name, "dish": dish, "qty": qty}

def send_message(text):
    box = driver.find_element(By.CSS_SELECTOR, "div[contenteditable='true']")
    box.click()
    box.send_keys(text)
    driver.find_element(By.CSS_SELECTOR, "span[data-icon='send']").click()

def format_orders(orders):
    summary = "📋 *Список заказов*\n\n"
    for name, info in orders.items():
        summary += f"👤 {name} — 🍽 {info['dish']} × {info['qty']}\n"
    return summary



orders = {}
last_msg = ""

while True:
    msgs = get_last_massages()
    for name, text in msgs:
        if text == last_msg:
            continue
        last_msg = text
        parsed = parse_order_multiline(text)
        if parsed:
            name = parsed['name']
            dish = parsed['dish']
            qty = parsed['qty']
            
            # Если заказ уже есть, удаляем, чтобы обновить и сохранить порядок
            if name in orders:
                del orders[name]
            
            orders[name] = {'dish': dish, 'qty': qty}
            print(f"Обновлен заказ: {name} — {dish} × {qty}")

        elif text == "/list":
            send_message(format_orders(orders))
        elif text == "/clear":
            orders.clear()
            send_message("✅ Список заказов очищен.")
    time.sleep(2)
