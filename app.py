import random
import threading
import flet as ft
from flet import (
    Column, Row, Text, TextField, Dropdown, dropdown, Slider, ElevatedButton,
    ProgressBar, ListView, Divider, Container, padding, alignment, border, Icons, Colors, Switch
)

import wb_photos
from wb_photos import parse_wb_input

def main(page: ft.Page):
    page.title = "WB Photo Downloader"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.window_width = 700
    page.window_height = 800
    page.theme_mode = ft.ThemeMode.DARK

    articles_field = TextField(label="Артикулы или ссылки через запятую", hint_text="271516033, 271515437...", expand=True)
    start_button = ElevatedButton(text="Начать скачивание", icon=Icons.DOWNLOAD, height=40)
    
    domain_dropdown = Dropdown(label="Домен для поиска", value="Все домены", options=[
        dropdown.Option("Все домены", "Все домены (рекомендуется)"),
        dropdown.Option("wbcontent.net", "basket-xx.wbcontent.net"),
        dropdown.Option("wbbasket.ru", "basket-xx.wbbasket.ru"),
        dropdown.Option("geobasket.ru", "mow-basket-cdn-xx.geobasket.ru"),
    ])
    
    algo_dropdown = Dropdown(label="Алгоритм обхода серверов", value="desc", options=[
        dropdown.Option("desc", "От большего к меньшему (Рекомендуется)"),
        dropdown.Option("asc", "От меньшего к большему"),
        dropdown.Option("random", "Случайный порядок"),
    ])
    
    max_server_slider = Slider(min=10, max=150, divisions=14, value=100, label="Макс. сервер: {value}")
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

        if domain_dropdown.value == "Все домены":
            host_options = tuple(wb_photos.HOSTS.values())
        else:
            host_options = (wb_photos.HOSTS[domain_dropdown.value],)

        if algo_dropdown.value == "desc": server_range = range(max_s, 0, -1)
        elif algo_dropdown.value == "asc": server_range = range(1, max_s + 1)
        else: server_range = random.sample(range(1, max_s + 1), max_s)

        for i, article in enumerate(articles):
            log_message(f"--- [ {i+1}/{len(articles)} ] Обработка артикула: {article} ---")
            wb_photos.download(article, "images", workers=max_w, log=log_message, progress=update_progress,
                               servers=server_range, hosts=host_options)
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
