from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
from collections import OrderedDict


from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# -----------------------------
# Настройки
# -----------------------------
GROUP_NAME = "Bot"  # <-- сюда вставьте имя группы
WHATSAPP_SESSION = "./whatsapp-session"  # папка для сохранения сессии

orders = OrderedDict()  # ключ = имя сотрудника, значение = словарь с блюдом и количеством

# -----------------------------
# Настройка Chrome
# -----------------------------
options = webdriver.ChromeOptions()
options.add_argument(f"user-data-dir={WHATSAPP_SESSION}")  # сохранение сессии
options.add_argument("--remote-debugging-port=9222")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"  # путь до Chrome

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get("https://web.whatsapp.com")

print("Откройте WhatsApp Web и дождитесь полной загрузки...")
time.sleep(15)  # увеличьте до 30 секунд, если интернет медленный

# -----------------------------
# Функция открытия группы
# -----------------------------
def open_group(group_name):
    search_box = driver.find_element(By.XPATH, "//div[@contenteditable='true'][@data-tab='3']")
    search_box.click()
    search_box.clear()
    time.sleep(1)
    search_box.send_keys(group_name)
    search_box.send_keys(Keys.ENTER)
    print(f"Открыта группа: {group_name}")
    time.sleep(3)  # ждём загрузки сообщений

# -----------------------------
# Функции для работы с сообщениями
# -----------------------------
def get_last_messages():
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
    # убираем пустые строки и лишние пробелы
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    
    if len(lines) != 3:
        return None  # не полный заказ
    
    # допускаем два варианта порядка строк: 
    # 1) блюдо — имя — количество
    # 2) блюдо — количество — имя
    dish, second, third = lines

    # проверяем, что second — число
    try:
        qty = int(second)
        name = third
    except ValueError:
        # иначе считаем third числом
        try:
            qty = int(third)
            name = second
        except ValueError:
            return None

    return {"name": name.strip(), "dish": dish.strip(), "qty": qty}

def send_message_to_phone(phone_number, text):
    url = "https://wa.me/" + phone_number
    driver.get(url)
    time.sleep(3)

    # Ищем кнопку "Продолжить в WhatsApp Web"
    try:
        continue_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//a[contains(@href, 'send')]"
            ))
        )
        driver.execute_script("arguments[0].click();", continue_btn)
        print("Кнопка перехода нажата")
    except:
        print("Не удалось нажать кнопку перехода в чат")
        return

    # Ждём поле ввода
    try:
        box = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//div[@contenteditable='true']"
            ))
        )
    except:
        print("Не найдено поле ввода")
        return

    # Отправка
    for line in text.split("\n"):
        box.send_keys(line)
        box.send_keys(Keys.SHIFT, Keys.ENTER)
    box.send_keys(Keys.ENTER)

    print("Сообщение отправлено на номер", phone_number)

    # Возвращаемся в группу
    open_group(GROUP_NAME)

def send_message(text):
    # ждём поле ввода сообщений
    box = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, "//div[@data-tab='10' and @contenteditable='true']"))
    )
    box.click()
    
    # разделяем текст на строки и отправляем каждую отдельно
    for line in text.split("\n"):
        box.send_keys(line)
        box.send_keys(Keys.SHIFT, Keys.ENTER)  # перенос строки без отправки
    box.send_keys(Keys.ENTER)  # отправляем всё сообщение одним Enter

def format_orders(orders):
    summary = "*Список заказов*\n\n"
    for name, info in orders.items():
        summary += f"{name}: {info['dish']} x {info['qty']}\n"
    return summary

def notify_start():
    text = "Бот активирован! Теперь можно присылать заказы в формате:\n\n" \
           "<название блюда> - <количество>\n<имя сотрудника>\n\n" \
           "Для проверки списка заказов: /list\n" \
           "Для очистки списка: /clear"
    send_message(text)
    print("Бот уведомил группу о старте работы.")

# -----------------------------
# Запуск
# -----------------------------
open_group(GROUP_NAME)
notify_start()  # уведомляем группу, что бот запущен

def open_private_chat(user_name):
    search_box = driver.find_element(By.XPATH, "//div[@contenteditable='true'][@data-tab='3']")
    search_box.click()
    search_box.clear()
    time.sleep(1)
    search_box.send_keys(user_name)
    search_box.send_keys(Keys.ENTER)
    print(f"Открыт личный чат с: {user_name}")
    time.sleep(2)

def send_orders_to_user(user_name):
    # открыть личку
    open_private_chat(user_name)

    # отправить список
    summary = format_orders(orders)
    send_message(summary)

    print("Заказы отправлены пользователю:", user_name)

    # вернуться в группу
    open_group(GROUP_NAME)

BOT_NAME = "Snabjenie"
orders = {}
last_msg_text = ""

while True:
    msgs = get_last_messages()
    if not msgs:
        time.sleep(1)
        continue

    name, text = msgs[-1]  # берём только последнее сообщение

    if name == BOT_NAME:
        time.sleep(1)
        continue

    if text == last_msg_text:
        time.sleep(1)
        continue
    last_msg_text = text

    

    # --------------------------
    # Парсим заказ
    # --------------------------
    parsed = parse_order_multiline(text)
    if parsed:
        order_name = parsed['name'].strip()
        dish = parsed['dish'].strip()
        qty = parsed['qty']

        # обновляем заказ, если уже есть
        orders[order_name] = {"dish": dish, "qty": qty}

        send_message(f"Заказ добавлен/обновлён: {order_name} — {dish} × {qty}")
        print(f"Обновлен заказ: {order_name} — {dish} × {qty}")

    # --------------------------
    # Команды
    # --------------------------
    elif text.lower() == "/list":
        send_message(format_orders(orders))

    elif text.lower() == "/clear":
        orders.clear()
        send_message("Список заказов очищен.")

    elif text.lower() == "/sendtoars":
        send_message_to_phone(
            "996502224244",  # <-- сюда твой номер БЕЗ плюса
            format_orders(orders)
        )
        send_message("Отчёт отправлен в личку Арсению.")

    time.sleep(1)