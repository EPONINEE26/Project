# -*- coding: utf-8 -*-
"""프차몰 + 점포가이드 원문 수집 스크립트.

실행:
    pip install selenium beautifulsoup4 lxml
    python 01_웹스크래핑_원문수집.py

각 페이지를 Chrome으로 열고 자동 스크롤한 뒤 HTML과 표시 텍스트를 저장합니다.
이 스크립트는 숫자를 추측해 자동 보정하지 않습니다. 연도별 수치는 두 사이트의
표에 실제로 보이는 연도를 사람이 확인한 뒤, 포함된 JSON 데이터와 대조하도록 합니다.
"""
import json
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URLS = {
  "블루클럽": {
    "프차몰": "https://fchamall.com/franchise-info/%EB%B8%94%EB%A3%A8%ED%81%B4%EB%9F%BD",
    "점포가이드": "https://jumpo.shop/%EB%B8%94%EB%A3%A8%ED%81%B4%EB%9F%BD-%ED%94%84%EB%9E%9C%EC%B0%A8%EC%9D%B4%EC%A6%88-%EC%A0%95%EB%B3%B4%EA%B3%B5%EA%B0%9C%EC%84%9C-%EC%9A%94%EC%95%BD/"
  },
  "박승철헤어스투디오": {
    "프차몰": "https://fchamall.com/franchise-info/%EB%B0%95%EC%8A%B9%EC%B2%A0%ED%97%A4%EC%96%B4%EC%8A%A4%ED%88%AC%EB%94%94%EC%98%A4",
    "점포가이드": "https://jumpo.shop/%EB%B0%95%EC%8A%B9%EC%B2%A0%ED%97%A4%EC%96%B4%EC%8A%A4%ED%88%AC%EB%94%94%EC%98%A4-%ED%94%84%EB%9E%9C%EC%B0%A8%EC%9D%B4%EC%A6%88-%EC%A0%95%EB%B3%B4%EA%B3%B5%EA%B0%9C%EC%84%9C-%EC%9A%94%EC%95%BD-2025-12/"
  },
  "제오헤어": {
    "프차몰": "https://fchamall.com/franchise-info/xeo-hair-%EC%A0%9C%EC%98%A4%ED%97%A4%EC%96%B4",
    "점포가이드": "https://jumpo.shop/xeo-hair%EC%A0%9C%EC%98%A4%ED%97%A4%EC%96%B4-%ED%94%84%EB%9E%9C%EC%B0%A8%EC%9D%B4%EC%A6%88-%EC%A0%95%EB%B3%B4%EA%B3%B5%EA%B0%9C%EC%84%9C-%EC%9A%94%EC%95%BD/"
  },
  "이철헤어커커": {
    "프차몰": "https://fchamall.com/franchise-info/%EC%9D%B4%EC%B2%A0%ED%97%A4%EC%96%B4%EC%BB%A4%EC%BB%A4",
    "점포가이드": "https://jumpo.shop/%EC%9D%B4%EC%B2%A0%ED%97%A4%EC%96%B4%EC%BB%A4%EC%BB%A4-%ED%94%84%EB%9E%9C%EC%B0%A8%EC%9D%B4%EC%A6%88-%EC%A0%95%EB%B3%B4%EA%B3%B5%EA%B0%9C%EC%84%9C-%EC%9A%94%EC%95%BD/"
  },
  "에이바헤어": {
    "프차몰": "https://fchamall.com/franchise-info/%EC%97%90%EC%9D%B4%EB%B0%94%ED%97%A4%EC%96%B4",
    "점포가이드": "https://jumpo.shop/%EC%97%90%EC%9D%B4%EB%B0%94%ED%97%A4%EC%96%B4-%ED%94%84%EB%9E%9C%EC%B0%A8%EC%9D%B4%EC%A6%88-%EC%A0%95%EB%B3%B4%EA%B3%B5%EA%B0%9C%EC%84%9C-%EC%9A%94%EC%95%BD-2026-03-20/"
  }
}
OUT = Path('웹스크래핑_원문')
OUT.mkdir(exist_ok=True)

options = Options()
options.add_experimental_option('excludeSwitches', ['enable-automation'])
options.add_experimental_option('useAutomationExtension', False)
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_experimental_option('prefs', {'profile.managed_default_content_settings.images': 2})
# 크롬 창을 보이지 않고 실행하려면 아래 주석을 해제하세요.
# options.add_argument('--headless=new')

browser = webdriver.Chrome(options=options)
manifest = []
try:
    for brand, pages in URLS.items():
        for source_name, url in pages.items():
            safe_brand = brand.replace('/', '_').replace(' ', '_')
            safe_src = '프차몰' if source_name == '프차몰' else '점포가이드'
            try:
                browser.get(url)
                WebDriverWait(browser, 25).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )
                time.sleep(2)

                # 700px씩 내려가며 추가 콘텐츠가 더 이상 로딩되지 않을 때까지 스크롤
                old_height = 0
                stable_count = 0
                scroll_count = 0
                for _ in range(40):
                    browser.execute_script('window.scrollBy(0, 700);')
                    time.sleep(0.4)
                    new_height = browser.execute_script(
                        'return document.documentElement.scrollHeight'
                    )
                    scroll_count += 1
                    if new_height == old_height:
                        stable_count += 1
                    else:
                        stable_count = 0
                    old_height = new_height
                    if stable_count >= 3:
                        break

                html = browser.page_source
                text = browser.find_element(By.TAG_NAME, 'body').text
                (OUT / f'{safe_brand}_{safe_src}.html').write_text(html, encoding='utf-8')
                (OUT / f'{safe_brand}_{safe_src}.txt').write_text(text, encoding='utf-8')
                manifest.append({
                    '브랜드': brand, '출처': source_name, 'URL': url,
                    '상태': '수집 완료', '스크롤 횟수': scroll_count,
                    '페이지 제목': browser.title
                })
                print(f'완료: {brand} / {source_name}')
            except Exception as exc:
                manifest.append({
                    '브랜드': brand, '출처': source_name, 'URL': url,
                    '상태': f'오류: {type(exc).__name__}: {exc}',
                    '스크롤 횟수': None, '페이지 제목': ''
                })
                print(f'오류: {brand} / {source_name}: {exc}')
finally:
    browser.quit()

(OUT / '수집목록.json').write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8'
)
print(f'원문 저장 폴더: {OUT.resolve()}')
