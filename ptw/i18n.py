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
    "Welcome!\n\nPlease choose the folder where permits will be saved (Options > Settings).":
        "Добро пожаловать!\n\nВыберите папку, куда сохранять пермиты (Параметры > Настройки).",
    "Output folder is not set.": "Не выбрана папка для сохранения.",
    "Generates daily Permit to Work forms\nfrom the Word template with rotating jobs and crew.":
        "Создаёт ежедневные Permit to Work\nпо шаблону Word, чередуя работы и экипаж.",
    "Data folder:": "Папка с данными:",
    # permit form
    "Permit": "Пермит", "Date:": "Дата:", "Permit No:": "№ пермита:",
    "(empty = auto / blank)": "(пусто = авто / не заполнять)", "Job:": "Работа:",
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
    "History already has permits for some of these dates.\n\nYes - replace them in history\nNo - keep both":
        "В истории уже есть пермиты на некоторые из этих дат.\n\n"
        "Да — заменить их в истории\nНет — оставить оба",
    "Could not create files:": "Не удалось создать файлы:",
    "Could not create file:": "Не удалось создать файл:",
    "{n} files created in {folder}": "Создано файлов: {n} в {folder}",
    "{n} permits created.\n\nOpen the folder?": "Создано пермитов: {n}.\n\nОткрыть папку?",
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
    "Responsible ranks: one of them leads the job and closes the permit, e.g. 2E.\n"
    "Counts are 'min-max', e.g. 0-1 or 1-2. Ranks are comma separated: MM, FITTR.\n"
    "Keep Location / Plant / Work short - the form has one line for each.":
        "Ответственные ранги: один из них ведёт работу и закрывает пермит, например 2E.\n"
        "Количество пишется как «мин-макс», например 0-1 или 1-2. Ранги через запятую: MM, FITTR.\n"
        "Место / Оборудование / Работа пишите коротко: в форме по одной строке на каждое. "
        "Текст на английском — форма английская.",
    "Rank": "Ранг", "First name": "Имя", "Last name": "Фамилия",
    "Rank title (optional)": "Должность (необязательно)", "On board": "На борту",
    "Rank title overrides the rank name in signatures, e.g. 'Asst. Second Engineer'.\n"
    "Untick 'On board' when a crew member signs off - history is kept.":
        "Должность заменяет название ранга в подписях, например «Asst. Second Engineer».\n"
        "Снимите «На борту», когда член экипажа списывается — история сохранится.",
    "Code": "Код", "Short (issued to)": "Кратко (поле Issued to)",
    "Full (signatures)": "Полностью (подписи)",
    "Officer (can sign as P.C.)": "Офицер (может подписывать как P.C.)",
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
    "Number permits automatically": "Нумеровать пермиты автоматически",
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
