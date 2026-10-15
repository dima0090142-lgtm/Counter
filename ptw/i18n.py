"""Interface languages. English text is the key; RU holds the Russian translation.

The permit itself is always filled in English (the form is English)."""

LANGUAGES = {"en": "English", "ru": "Русский"}
_lang = "en"

RU = {
    # main window
    "Permit to Work Generator": "Генератор Permit to Work",
    "Daily Permit to Work, Engine Department": "Ежедневный Permit to Work, машинная команда",
    "File": "Файл", "Data": "Данные", "Options": "Параметры", "Help": "Справка",
    "Open output folder": "Открыть папку с пермитами", "Exit": "Выход",
    "Jobs...": "Работы...", "Crew...": "Экипаж...", "Ranks...": "Ранги...",
    "Settings...": "Настройки...", "About": "О программе",
    "Auto generate": "Автогенерация", "Manual": "Вручную", "History": "История",
    "Ready. Choose the period and press 'Generate'.":
        "Готово. Выберите период и нажмите «Сгенерировать».",
    "Output folder is not set.": "Не выбрана папка для сохранения.",
    "Generates daily Permit to Work forms\nfrom the Word template with rotating jobs and crew.":
        "Создаёт ежедневные Permit to Work\nпо шаблону Word, чередуя работы и экипаж.",
    "Data folder:": "Папка с данными:",
    # permit form
    "Permit": "Пермит", "Date:": "Дата:", "Permit No:": "№ пермита:",
    "Job:": "Работа:",
    "Location": "Место", "Plant": "Оборудование", "Work": "Работа",
    "Risk Assessment": "Risk Assessment",
    "Crew taking part": "Участники", "Auto-pick crew": "Подобрать экипаж",
    "Signatures": "Подписи",
    "5) P.C. (accepts permit):": "5) P.C. (принимает пермит):",
    "6) Transferred to:": "6) Передан:",
    "7) P.C. (closes permit):": "7) P.C. (закрывает пермит):",
    "(not set)": "(не выбран)",
    "Select a job first.": "Сначала выберите работу.",
    "Select a job.": "Выберите работу.",
    "Select at least one crew member.": "Отметьте хотя бы одного участника.",
    "Edit permit": "Изменить пермит",
    "OK": "OK", "Cancel": "Отмена", "Apply": "Применить",
    "Text is long and will be printed smaller ({size} pt):":
        "Текст длинный и будет напечатан мельче ({size} pt):",
    "Text is too long for one line even at {size} pt:":
        "Текст не помещается в одну строку даже шрифтом {size} pt:",
    # auto tab
    "From": "С", "To": "По", "days": "дн.",
    "Generate": "Сгенерировать", "Reroll": "Заменить", "Edit...": "Изменить...",
    "Remove": "Удалить", "Create files": "Создать файлы", "Plan": "План",
    "Date": "Дата", "Job": "Работа", "RA No": "№ RA", "Issued to": "Выдан",
    "P.C. (5)": "P.C. (5)", "Transfer (6)": "Передача (6)", "Close (7)": "Закрыл (7)",
    "'To' date is before 'From' date.": "Дата «По» раньше даты «С».",
    "Period is longer than one year.": "Период больше года.",
    "{n} permits planned. Check the list, then press 'Create files'.":
        "Запланировано пермитов: {n}. Проверьте список и нажмите «Создать файлы».",
    "Select permits in the list to reroll.": "Выделите в списке пермиты для замены.",
    "Nothing to create. Press 'Generate' first.": "Нечего создавать. Сначала нажмите «Сгенерировать».",
    "History already has permits for some of these dates.\n\n"
    "Yes - replace them (old files and history entries are removed)\nNo - keep both":
        "В истории уже есть пермиты на некоторые из этих дат.\n\n"
        "Да — заменить их (старые файлы и записи истории удаляются)\nНет — оставить оба",
    "Could not create files:": "Не удалось создать файлы:",
    "Could not create file:": "Не удалось создать файл:",
    "{n} files created in {folder}": "Создано файлов: {n} в {folder}",
    "Some values were too long even in the smallest font and were shortened (…) "
    "to keep the permit on one page:":
        "Некоторые значения не уместились даже самым мелким шрифтом и были сокращены (…), "
        "чтобы пермит остался на одной странице:",
    "No days in the period (check 'Days without permits' in Settings).":
        "В периоде нет рабочих дней (проверьте «Дни без пермитов» в настройках).",
    # manual tab
    "Create file": "Создать файл", "Created {name}": "Создан {name}",
    "Created:\n{name}\n\nOpen it now?": "Создан:\n{name}\n\nОткрыть его?",
    # history
    "No.": "№", "Yes": "Да", "No": "Нет", "Open file": "Открыть файл", "Open folder": "Открыть папку",
    "Delete entry": "Удалить запись",
    "History is used to keep jobs and crew different from day to day.":
        "История нужна, чтобы работы и экипаж менялись день ото дня.",
    "File not found:": "Файл не найден:",
    "Delete {n} entries from history?\n(Files are not deleted.)":
        "Удалить записей из истории: {n}?\n(Файлы не удаляются.)",
    "History: {n} permits": "История: {n} пермитов",
    # editors
    "Records": "Записи", "Details": "Подробно", "New": "Новая", "Copy": "Копия",
    "Delete": "Удалить", "Delete this record?": "Удалить эту запись?",
    "Jobs": "Работы", "Crew": "Экипаж", "Ranks": "Ранги",
    "'{key}' must be a number": "«{key}» должно быть числом",
    "'{key}' must look like 0-2": "«{key}» должно быть вида 0-2",
    "Code must not be empty.": "Код не может быть пустым.",
    "ID": "ID", "Title (file name)": "Название (имя файла)",
    "Plant / Equipment": "Оборудование", "Work to be done": "Описание работы",
    "Risk Assessment No": "№ Risk Assessment", "Responsible ranks": "Ответственные ранги",
    "Extra officers ranks": "Ранги доп. офицеров", "Extra officers count": "Кол-во доп. офицеров",
    "Ratings ranks": "Ранги рядовых", "Ratings count": "Кол-во рядовых", "Active": "Активна",
    "Rank": "Ранг", "First name": "Имя", "Last name": "Фамилия",
    "Rank title (optional)": "Должность (необязательно)", "On board": "На борту",
    "Rank title overrides the rank name in signatures, e.g. 'Asst. Second Engineer'.\n"
    "Untick 'On board' when a crew member signs off - history is kept.":
        "Должность заменяет название ранга в подписях, например «Asst. Second Engineer».\n"
        "Снимите «На борту», когда член экипажа списывается — история сохранится.",
    "Code": "Код", "Short (issued to)": "Кратко (поле Issued to)",
    "Full (signatures)": "Полностью (подписи)",
    "Order (seniority)": "Порядок (старшинство)",
    "(off)": "(списан)",
    # settings
    "Settings": "Настройки", "General": "Общие", "Files": "Файлы", "Generation": "Генерация",
    "Print": "Печать",
    "Language:": "Язык:", "Interface font size:": "Размер шрифта интерфейса:",
    "Ship name:": "Название судна:", "A.O. (Authorizing Officer):": "A.O. (Authorizing Officer):",
    "Output folder:": "Папка для пермитов:", "Word template:": "Шаблон Word:",
    "Browse...": "Обзор...", "(empty = built-in template)": "(пусто = встроенный шаблон)",
    "File name pattern:": "Шаблон имени файла:", "Date format in file name:": "Формат даты в имени:",
    "Fields: {date} {title} {ra} {no}.  Date: %Y-%m-%d, %d.%m.%Y ...":
        "Поля: {date} {title} {ra} {no}.  Дата: %Y-%m-%d, %d.%m.%Y ...",
    "Open the folder after creating files": "Открывать папку после создания файлов",
    "Example:": "Пример:",
    "Time permit issued (5):": "Время выдачи (5):", "Time of transfer (6):": "Время передачи (6):",
    "Time permit closed (7):": "Время закрытия (7):",
    "Next permit number:": "Следующий номер:",
    "Permits per day:": "Пермитов в день:",
    "Do not repeat a job within (days):": "Не повторять работу (дней):",
    "Days without permits:": "Дни без пермитов:",
    "Mon": "Пн", "Tue": "Вт", "Wed": "Ср", "Thu": "Чт", "Fri": "Пт", "Sat": "Сб", "Sun": "Вс",
    "Fit long text on one line (smaller font)": "Уменьшать шрифт длинного текста, чтобы он влез в строку",
    "Smallest font size, pt:": "Минимальный размер шрифта, pt:",
    "The form must stay on one A4 page. Values are printed in Times New Roman 9 pt;\n"
    "a value that does not fit its line is printed smaller instead of wrapping.":
        "Форма должна умещаться на одном листе A4. Значения печатаются Times New Roman 9 pt;\n"
        "если значение не помещается в строку, оно печатается мельче, а не переносится.",
    "Defaults": "По умолчанию",
    "Play sounds": "Звуки", "Test": "Проверить",
    "Show the splash screen at start": "Показывать заставку при запуске",
    "Generator  -  Engine Department": "Генератор  -  машинная команда",
    "Version {v}": "Версия {v}",
    "Loading settings...": "Загрузка настроек...", "Loading crew list...": "Загрузка экипажа...",
    "Loading jobs...": "Загрузка списка работ...",
    "Checking Word template...": "Проверка шаблона Word...", "Starting...": "Запуск...",
    "Reset all settings to defaults (folders are kept)?":
        "Сбросить все настройки по умолчанию (папки сохранятся)?",
    "Numbers expected for per day / repeat / permit no.":
        "В полях «в день», «не повторять», «номер» должны быть числа.",
    "Time must look like 08:00 ({key}).": "Время должно быть вида 08:00 ({key}).",
    "Wrong file name pattern: {e}": "Неверный шаблон имени файла: {e}",
    "Smallest font size must be a number between 5 and 9.":
        "Минимальный размер шрифта — число от 5 до 9.",
    "Template not found: {path}": "Шаблон не найден: {path}",
    # version 1.3
    "(empty = automatic)": "(пусто = автоматически)",
    "P.C. can be: {ranks}": "P.C. может быть: {ranks}",
    "4) LOTO procedure, Rank/Name (A.O.):": "4) LOTO, Rank/Name (A.O.):",
    "yes": "да", "no": "нет", "LOTO": "LOTO",
    "Nobody in the team can sign as P.C. Add one of: {ranks}.":
        "В команде нет никого, кто может быть P.C. Добавьте одного из: {ranks}.",
    "Choose the P.C. for sections 5 and 7.": "Выберите P.C. для разделов 5 и 7.",
    "Choose who applies LOTO, or untick LOTO.": "Выберите, кто ставит LOTO, или снимите галочку LOTO.",
    "Consecutive Permit No:": "Consecutive Permit No:",
    "Day of the year: 285, or 285-1, 285-2 for several a day":
        "По дню года: 285, а если пермитов за день несколько — 285-1, 285-2",
    "Running number (next number below)": "Сквозной номер (следующий номер ниже)",
    "Leave empty (written by pen)": "Не заполнять (вписать ручкой)",
    "Sections 2 and 3, tick the boxes in the file:": "Разделы 2 и 3, ставить галочки в файле:",
    "P.C. when the job lead cannot be P.C. (take turns):":
        "P.C., если ответственный не может быть P.C. (по очереди):",
    "LOTO is applied first of all by:": "LOTO в первую очередь ставит:",
    "Who may be P.C. or apply LOTO is set per rank in Data > Ranks.":
        "Кто может быть P.C. и ставить LOTO, задаётся у рангов: Данные > Ранги.",
    "Load default jobs list...": "Загрузить стандартный список работ...",
    "Welcome!\n\nPlease enter the ship name and choose the folder where permits will be saved "
    "(Options > Settings).":
        "Добро пожаловать!\n\nВведите название судна и выберите папку, куда сохранять пермиты "
        "(Параметры > Настройки).",
    "P.C. ranks (if the lead cannot be P.C.)": "Ранги P.C. (если ответственный не P.C.)",
    "LOTO usually needed (hint only)": "Обычно нужен LOTO (только подсказка)",
    "LOTO usually needed: {answer}": "Обычно нужен LOTO: {answer}",
    "Responsible ranks: one of them leads the job, e.g. 2E. If the lead cannot be P.C.\n"
    "(4E, 5E), a P.C. from 'P.C. ranks' is added - empty = Settings > Generation.\n"
    "Counts are 'min-max', e.g. 0-1 or 1-2. Ranks are comma separated: MM, FITTR.\n"
    "Keep Location / Plant / Work short - the form has one line for each.":
        "Ответственные ранги: один из них ведёт работу, например 2E. Если он не может быть P.C.\n"
        "(4E, 5E), добавляется P.C. из «Ранги P.C.»; пусто = Настройки > Генерация.\n"
        "Количество пишется как «мин-макс», например 0-1 или 1-2. Ранги через запятую: MM, FITTR.\n"
        "Место / Оборудование / Работа пишите коротко: в форме по одной строке на каждое. "
        "Текст на английском — форма английская.",
    "Officer": "Офицер",
    "Can sign as P.C. (sections 5-7)": "Может быть P.C. (разделы 5-7)",
    "Can apply LOTO": "Может ставить LOTO",
    "Default list: {n} jobs.\n\nYes - replace your list with it\nNo - only add the jobs you do not have yet":
        "В стандартном списке работ: {n}.\n\nДа — заменить ваш список стандартным\n"
        "Нет — только добавить работы, которых у вас нет",
    "Jobs list updated: {n} jobs ({added} new).": "Список работ обновлён: {n} работ ({added} новых).",
    "Recreate file": "Пересоздать файл",
    "Filter:": "Фильтр:", "{n} of {total}": "{n} из {total}",
    "(title, equipment, location, rank or RA No)": "(название, оборудование, место, ранг или № RA)",
    "Print (test)": "Печать (тест)", "Print selected files (test)": "Печать выделенных файлов (тест)",
    "Printing is not available on this computer.": "Печать на этом компьютере недоступна.",
    "Print {n} files on the default printer?\n(test function: Word opens and prints each file)":
        "Напечатать файлов: {n} на принтере по умолчанию?\n(тестовая функция: Word откроет и напечатает каждый файл)",
    "{n} files sent to the printer": "Отправлено на печать файлов: {n}",
    "Keyboard shortcuts": "Горячие клавиши",
    "Ctrl+A - select all (lists, text fields)\n"
    "Ctrl+C / Ctrl+V / Ctrl+X - copy / paste / cut (lists: rows for Excel)\n"
    "Right mouse button - Copy / Paste menu\n"
    "Shift / Ctrl + click - select several rows\n"
    "F5 or Ctrl+G - generate the plan\n"
    "Ctrl+R - reroll selected rows\n"
    "Enter, F2 or Ctrl+E - edit the selected row\n"
    "Delete - remove the selected rows\n"
    "Ctrl+S - create files (Auto) / create file (Manual)\n"
    "Ctrl+F - job filter (Manual) / filter in the editors\n"
    "Ctrl+N - new record (editors), Ctrl+S - OK (editors)\n"
    "Ctrl+P - print selected files (History, test)\n"
    "Ctrl+O - open the output folder\n"
    "Ctrl+1 / 2 / 3 - Auto generate / Manual / History\n"
    "Ctrl+Q - exit":
        "Ctrl+A — выделить всё (списки, поля ввода)\n"
        "Ctrl+C / Ctrl+V / Ctrl+X — копировать / вставить / вырезать (в списках — строки для Excel)\n"
        "Правая кнопка мыши — меню «Копировать / Вставить»\n"
        "Shift / Ctrl + щелчок — выделить несколько строк\n"
        "F5 или Ctrl+G — сгенерировать план\n"
        "Ctrl+R — заменить выделенные строки\n"
        "Enter, F2 или Ctrl+E — изменить выделенную строку\n"
        "Delete — удалить выделенные строки\n"
        "Ctrl+S — создать файлы (Авто) / создать файл (Вручную)\n"
        "Ctrl+F — фильтр работ (Вручную) / фильтр в редакторах\n"
        "Ctrl+N — новая запись (редакторы), Ctrl+S — OK (редакторы)\n"
        "Ctrl+P — печать выделенных файлов (История, тест)\n"
        "Ctrl+O — открыть папку с пермитами\n"
        "Ctrl+1 / 2 / 3 — Автогенерация / Вручную / История\n"
        "Ctrl+Q — выход\n\nКлавиши работают и в русской раскладке.",
    "Name": "Имя", "All": "Все", "None": "Никого",
    "(a job and crew for the date - like Auto generate)":
        "(работа и экипаж на выбранную дату — как в автогенерации)",
    "No job can be planned (check the jobs and crew).":
        "Не удалось подобрать работу (проверьте список работ и экипаж).",
    "Creating permit files...": "Создание файлов пермитов...",
    "Cancelled: {n} of {total} files created": "Отменено: создано файлов {n} из {total}",
    "Cut": "Вырезать", "Copy (clipboard)": "Копировать", "Paste": "Вставить",
    "Select all": "Выделить всё", "Log files:": "Журнал ошибок:",
    "Check for updates": "Проверить обновления", "Open log folder": "Открыть папку журнала",
    "Could not check for updates:\n{e}": "Не удалось проверить обновления:\n{e}",
    "You have the latest version ({v}).": "У вас последняя версия ({v}).",
    "Version {new} is available (you have {v}).\nOpen the download page?":
        "Доступна версия {new} (у вас {v}).\nОткрыть страницу загрузки?",
    "Version {new} is available (you have {v}).\n\nDownload it and restart the program now?\n"
    "Your data, templates and history are kept.":
        "Доступна версия {new} (у вас {v}).\n\nСкачать и перезапустить программу?\n"
        "Ваши данные, шаблоны и история сохранятся.",
    "Downloading version {new}...": "Загрузка версии {new}...",
    "An error occurred:\n{e}\n\nDetails are in the log:\n{path}":
        "Произошла ошибка:\n{e}\n\nПодробности в журнале:\n{path}",
    "Select permits in the list.": "Выделите пермиты в списке.",
    "Write {n} files again with the same numbers?\nThe old files are overwritten.":
        "Записать заново файлов: {n}, с теми же номерами?\nСтарые файлы будут перезаписаны.",
    "These plan rows cannot be printed (selected in the list). Use Reroll or Edit...:":
        "Эти строки плана нельзя печатать (выделены в списке). Нажмите «Заменить» или «Изменить...»:",
    "'P.C. when the job lead cannot be P.C.' needs ranks that may be P.C.: {ok}":
        "В поле «P.C., если ответственный не может быть P.C.» нужны ранги, которые могут быть P.C.: {ok}",
    "Unknown rank: {codes}": "Неизвестный ранг: {codes}",
    "Group (same filter / purifier: not on close days)":
        "Группа (тот же фильтр / сепаратор: не в соседние дни)",
    "The Word template has no fields for: {fields}.\n{path}\n\nThese values will not be printed. "
    "Use the built-in template (Options > Settings > Files, Word template empty).\n\n"
    "Create the files anyway?":
        "В шаблоне Word нет полей: {fields}.\n{path}\n\nЭти значения не будут напечатаны. "
        "Используйте встроенный шаблон (Параметры > Настройки > Файлы, поле «Шаблон Word» пустое)."
        "\n\nВсё равно создать файлы?",
}


def set_language(lang):
    global _lang
    _lang = lang if lang in LANGUAGES else "en"


def language():
    return _lang


def T(text, **kw):
    """Translate text to the current language and fill {placeholders}."""
    if _lang == "ru":
        text = RU.get(text, text)
    return text.format(**kw) if kw else text
