import csv
import json
import time
import zipfile
import logging
import requests
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ---------------- CONFIG ---------------- #
with open("config.json") as f:
    CONFIG = json.load(f)

BASE_URL = CONFIG["base_url"]
OUTPUT_DIR = Path(CONFIG["output_dir"])
WAIT_TIME = CONFIG["page_load_wait"]
CAPTCHA_PAUSE = CONFIG.get("captcha_pause", True)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
Path("logs").mkdir(exist_ok=True)

# ---------------- LOGGING ---------------- #
logging.basicConfig(
    filename="logs/failed_downloads.log",
    level=logging.ERROR,
    format="%(asctime)s - %(message)s"
)

COMPLETED_FILE = Path("logs/completed.csv")
if not COMPLETED_FILE.exists():
    with open(COMPLETED_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ward_no", "parcel_no"])

# ---------------- LOAD COMPLETED ---------------- #
completed = set()
with open(COMPLETED_FILE) as f:
    reader = csv.DictReader(f)
    for row in reader:
        completed.add((row["ward_no"], row["parcel_no"]))

# ---------------- SELENIUM SETUP ---------------- #
def setup_driver():
    options = Options()

    # Windows / Mac / Linux safe
    options.add_argument("--window-size=1920,1080")

    if CONFIG.get("headless", False):
        options.add_argument("--headless=new")

    service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(
        service=service,
        options=options
    )
    return driver




# ---------------- IMAGE DOWNLOAD ---------------- #
def download_image(driver, image_url, save_path):
    try:
        session = requests.Session()
        for cookie in driver.get_cookies():
            session.cookies.set(cookie["name"], cookie["value"])

        response = session.get(image_url, timeout=20)
        response.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(response.content)

        return True

    except Exception as e:
        logging.error(f"{image_url} -> {str(e)}")
        return False

# ---------------- CSV INPUT ---------------- #
def load_csv():
    records = []
    with open("input.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    return records

# ---------------- CAPTCHA PAUSE ---------------- #
def wait_for_captcha():
    if CAPTCHA_PAUSE:
        input("\nSolve CAPTCHA in browser, then press ENTER to continue...")

# ---------------- MAIN SCRAPER ---------------- #
def run():
    driver = setup_driver()
    driver.get(BASE_URL)

    wait_for_captcha()

    records = load_csv()

    for row in records:
        ward = row["ward_no"]
        parcel = row["parcel_no"]

        if (ward, parcel) in completed:
            print(f"Skipping completed: Ward {ward} Parcel {parcel}")
            continue

        try:
            print(f"Processing Ward {ward} Parcel {parcel}")

            # -------- PLACEHOLDER SELECTORS --------
            # Replace when real portal is provided
            # driver.find_element(By.ID, "ward").send_keys(ward)
            # driver.find_element(By.ID, "parcel").send_keys(parcel)
            # driver.find_element(By.ID, "search").click()

            driver.find_element(By.ID, "ward").clear()
            driver.find_element(By.ID, "ward").send_keys(ward)

            driver.find_element(By.ID, "parcel").clear()
            driver.find_element(By.ID, "parcel").send_keys(parcel)

            driver.find_element(By.TAG_NAME, "button").click()
##

            time.sleep(WAIT_TIME)

            image = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "img"))
            )

            image_url = image.get_attribute("src")

            ward_dir = OUTPUT_DIR / f"ward_{ward}"
            ward_dir.mkdir(exist_ok=True)

            save_path = ward_dir / f"parcel_{parcel}_712.jpg"

            if download_image(driver, image_url, save_path):
                with open(COMPLETED_FILE, "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([ward, parcel])
                completed.add((ward, parcel))

            time.sleep(1)

        except Exception as e:
            logging.error(f"Ward {ward} Parcel {parcel} -> {str(e)}")

    driver.quit()
    zip_results()

# ---------------- ZIP RESULTS ---------------- #
def zip_results():
    zip_path = OUTPUT_DIR / "712_records.zip"
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file in OUTPUT_DIR.rglob("*.jpg"):
            zipf.write(file, file.relative_to(OUTPUT_DIR))

    print("ZIP created successfully.")

# ---------------- RUN ---------------- #
if __name__ == "__main__":
    run()
