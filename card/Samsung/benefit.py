from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time

# 설정
LIST_URL = "https://www.card-gorilla.com/team/detail/1"
BASE_URL = "https://www.card-gorilla.com"
card_company_id = 4
created_at = datetime.now().strftime("%Y-%m-%d")

# 브라우저 설정
options = Options()
# options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("window-size=1920,1080")
options.add_argument("user-agent=Mozilla/5.0")
driver = webdriver.Chrome(options=options)
driver.set_page_load_timeout(60)

print("🚀 사이트 접속 중...")
driver.get(LIST_URL)
time.sleep(3)

# "더보기" 버튼 반복 클릭
while True:
    try:
        more_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.lst_more"))
        )
        driver.execute_script("arguments[0].click();", more_button)
        time.sleep(1.5)
    except TimeoutException:
        print("🖐️ 더보기 버튼 없음 → 전체 카드 로딩 완료")
        break
    except ElementClickInterceptedException:
        driver.execute_script("window.scrollBy(0, 300);")
        time.sleep(1)

# 카드 리스트 수집
card_elements = driver.find_elements(By.CSS_SELECTOR, "ul.lst li div.card-container")
print(f"✅ 총 카드 수: {len(card_elements)}개")

detail_urls = []
for card in card_elements:
    try:
        href = BeautifulSoup(card.get_attribute("innerHTML"), "html.parser").select_one("a.b_view")["href"]
        full_url = BASE_URL + href
        detail_urls.append(full_url)
    except Exception as e:
        print(f"❌ 상세 URL 추출 실패: {e}")
        continue

card_data = []
for idx, url in enumerate(detail_urls):
    try:
        driver.get(url)
        # 페이지 로딩 대기
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # 이미지 로딩 대기 - 카드 이미지가 로드될 때까지 기다림
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "img[data-v-320b85ff], img[src*='card_img']"))
            )
        except TimeoutException:
            print(f"⚠️ 이미지 로딩 타임아웃: {url}")
        
        time.sleep(3)  # 추가 로딩 시간

        soup = BeautifulSoup(driver.page_source, "html.parser")

        name_tag = soup.select_one("strong.card")
        name = name_tag.text.strip() if name_tag else "N/A"

        type_list = "체크카드" if "체크" in name else "신용카드"

        # 카드 이미지 찾기 - 더 정확한 선택자 사용
        img_tag = None
        img_url = "N/A"
        
        # 방법 1: data-v 속성이 있는 img 태그 찾기
        img_candidates = soup.select("img[data-v-320b85ff][data-v-35734774]")
        if img_candidates:
            for img in img_candidates:
                if img.get("src") and "card_img" in img.get("src"):
                    img_tag = img
                    break
        
        # 방법 2: 없다면 card_img가 포함된 img 찾기
        if not img_tag:
            img_candidates = soup.select("img[src*='card_img']")
            if img_candidates:
                img_tag = img_candidates[0]
        
        # 방법 3: 카드 관련 클래스나 영역에서 찾기
        if not img_tag:
            card_areas = soup.select("div.card-container img, div.card-img img, .card-image img")
            for img in card_areas:
                if img.get("src") and any(keyword in img.get("src").lower() for keyword in ["card", "img"]):
                    img_tag = img
                    break
        
        # 방법 4: Selenium으로 직접 찾기 (BeautifulSoup으로 안 될 경우)
        if not img_tag:
            try:
                selenium_img = driver.find_element(By.CSS_SELECTOR, "img[data-v-320b85ff][data-v-35734774]")
                img_url = selenium_img.get_attribute("src")
                print(f"🖼️ Selenium으로 이미지 찾음: {img_url}")
            except:
                try:
                    selenium_img = driver.find_element(By.CSS_SELECTOR, "img[src*='card_img']")
                    img_url = selenium_img.get_attribute("src")
                    print(f"🖼️ Selenium 대체 방법으로 이미지 찾음: {img_url}")
                except:
                    print(f"❌ 이미지를 찾을 수 없습니다: {name}")
        else:
            img_url = img_tag.get("src", "N/A")
            
        print(f"🖼️ 이미지 URL: {img_url}")

        other_block = soup.select_one("div.bnf2")
        other_details = other_block.get_text(separator="\n", strip=True) if other_block else ""

        category_list = []
        benefit_summary_list = []
        benefit_list = []

        # 모든 dt 요소 찾기
        dt_elements = driver.find_elements(By.CSS_SELECTOR, "dt")

        # 카테고리별 데이터를 저장할 리스트
        category_data = []

        # 먼저 모든 카테고리 정보를 수집
        for dt_idx, dt_element in enumerate(dt_elements):
            try:
                cat_element = dt_element.find_element(By.CSS_SELECTOR, "p.txt1")
                category_text = cat_element.text.strip()
            except:
                continue

            # 카테고리 이름 자체가 "유의사항"인 경우에만 넘어가기
            if category_text == "유의사항":
                break

            try:
                summary_element = dt_element.find_element(By.CSS_SELECTOR, "i")
                summary_text = summary_element.text.strip()
            except:
                summary_text = ""

            # 카테고리 데이터 저장
            category_data.append({
                'index': dt_idx,
                'category': category_text,
                'summary': summary_text,
                'content': "",
                'element': dt_element  # 요소 자체도 저장
            })

        print(f"📋 수집할 카테고리: {[(data['index'], data['category']) for data in category_data]}")

        # 현재 열려있는 dd들을 모두 닫기
        def close_all_open_dd():
            try:
                # 열려있는 dt 요소들 찾기 (활성 상태 확인)
                open_dt_elements = driver.find_elements(By.CSS_SELECTOR, "dt.on")
                for open_dt in open_dt_elements:
                    try:
                        driver.execute_script("arguments[0].click();", open_dt)
                        time.sleep(0.5)
                    except:
                        pass
            except:
                pass

        # 초기에 열려있을 수 있는 dd들 닫기
        close_all_open_dd()
        time.sleep(1)

        # 각 카테고리별로 순차적으로 처리
        for data_idx, data in enumerate(category_data):
            category_text = data['category']
            dt_element = data['element']
            
            try:
                print(f"🔍 처리 중: {category_text} (인덱스: {data['index']})")
                
                # 해당 카테고리 클릭하여 열기
                driver.execute_script("arguments[0].click();", dt_element)
                time.sleep(1.5)  # 애니메이션 대기

                # 클릭 후 해당 dd 요소 찾기
                try:
                    # JavaScript로 다음 형제 dd 요소 찾기
                    dd_element = driver.execute_script("""
                        var dt = arguments[0];
                        var nextElement = dt.nextElementSibling;
                        while(nextElement && nextElement.tagName.toLowerCase() !== 'dd') {
                            nextElement = nextElement.nextElementSibling;
                        }
                        return nextElement;
                    """, dt_element)
                    
                    if dd_element:
                        # dd가 실제로 열려있는지 확인 (display나 class 확인)
                        is_visible = driver.execute_script("""
                            var dd = arguments[0];
                            var style = window.getComputedStyle(dd);
                            return style.display !== 'none' && style.visibility !== 'hidden';
                        """, dd_element)
                        
                        if is_visible:
                            dd_html = dd_element.get_attribute('innerHTML')
                            dd_soup = BeautifulSoup(dd_html, 'html.parser')
                            
                            in_box = dd_soup.select_one("div.in_box")
                            if in_box:
                                # 텍스트 정리
                                box_lines = [p.get_text(strip=True) for p in in_box.find_all("p") if p.get_text(strip=True)]
                                box_text = "\n".join(box_lines)

                                # 불필요한 텍스트 제거
                                if "Powered by Froala Editor" in box_text:
                                    box_text = box_text.split("Powered by Froala Editor")[0].strip()

                                if box_text:
                                    category_data[data_idx]['content'] = box_text
                                    print(f"✅ 혜택 수집 완료: {category_text}")
                                else:
                                    print(f"❌ {category_text} 내용이 비어있습니다.")
                                    category_data[data_idx]['content'] = "상세 정보 없음"
                            else:
                                print(f"❌ {category_text} in_box를 찾을 수 없습니다.")
                                category_data[data_idx]['content'] = "상세 정보 없음"
                        else:
                            print(f"❌ {category_text} dd가 열리지 않았습니다.")
                            category_data[data_idx]['content'] = "상세 정보 없음"
                    else:
                        print(f"❌ {category_text} dd 요소를 찾을 수 없습니다.")
                        category_data[data_idx]['content'] = "상세 정보 없음"
                        
                except Exception as inner_e:
                    print(f"❌ {category_text} 내용 추출 중 오류: {inner_e}")
                    category_data[data_idx]['content'] = "수집 실패"

                # 현재 열린 카테고리 닫기 (다음 카테고리 처리 전)
                try:
                    driver.execute_script("arguments[0].click();", dt_element)
                    time.sleep(0.5)
                except:
                    pass

            except Exception as e:
                print(f"❌ 혜택 수집 오류 [{category_text}]: {e}")
                category_data[data_idx]['content'] = "수집 실패"
                continue

        # 수집된 데이터로 리스트 구성
        category_counter = {}  # 동일 카테고리 카운터
        
        for data in category_data:
            if data['content'] and data['content'] not in ["상세 정보 없음", "수집 실패"]:
                category_name = data['category']
                
                # 동일한 카테고리명 처리
                if category_name in category_counter:
                    category_counter[category_name] += 1
                    category_display = f"{category_name}({category_counter[category_name]})"
                else:
                    category_counter[category_name] = 1
                    # 첫 번째는 번호 없이, 하지만 나중에 같은 이름이 또 나오면 첫 번째도 (1)을 붙임
                    category_display = category_name
                
                category_list.append(category_display)
                benefit_summary_list.append(f"<{category_display}> {data['summary']}")
                benefit_list.append(f"<{category_display}>\n{data['content']}")

        # 동일 카테고리가 2개 이상인 경우 첫 번째에도 번호 추가
        final_category_list = []
        final_benefit_summary_list = []
        final_benefit_list = []
        
        temp_counter = {}
        for i, (cat, summary, benefit) in enumerate(zip(category_list, benefit_summary_list, benefit_list)):
            original_cat = cat.split('(')[0]  # 괄호 앞 부분만 추출
            
            if original_cat in temp_counter:
                temp_counter[original_cat] += 1
                current_num = temp_counter[original_cat]
            else:
                temp_counter[original_cat] = 1
                current_num = 1
            
            # 해당 카테고리의 총 개수 확인
            total_count = sum(1 for c in category_list if c.split('(')[0] == original_cat)
            
            if total_count > 1:
                final_cat = f"{original_cat}({current_num})"
                final_summary = f"<{original_cat}({current_num})> {summary.split('> ')[1]}"
                benefit_body = benefit.split('>\n', 1)[1] if '>\n' in benefit else benefit
                final_benefit = f"<{original_cat}({current_num})>\n{benefit_body}"
            else:
                final_cat = original_cat
                final_summary = summary
                final_benefit = benefit
                
            final_category_list.append(final_cat)
            final_benefit_summary_list.append(final_summary)
            final_benefit_list.append(final_benefit)

        # 카드 데이터를 딕셔너리로 구성
        card_info = {
            "card_company_id": card_company_id,
            "name": name,
            "img_url": img_url,
            "type": type_list,
            "created_at": created_at,
            "category": " / ".join(final_category_list),
            "benefit_summary": " / ".join(final_benefit_summary_list),
            "benefit": "\n\n".join(final_benefit_list),
            "other_details": other_details
        }
        
        card_data.append(card_info)
        print(f"🎉 [{idx + 1}/{len(detail_urls)}] {name} 수집 완료")

    except Exception as e:
        print(f"❌ 카드 수집 중 오류: {e}")
        continue

driver.quit()

# DataFrame 생성 시 컬럼 순서 명시
column_order = [
    "card_company_id", 
    "name", 
    "img_url", 
    "type", 
    "created_at",
    "category",
    "benefit_summary",
    "benefit", 
    "other_details"
]

# DataFrame 생성
df = pd.DataFrame(card_data, columns=column_order)

# 빈 값이나 None 값을 빈 문자열로 처리
df = df.fillna("")

# CSV 저장
output_filename = "Samsung_benefit.csv"
df.to_csv(output_filename, index=False, encoding="utf-8-sig")

print(f"\n📁 CSV 저장 완료: {output_filename}")
print(f"📊 수집된 카드 수: {len(card_data)}개")