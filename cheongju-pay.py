from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time

category_code_map = {
    "숙박": "1001", "여행": "1101", "레저": "2001", "문화/취미": "2201",
    "의류/잡화/생활가전": "4201", "주유소": "3301", "유통": "4001",
    "서적/문구": "5001", "학원": "5101", "사무통신": "5201", "자동차판매": "6001",
    "서비스": "6101", "보험": "6201", "병원": "7001", "약국": "7040", "기타 의료기관": "7043",
    "미용/안경/보건위생": "7101", "일반/휴게음식": "8001", "제과/음료식품": "8301",
    "기타": "9993"
}

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
driver.get("https://search.konacard.co.kr/payable-merchants/cheongju")
time.sleep(3)

all_data = []

for category, code in category_code_map.items():
    print(f"카테고리: {category}")

    try:
        # 1) 카테고리 버튼 클릭
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, f'li[data-biz-type="{code}"]'))
        ).click()
        time.sleep(2)

        # 2) 검색 버튼 클릭
        search_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[text()='검색']"))
        )
        search_btn.click()
        time.sleep(2)

    except Exception as e:
        print(f"버튼 클릭 실패: {e}")
        continue

    while True:
        try:
            # tbody 요소가 비어있다가 → tr 요소가 등장할 때까지 대기
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'tbody tr[data-seq]'))
            )
            rows = driver.find_elements(By.CSS_SELECTOR, 'tbody tr[data-seq]')
        except:
            print("가맹점 로딩 실패 혹은 없음")
            break

        print(f"  → {len(rows)}건 수집 중...")

        for row in rows:
            try:
                tds = row.find_elements(By.TAG_NAME, 'td')
                if len(tds) >= 4:
                    name = tds[0].text.strip()
                    category_text = tds[1].text.strip()
                    address = tds[2].text.strip()
                    phone = tds[3].text.strip()
                    all_data.append({
                        '카테고리': category,
                        '상호명': name,
                        '업종': category_text,
                        '주소': address,
                        '전화번호': phone
                    })
            except:
                continue

        # 다음 버튼 확인
        try:
            next_btn = driver.find_element(By.XPATH, '//img[@alt="다음으로"]/parent::a')
            if 'javascript' in next_btn.get_attribute("href"):
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(2)
            else:
                break  # 다음 버튼 없음
        except:
            break  # 다음 버튼 없음

driver.quit()

df = pd.DataFrame(all_data)
df.to_csv("/Users/hyunji/Desktop/work/25-1_공모전/PAY-TERN/Data/cheongju-pay.csv", index=False, encoding='utf-8-sig')
print("전체 수집 완료! 총 수집 수:", len(df))