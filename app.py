import os
import re
import time
import requests
import random
import threading
import concurrent.futures
import flet as ft
from flet import (
    Column, Row, Text, TextField, Dropdown, dropdown, Slider, ElevatedButton,
    ProgressBar, ListView, Divider, Container, padding, alignment, border, Icons, Colors, Switch
)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
}

def parse_wb_input(user_input):
    user_input = user_input.strip()
    if user_input.isdigit(): return user_input
    match = re.search(r'catalog/(\d+)/', user_input)
    return match.group(1) if match else None

def find_images_on_server(article_id, server_range, host_options, log_callback, detailed_logging):
    images = []
    found_combination = False
    correct_host_template, correct_server_str = "", ""

    for server_id in server_range:
        for host_template in host_options:
            server_str = f"{server_id:02d}"
            host = host_template.format(server=server_str)
            vol, part = (article_id[:-5], article_id[:-3])
            url = f"{host}/vol{vol}/part{part}/{article_id}/images/big/1.webp"
            try:
                if detailed_logging:
                    log_callback(f"  [PROBE] {url}")
                response = requests.head(url, headers=HEADERS, timeout=2)
                if response.status_code == 200:
                    correct_host_template, correct_server_str = host_template, server_str
                    found_combination = True
                    break
            except requests.exceptions.RequestException:
                continue
        if found_combination:
            break
    
    if not found_combination:
        log_callback(f"Артикул {article_id}: Не удалось найти рабочую комбинацию сервера и хоста.")
        return []

    log_callback(f"Артикул {article_id}: Найдена комбинация. Сервер: {correct_server_str}, Хост: {correct_host_template.split('/')[2]}. Ищу все изображения...")
    
    host = correct_host_template.format(server=correct_server_str)
    vol, part = (article_id[:-5], article_id[:-3])
    max_images = 50
    for img_id in range(1, max_images + 1):
        url = f"{host}/vol{vol}/part{part}/{article_id}/images/big/{img_id}.webp"
        try:
            if requests.head(url, headers=HEADERS, timeout=2).status_code == 200:
                images.append(url)
            else:
                break
        except requests.exceptions.RequestException:
            break
    return images

def download_images_for_article(article_id, image_urls, max_workers, progress_callback, log_callback):
    save_dir = f"images/{article_id}"
    os.makedirs(save_dir, exist_ok=True)
    total_images = len(image_urls)
    downloaded_count = 0

    def download_image_task(url, img_path):
        nonlocal downloaded_count
        try:
            response = requests.get(url, headers=HEADERS, stream=True, timeout=15)
            response.raise_for_status()
            with open(img_path, "wb") as f: f.write(response.content)
            downloaded_count += 1
            progress_callback(downloaded_count / total_images)
            return True
        except requests.exceptions.RequestException:
            log_callback(f"  [Ошибка] при скачивании {url}")
            return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(download_image_task, url, f"{save_dir}/{i+1}.webp") for i, url in enumerate(image_urls)]
        concurrent.futures.wait(futures)
        
    log_callback(f"Артикул {article_id}: Загрузка завершена. Файлы в папке: {os.path.abspath(save_dir)}")

def main(page: ft.Page):
    page.title = "WB Photo Downloader"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.window_width = 700
    page.window_height = 800
    page.theme_mode = ft.ThemeMode.DARK

    articles_field = TextField(label="Артикулы или ссылки через запятую", hint_text="271516033, 271515437...", expand=True)
    start_button = ElevatedButton(text="Начать скачивание", icon=Icons.DOWNLOAD, height=40)
    
    domain_dropdown = Dropdown(label="Домен для поиска", value="wbcontent.net", options=[
        dropdown.Option("wbcontent.net", "basket-xx.wbcontent.net"),
        dropdown.Option("wbbasket.ru", "basket-xx.wbbasket.ru"),
        dropdown.Option("Оба домена", "Оба домена"),
    ])
    
    algo_dropdown = Dropdown(label="Алгоритм обхода серверов", value="desc", options=[
        dropdown.Option("desc", "От большего к меньшему (Рекомендуется)"),
        dropdown.Option("asc", "От меньшего к большему"),
        dropdown.Option("random", "Случайный порядок"),
    ])
    
    max_server_slider = Slider(min=10, max=100, divisions=9, value=30, label="Макс. сервер: {value}")
    max_workers_slider = Slider(min=1, max=10, divisions=9, value=5, label="Потоков: {value}")
    
    detailed_log_switch = Switch(label="Подробный лог", value=False)
    
    progress_bar = ProgressBar(value=0, visible=False, bar_height=10)
    log_view = ListView(spacing=5, auto_scroll=True, expand=True)

    def start_download_thread(e):
        start_button.disabled = True
        progress_bar.value = 0
        progress_bar.visible = True
        log_view.controls.clear()
        page.update()
        threading.Thread(target=download_worker, daemon=True).start()

    def log_message(message):
        log_view.controls.append(Text(message, size=12))
        page.update()

    def update_progress(value):
        progress_bar.value = value
        page.update()

    def download_worker():
        articles_raw = [item.strip() for item in articles_field.value.split(',')]
        articles = [parse_wb_input(a) for a in articles_raw if parse_wb_input(a)]
        
        if not articles:
            log_message("Не найдено корректных артикулов для обработки.")
            start_button.disabled = False
            progress_bar.visible = False
            page.update()
            return
            
        max_s, max_w = int(max_server_slider.value), int(max_workers_slider.value)
        detailed_logging = detailed_log_switch.value

        if domain_dropdown.value == "Оба домена":
            host_options = ["https://basket-{server}.wbcontent.net", "https://basket-{server}.wbbasket.ru"]
        else:
            host_options = [f"https://basket-{{server}}.{domain_dropdown.value}"]

        if algo_dropdown.value == "desc": server_range = range(max_s, 0, -1)
        elif algo_dropdown.value == "asc": server_range = range(1, max_s + 1)
        else: server_range = random.sample(range(1, max_s + 1), max_s)

        for i, article in enumerate(articles):
            log_message(f"--- [ {i+1}/{len(articles)} ] Обработка артикула: {article} ---")
            image_urls = find_images_on_server(article, server_range, host_options, log_message, detailed_logging)
            if image_urls:
                log_message(f"Найдено изображений: {len(image_urls)}. Начинаю загрузку...")
                download_images_for_article(article, image_urls, max_w, update_progress, log_message)
            else:
                log_message(f"Артикул {article}: Изображения не найдены.")
            update_progress(0)
        
        log_message("--- Все задачи выполнены! ---")
        start_button.disabled = False
        progress_bar.visible = False
        page.update()

    start_button.on_click = start_download_thread

    settings_container = Container(
        padding=padding.all(15), border=border.all(1, Colors.OUTLINE), border_radius=8,
        content=Column([
            Text("Настройки", style="titleMedium"),
            Row([domain_dropdown, algo_dropdown], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            Text("Максимальный номер сервера для поиска:"), max_server_slider,
            Text("Количество потоков для одновременной загрузки:"), max_workers_slider,
            detailed_log_switch
        ])
    )
    
    page.add(
        Column([
            Text("WB Photo Downloader", style="headlineMedium"),
            Text("Введите артикулы или ссылки на товары Wildberries (до 10 шт. через запятую).", size=14, color=Colors.ON_SURFACE_VARIANT),
            Row([articles_field, start_button]),
            Divider(), settings_container, Divider(),
            Text("Лог выполнения", style="titleMedium"),
            progress_bar,
            Container(
                content=log_view, border=border.all(1, Colors.OUTLINE),
                border_radius=8, padding=padding.all(10), expand=True
            )
        ], expand=True, spacing=10)
    )

if __name__ == "__main__":
    ft.app(target=main)
