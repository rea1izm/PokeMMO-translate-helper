import sqlite3
from PyQt5.QtWidgets import QApplication, QFileDialog
import re
from collections import defaultdict
import xml.etree.ElementTree as ET
from tqdm import tqdm
import os


def select_file():
    """ Выбрать файл с помощью проводника """
    app = QApplication([])
    file_path, _ = QFileDialog.getOpenFileName(None, 'Выбор файла', '', 'Files (*.xml)')
    return file_path


def creating_database():
    """ Создание базы данных """
    connection = sqlite3.connect('pokemmo_strings.db')
    cursor = connection.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS basic_strings (
        id TEXT,
        text_en TEXT,
        text_ru TEXT
    )
    ''')
    connection.commit()


def get_id(line):
    """ Возвращает id из строки <string> """
    pattern = '[0-9]+'
    match = re.findall(pattern, line)
    return match[0]


def get_text(line):
    """ Возвращает текст из строки <string> """
    pattern = r'>([^<]+)<'
    match = re.search(pattern, line).span()
    text = line[match[0] + 1:match[1] - 1]
    return text


def add_basic_strings():
    """ Добавляет в БД id и текст на английском языке """
    connection = sqlite3.connect('pokemmo_strings.db')
    cursor = connection.cursor()

    with open(select_file(), 'r', encoding='utf-8') as file:
        rows = file.readlines()
        for row in rows:
            try:
                index = get_id(row)
                text = get_text(row)

                cursor.execute("SELECT id FROM basic_strings WHERE id = ?", (index,))
                existing_record = cursor.fetchone()

                if not existing_record:
                    cursor.execute("INSERT INTO basic_strings (id, text_en) VALUES (?, ?)", (index, text))
            except:
                pass

    connection.commit()


def update_basic_strings():
    """ По id добавляет в БД текст на русском языке"""
    connection = sqlite3.connect('pokemmo_strings.db')
    cursor = connection.cursor()
    count = 0

    with open(select_file(), 'r', encoding='utf-8') as file:
        rows = file.readlines()
        for row in tqdm(rows):
            try:
                index = get_id(row)
                text = get_text(row)
                cursor.execute("UPDATE basic_strings SET text_ru = ? WHERE id = ?", (text, index))
                count += 1
            except:
                pass

        connection.commit()
        print(f'В базу данных загружено {count} строк.')


def update_tab_strings():
    """ Добавляет в БД текст на русском языке из табличного стринга """
    connection = sqlite3.connect('pokemmo_strings.db')
    cursor = connection.cursor()

    # Парсим xml файл
    tree = ET.parse(select_file())
    root = tree.getroot()
    archive_type = root.get('archive_type')
    region_id = root.get('region_id')
    count = 0

    for child in tqdm(root):
        entry_id = child.get('entry_id')
        table_id = child.get('table_id')
        text = child.text
        index = f'{archive_type}-{region_id}-{entry_id}-{table_id}'

        cursor.execute("UPDATE basic_strings SET text_ru = ? WHERE id = ?", (text, index))
        count += 1

    connection.commit()
    print(f'В базу данных загружено {count} строк.')


def add_tab_strings():
    """ Добавляет в БД данные табличного стринга на английском языке,
     учитывая регион и номер архива"""
    # Подключение к БД
    connection = sqlite3.connect('pokemmo_strings.db')
    cursor = connection.cursor()

    # Парсим xml файл
    tree = ET.parse(select_file())
    root = tree.getroot()
    archive_type = root.get('archive_type')
    region_id = root.get('region_id')
    count = 0

    for child in tqdm(root):
        entry_id = child.get('entry_id')
        table_id = child.get('table_id')
        text = child.text

        if not text:
            continue
        else:
            # Индекс для табличного стринга формируется в следующем формате
            index = f'{archive_type}-{region_id}-{entry_id}-{table_id}'
            try:
                cursor.execute("SELECT id FROM basic_strings WHERE id = ?", (index,))
                existing_record = cursor.fetchone()
                if not existing_record:
                    cursor.execute("INSERT INTO basic_strings (id, text_en) VALUES (?, ?)", (index, text))
                    count += 1
            except:
                pass

    connection.commit()
    print(f'В базу данных загружено {count} строк.')


def export_basic_string_to_translate():
    """ Выгрузить строки, которые требуют перевода """
    result = defaultdict(str)
    pattern = '  <string id="{}">{}</string>\n'
    with sqlite3.connect('pokemmo_strings.db') as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM basic_strings WHERE text_ru IS NULL")
        rows = cursor.fetchall()
        for row in rows:
            result[row[0]] = row[1]

    with open('strings to translate.xml', 'w', encoding='utf-8') as file:
        header = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n',
                  '<strings lang="rus" lang_full="Русский" is_primary="0">\n']
        footer = '</strings>'
        file.writelines(header)

        for k, v in result.items():
            file.write(pattern.format(k, f'{k} - {v}'))

        file.write(footer)


def create_new_string_ru():
    """Создает файлы с русским переводом"""
    # Папка для сохранения файлов
    output_folder = 'strings'
    # Создать папку, если она не существует
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Создание обычного стринга
    def create_basic_string(rows):
        pattern = '  <string id="{}">{}</string>\n'
        file_name = f'{output_folder}/rus_strings.xml'
        with open(file_name, 'w', encoding='utf-8') as file:
            header = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n',
                      '<strings lang="rus" lang_full="Русский" is_primary="0">\n']
            footer = '</strings>'
            file.writelines(header)

            for row in rows:
                index, text = row
                file.write(pattern.format(index, text))

            file.write(footer)

    # Создание табличного стринга
    def create_tab_string(region, rows):
        archive_type, region_id = region.split('-')
        file_name = f'{output_folder}/rus_tab_{archive_type}-{region_id}_strings.xml'
        pattern = '\t<string block_id="0" entry_id="{}" table_id="{}">{}</string>\n'
        header = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n',
                  f'<ds_strings_archive archive_type="{archive_type}" lang="rus" region_id="{region_id}">\n']
        footer = '</ds_strings_archive>'

        with open(file_name, 'w', encoding='utf-8') as file:
            file.writelines(header)
            for row in rows:
                entry_id, table_id = row[0].split('-')
                text = row[1]
                file.write(pattern.format(entry_id, table_id, text))
            file.write(footer)

    tab_rows = defaultdict(list)
    basic_rows = list()

    # Считывание всех строк, в которых заполнена колонка с русским текстом
    with sqlite3.connect('pokemmo_strings.db') as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM basic_strings WHERE text_ru IS NOT NULL")
        rows = cursor.fetchall()

        # Если обычный индекс, добавляем пару (индекс, текст) в отдельный список
        # Если индекс табличный, создаем словарь, где ключ это архив-регион, а значение - список строк этого региона
        for row in rows:
            index, _, text = row

            if '-' not in index:
                basic_rows.append((index, text))
            else:
                tab_reg = index[:3]
                tab_ind = index[4:]
                tab_rows[tab_reg].append((tab_ind, text))

    # Создание обычно русского стринга
    create_basic_string(basic_rows)

    # Перебор всех регионов из словаря tab_rows и создание по кадому региону своего стриг-файла на русском
    for k, v in tab_rows.items():
        create_tab_string(k, v)


creating_database()
commands = {'0': creating_database,
            '1': add_basic_strings,
            '2': add_tab_strings,
            '3': update_basic_strings,
            '4': update_tab_strings,
            '5': export_basic_string_to_translate,
            '6': create_new_string_ru}

print('Список команд:\n'
      '0. Создание базы данных\n'
      '1. Добавить английский текст в БД из обычного стринга\n'
      '2. Добавить английский текст в БД из табличного стринга\n'
      '- - - - - - - -\n'
      '3. Добавить русский текст в БД из обычного стринга\n'
      '4. Добавить русский текст в БД из таблично стринга\n'
      '- - - - - - - -\n'
      '5. Выгрузить строки, которые требуют перевода\n'
      '6. Создать файлы с переводом по всем регионам\n'
      '-----------------------------------------------------')
commands[input('Введи номер команды: ')]()
