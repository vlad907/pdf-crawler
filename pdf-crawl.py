import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import requests.exceptions
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import sys

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def fetch_pdf_links(query, max_pdfs=20):
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    try:
        driver = uc.Chrome(headless=False)
    except Exception as e:
        print("Failed to launch Chrome with undetected-chromedriver.")
        print("Make sure Chrome is installed and undetected-chromedriver is compatible.")
        print(f"Error: {e}")
        return []

    try:
        driver.get("https://www.google.com")
        search_box = driver.find_element(By.NAME, "q")
        search_box.send_keys(f"{query} filetype:pdf")
        search_box.send_keys(Keys.RETURN)

        time.sleep(3)  # Wait for results to load

        links = driver.find_elements(By.XPATH, '//a[@href]')
        pdf_links = []
        for link in links:
            href = link.get_attribute("href")
            if href and ".pdf" in href and href.startswith("http"):
                if href not in pdf_links:
                    pdf_links.append(href)
                if len(pdf_links) >= max_pdfs:
                    break
        return pdf_links
    except Exception as e:
        print(f"Selenium error: {e}")
        return []
    finally:
        driver.quit()

def download_pdf(url, save_dir, name_prefix):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            if not response.content.startswith(b'%PDF'):
                print(f"Skipped (not a valid PDF): {url}")
                return
            file_name = os.path.join(save_dir, f"{name_prefix}_{os.path.basename(url.split('?')[0])}")
            with open(file_name, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded: {file_name}")
        else:
            print(f"Failed to download: {url}")
    except requests.exceptions.Timeout:
        print(f"Skipped (timeout): {url}")
    except Exception as e:
        print(f"Error downloading {url}: {e}")

def main():
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        max_pdfs_per_keyword = int(sys.argv[1])
    else:
        max_pdfs_per_keyword = 20

    with open("keywords.json", "r") as f:
        keyword_data = json.load(f)

    output_dir = "downloaded_pdfs"
    os.makedirs(output_dir, exist_ok=True)

    max_search_results = 50  # Increase pool of candidate links

    for category, details in keyword_data.items():
        keywords = details.get("keywords", [])
        category_dir = os.path.join(output_dir, category.replace(" ", "_").replace("/", "_"))
        os.makedirs(category_dir, exist_ok=True)

        for keyword in keywords:
            print(f"Searching PDFs for: {keyword}")
            pdf_links = fetch_pdf_links(keyword, max_pdfs=max_search_results)
            successful_downloads = 0
            for i, pdf_url in enumerate(pdf_links):
                if successful_downloads >= max_pdfs_per_keyword:
                    break
                try:
                    response = requests.get(pdf_url, headers=HEADERS, timeout=10)
                    if response.status_code == 200 and response.content.startswith(b'%PDF'):
                        file_name = os.path.join(category_dir, f"{keyword.replace(' ', '_')}_{successful_downloads+1}.pdf")
                        with open(file_name, 'wb') as f:
                            f.write(response.content)
                        print(f"Downloaded: {file_name}")
                        successful_downloads += 1
                    else:
                        print(f"Skipped (not a valid PDF): {pdf_url}")
                except requests.exceptions.Timeout:
                    print(f"Skipped (timeout): {pdf_url}")
                except Exception as e:
                    print(f"Error downloading {pdf_url}: {e}")

            if successful_downloads == 0:
                with open("failed_keywords.txt", "a") as fail_log:
                    fail_log.write(f"{category} => {keyword}\n")

if __name__ == "__main__":
    main()