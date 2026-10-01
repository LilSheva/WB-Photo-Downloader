"""Поиск и загрузка фото товара WB по артикулу — без интерфейса и без сторонних пакетов (app.py и консоль).

Фото лежат по адресу <хост>/vol<артикул без 5 последних цифр>/part<без 3 последних>/<артикул>/images/big/<N>.webp.
Номер сервера заранее неизвестен, поэтому перебираем хосты параллельно. С 2026 года новые карточки
отдаются и с mow-basket-cdn-NN.geobasket.ru, а номера серверов выросли за 30.

Консоль:  python wb_photos.py 187565553 https://www.wildberries.ru/catalog/569813064/detail.aspx --out images
"""

from __future__ import annotations

import argparse
import concurrent.futures
import os
import re
import urllib.error
import urllib.request

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}
HOSTS = {
    "wbbasket.ru": "https://basket-{server}.wbbasket.ru",
    "wbcontent.net": "https://basket-{server}.wbcontent.net",
    "geobasket.ru": "https://mow-basket-cdn-{server}.geobasket.ru",
}
MAX_IMAGES = 50


def parse_wb_input(text: str) -> str | None:
    text = text.strip()
    if text.isdigit():
        return text
    match = re.search(r"catalog/(\d+)/", text)
    return match.group(1) if match else None


def image_url(host: str, article: str, n: int) -> str:
    return f"{host}/vol{article[:-5]}/part{article[:-3]}/{article}/images/big/{n}.webp"


def _alive(url: str) -> bool:
    try:
        req = urllib.request.Request(url, headers=HEADERS, method="HEAD")
        with urllib.request.urlopen(req, timeout=4) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=20) as resp:
        return resp.read()


def find_host(article: str, servers=range(1, 101), hosts=tuple(HOSTS.values()), workers: int = 24,
              exclude=frozenset(), log=print) -> str | None:
    """Первый хост, у которого есть фото №1. Перебор параллельный, после находки остальные проверки снимаются."""
    candidates = [h.format(server=f"{s:02d}") for s in servers for h in hosts]
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
    try:
        futures = {pool.submit(_alive, image_url(h, article, 1)): h for h in candidates if h not in exclude}
        for future in concurrent.futures.as_completed(futures):
            if future.result():
                return futures[future]
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    log(f"Артикул {article}: фото не найдены ни на одном хосте")
    return None


def list_images(host: str, article: str) -> list[str]:
    urls = []
    for n in range(1, MAX_IMAGES + 1):
        url = image_url(host, article, n)
        if not _alive(url):
            break
        urls.append(url)
    return urls


def download(article: str, out_dir: str = "images", workers: int = 5, log=print, progress=None, **find_kw) -> list[str]:
    tried: set[str] = set()
    urls: list[str] = []
    while not urls and len(tried) < 3:  # бывает, что CDN ответил на №1, а дальше пусто — берём следующий хост
        host = find_host(article, exclude=frozenset(tried), log=log, **find_kw)
        if not host:
            return []
        tried.add(host)
        urls = list_images(host, article)
    log(f"Артикул {article}: {host.split('/')[2]}, фото: {len(urls)}")
    save_dir = os.path.join(out_dir, article)
    os.makedirs(save_dir, exist_ok=True)
    done, paths = 0, []

    def fetch(i_url):
        i, url = i_url
        path = os.path.join(save_dir, f"{i}.webp")
        with open(path, "wb") as fh:
            fh.write(_get(url))
        return path

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for future in concurrent.futures.as_completed([pool.submit(fetch, x) for x in enumerate(urls, start=1)]):
            try:
                paths.append(future.result())
            except (urllib.error.URLError, OSError) as exc:
                log(f"  [Ошибка] {exc}")
            done += 1
            if progress:
                progress(done / len(urls))
    log(f"Артикул {article}: готово, папка {os.path.abspath(save_dir)}")
    return sorted(paths)


def main() -> None:
    parser = argparse.ArgumentParser(description="Скачать фото товаров WB по артикулам или ссылкам")
    parser.add_argument("articles", nargs="+")
    parser.add_argument("--out", default="images")
    parser.add_argument("--max-server", type=int, default=100)
    args = parser.parse_args()
    for raw in args.articles:
        article = parse_wb_input(raw)
        if article:
            download(article, args.out, servers=range(1, args.max_server + 1))
        else:
            print(f"Не похоже на артикул или ссылку WB: {raw}")


if __name__ == "__main__":
    main()
