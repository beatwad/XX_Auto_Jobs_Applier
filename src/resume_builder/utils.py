import os
import platform
import time

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager


def create_driver_selenium():
    """Создание Selenium driver"""
    options = chrome_browser_options()

    chrome_install = ChromeDriverManager().install()
    folder = os.path.dirname(chrome_install)
    if platform.system() == "Windows":
        chromedriver_path = os.path.join(folder, "chromedriver.exe")
    else:
        chromedriver_path = os.path.join(folder, "chromedriver")
    service = ChromeService(executable_path=chromedriver_path)
    return webdriver.Chrome(service=service, options=options)


def HTML_to_PDF(FilePath):
    """Проверка и подготовка пути к файлу"""
    if not os.path.isfile(FilePath):
        raise FileNotFoundError(f"Файл не найден: {FilePath}")
    FilePath = f"file:///{os.path.abspath(FilePath).replace(os.sep, '/')}"
    driver = create_driver_selenium()

    try:
        driver.get(FilePath)
        time.sleep(2)
        pdf_base64 = driver.execute_cdp_cmd(
            "Page.printToPDF",
            {
                "printBackground": True,  # Включить фон при печати
                "landscape": False,  # Печатать в вертикальной ориентации (False для портретной ориентации)
                "paperWidth": 8.27,  # Ширина листа в дюймах (A4)
                "paperHeight": 11.69,  # Высота листа в дюймах (A4)
                "marginTop": 0.8,  # Верхнее поле в дюймах
                "marginBottom": 0.8,  # Нижнее поле в дюймах
                "marginLeft": 0.5,  # Левое поле в дюймах
                "marginRight": 0.5,  # Правое поле в дюймах
                "displayHeaderFooter": False,  # Не отображать заголовки и нижние колонтитулы
                "preferCSSPageSize": True,  # Использовать размеры страницы из CSS
                "generateDocumentOutline": False,  # Не генерировать оглавление документа
                "generateTaggedPDF": False,  # Не генерировать тэгированный PDF
                "transferMode": "ReturnAsBase64",  # Вернуть PDF в виде строки base64
            },
        )
        return pdf_base64["data"]
    except WebDriverException as e:
        raise RuntimeError(f"Ошибка при работе WebDriver: {e}")
    finally:
        driver.quit()


def chrome_browser_options():
    """Задать настройки браузера Chrome, в котором будет работать Selenium"""
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")  # Avvia il browser a schermo intero
    options.add_argument("--no-sandbox")  # Disabilita la sandboxing per migliorare le prestazioni
    options.add_argument(
        "--disable-dev-shm-usage"
    )  # Utilizza una directory temporanea per la memoria condivisa
    options.add_argument("--ignore-certificate-errors")  # Ignora gli errori dei certificati SSL
    options.add_argument("--disable-extensions")  # Disabilita le estensioni del browser
    options.add_argument("--disable-gpu")  # Disabilita l'accelerazione GPU
    options.add_argument("window-size=1200x800")  # Imposta la dimensione della finestra del browser
    options.add_argument(
        "--disable-background-timer-throttling"
    )  # Disabilita il throttling dei timer in background
    options.add_argument(
        "--disable-backgrounding-occluded-windows"
    )  # Disabilita la sospensione delle finestre occluse
    options.add_argument("--disable-translate")  # Disabilita il traduttore automatico
    options.add_argument("--disable-popup-blocking")  # Disabilita il blocco dei popup
    # options.add_argument("--disable-features=VizDisplayCompositor")  # Disabilita il compositore di visualizzazione
    options.add_argument("--no-first-run")  # Disabilita la configurazione iniziale del browser
    options.add_argument(
        "--no-default-browser-check"
    )  # Disabilita il controllo del browser predefinito
    options.add_argument("--single-process")  # Esegui Chrome in un solo processo
    options.add_argument("--disable-logging")  # Disabilita il logging
    options.add_argument("--disable-autofill")  # Disabilita l'autocompletamento dei moduli
    # options.add_argument("--disable-software-rasterizer")  # Disabilita la rasterizzazione software
    options.add_argument("--disable-plugins")  # Disabilita i plugin del browser
    options.add_argument("--disable-animations")  # Disabilita le animazioni
    options.add_argument("--disable-cache")  # Disabilita la cache
    # options.add_argument('--proxy-server=localhost:8081')
    # options.add_experimental_option("useAutomationExtension", False)  # Disabilita l'estensione di automazione di Chrome
    options.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"]
    )  # Esclude switch della modalità automatica e logging

    options.add_argument("--single-process")  # Esegui Chrome in un solo processo
    return options
