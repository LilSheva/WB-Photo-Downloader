# Этот скрипт проходит по указанной папке, заходит в каждую вложенную папку
# и переименовывает все файлы в них.
# Новое имя файла формируется из старого имени, к которому добавляется
# имя родительской папки перед расширением.
# Например, файл '1.webp' в папке 'folder_name' будет переименован в
# '1_folder_name.webp'.

import os

def rename_files_in_subfolders(main_folder_path):
    """
    Переименовывает файлы в каждой подпапке указанной основной папки.

    Аргументы:
    main_folder_path (str): Путь к основной папке, содержащей подпапки с файлами.
    """
    try:
        # Проверяем, существует ли указанный путь
        if not os.path.isdir(main_folder_path):
            print(f"Ошибка: Папка '{main_folder_path}' не найдена.")
            return

        # Использование os.walk() для обхода всех папок и файлов. [4, 10]
        for dirpath, dirnames, filenames in os.walk(main_folder_path):
            # Пропускаем саму основную папку, работаем только с вложенными
            if dirpath == main_folder_path:
                continue

            # Получаем имя текущей папки (родительской для файлов)
            folder_name = os.path.basename(dirpath)

            for filename in filenames:
                # Разделяем имя файла и его расширение. [2]
                file_base, file_extension = os.path.splitext(filename)

                # Формируем новое имя файла
                new_filename = f"{file_base}_{folder_name}{file_extension}"

                # Получаем полные пути к старому и новому файлам
                old_file_path = os.path.join(dirpath, filename)
                new_file_path = os.path.join(dirpath, new_filename)

                # Переименовываем файл. [3, 9]
                try:
                    os.rename(old_file_path, new_file_path)
                    print(f"Файл '{old_file_path}' переименован в '{new_file_path}'")
                except OSError as e:
                    print(f"Ошибка при переименовании файла '{old_file_path}': {e}")

    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")

# Укажите здесь путь к вашей основной папке
# Например, r'C:\Users\User\Desktop\МояПапка' для Windows
# или '/home/user/my_folder' для Linux
path_to_main_folder = 'images'

rename_files_in_subfolders(path_to_main_folder)
