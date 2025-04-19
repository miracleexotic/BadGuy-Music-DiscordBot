from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from netscape_cookies import to_netscape_string


def get_cookies():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()), options=options
    )

    driver.get("https://www.youtube.com")

    cookie_data = driver.get_cookies()

    file_path = "../databases/cookies.txt"

    # Save cookies to file in Netscape format
    with open(file_path, "w") as f:
        f.writelines(
            "# Netscape HTTP Cookie File\n# https://curl.haxx.se/rfc/cookie_spec.html\n# This is a generated file! Do not edit.\n\n"
        )
        f.writelines(to_netscape_string(cookie_data))

    driver.quit()
