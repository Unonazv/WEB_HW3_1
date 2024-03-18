import sys
import shutil
import re
from pathlib import Path
import threading

UKRAINIAN_SYMBOLS = 'абвгдеєжзиіїйклмнопрстуфхцчшщьюя'
TRANSLATION = ("a", "b", "v", "g", "d", "e", "je", "zh", "z", "y", "i", "ji", "j", "k", "l", "m", "n", "o", "p", "r", "s", "t", "u",
               "f", "h", "ts", "ch", "sh", "sch", "", "ju", "ja")
TRANS = {}  # таблица сопоставления для транслитерации 

image_files = list()  # списки для отсортированных по расширению файлов
video_files = list()
docx_files = list()
audio_files = list()
archives = list()
others = list()
folders = list()   #  для хранения  папок
unknown = set() # множество НЕизвестных расширений
extensions = set() # множество известных расширений

registered_extensions = {    # словарь для сортировки файлов по расширению
    'JPEG': image_files,
    'PNG': image_files,
    'JPG': image_files,
    'SVG': image_files,
    'AVI': video_files,
    'MP4': video_files,
    'MOV': video_files,
    'MKV': video_files,
    'DOC': docx_files,
    'DOCX': docx_files,
    'TXT': docx_files,
    'PDF': docx_files,
    'XLSX': docx_files,
    'PPTX': docx_files,
    'MP3': audio_files,
    'OGG': audio_files,
    'WAV': audio_files,
    'AMR': audio_files,
    'ZIP': archives,
    'GZ': archives,
    'TAR': archives
}

for key, value in zip(UKRAINIAN_SYMBOLS, TRANSLATION):
    TRANS[ord(key)] = value  # для нижнего регистра
    TRANS[ord(key.upper())] = value.upper() # для верхнего регистра

def normalize(name: str) -> str:
    name, *extension = name.split('.')
    new_name = name.translate(TRANS)
    new_name = re.sub(r'\W', '_', new_name) # ругулярные выражения \W- все что НЕ буква, цифра, нижнее подчеркивание заменяется на "_"
    return f"{new_name}.{'.'.join(extension)}"

def get_extensions(file_name):   # функция для выделения расширения файла    ??? suffix
    return Path(file_name).suffix[1:].upper()   # перевод в верхний регистр чтобы сопоставить со словарем registered_extensions

def scan(folder):
    for item in folder.iterdir():
        if item.is_dir():   
            if item.name not in ('images', 'video', 'documents', 'audio', 'archives', 'other'): # если объект папка, которая подлежит сортировке
                folders.append(item) # добавляется адрес папки в список folders
                scan(item) # переход наслед уровень сканирования
            continue
        extension = get_extensions(file_name=item.name)   # если объект не директория ,т.е. файл - извлекается расширение
        new_name = folder/item.name
        if not extension:    # для файлов без раширения типа _pycach_
            others.append(new_name)
        else:
            try:
                container = registered_extensions[extension]  # список зарегистрированных расширений, которые были в отсканированной папке  
                extensions.add(extension)  # пополнение множества известных расширений
                container.append(new_name)  # пополнение списка файлов с зарегистрированным расширением
            except KeyError:  # обработка для случая отсутствия ключа(расширения)  в словаре registered_extensions
                unknown.add(extension)  # пополнение множества НЕизвестных расширений
                others.append(new_name)

def handle_file(path, root_folder, dist):  # начальный путь к папке; стартовый каталог; назначение, куда переместить.
    target_folder = root_folder/dist  # путь для создания одного из каталогов с отсортированными файлами
    target_folder.mkdir(exist_ok=True) # непосредствено создание каталога (если такого нет)
    path.replace(target_folder/normalize(path.name)) # перенос файла в целевой каталог с нормализацией названия

def handle_archive(path, root_folder, dist):
    target_folder = root_folder / dist
    target_folder.mkdir(exist_ok=True)
    new_name = normalize(path.name.replace(".zip", '').replace(".gz", '').replace(".tar", '')) # имя каталога, куда будет распаковываться архив
    archive_folder = target_folder / new_name
    archive_folder.mkdir(exist_ok=True)
    try:
        shutil.unpack_archive(str(path.resolve()), str(archive_folder.resolve()))
    except shutil.ReadError:
        archive_folder.rmdir()
        return
    except FileNotFoundError:
        archive_folder.rmdir()
        return
    path.unlink()

def remove_empty_folders(path):
    for item in path.iterdir():
        if item.is_dir():
            remove_empty_folders(item)
            try:
                item.rmdir()
            except OSError:
                pass

def main(folder_path):
    print(folder_path)
    scan(folder_path)

    threads = []
    
    # Для каждого типа файла запускаем отдельный поток обработки
    for file in image_files:
        thread = threading.Thread(target=handle_file, args=(file, folder_path, "images"))
        thread.start()
        threads.append(thread)
        
    for file in video_files:
        thread = threading.Thread(target=handle_file, args=(file, folder_path, "video"))
        thread.start()
        threads.append(thread)
        
    for file in docx_files:
        thread = threading.Thread(target=handle_file, args=(file, folder_path, "documents"))
        thread.start()
        threads.append(thread)
        
    for file in audio_files:
        thread = threading.Thread(target=handle_file, args=(file, folder_path, "audio"))
        thread.start()
        threads.append(thread)
        
    for file in archives:
        thread = threading.Thread(target=handle_archive, args=(file, folder_path, "archives"))
        thread.start()
        threads.append(thread)
        
    for file in others:
        thread = threading.Thread(target=handle_file, args=(file, folder_path, "other"))
        thread.start()
        threads.append(thread)
        
    # Дожидаемся завершения всех потоков
    for thread in threads:
        thread.join()

    remove_empty_folders(folder_path)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python main.py <folder_path>")
        sys.exit(1)
    path = sys.argv[1]
    print(f'Start in {path}')
    folder = Path(path)
    main(folder.resolve())
    print(f"images: {image_files}")
    print(f"video: {video_files}")
    print(f"documents: {docx_files}")
    print(f"audio: {audio_files}")
    print(f"archives: {archives}")
    print(f"other: {others}")
    print(f"Noun extensions: {extensions}")
    print(f"Unknown extensions: {unknown}")
