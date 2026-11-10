# ===================================================
# For_Func.py
# - [프로젝트명] 외국인 방문객을 위한 여행코스 제안 프로그램
# - 데이터(관심사별 장소, 예산별 코스+호텔, 환율)와
#   번호별로 실행될 "기능 함수"들을 모아둔 파일
# - "몇 번을 선택하면 어떤 함수를 부를지"는 여기서 정하지 않음 (그건 main.py의 역할)
# ===================================================

# [데이터 1] 관심사별 여행지
# - 서울 안에서만 고르지 않도록 지역(region)을 함께 적어서 서울을 벗어난 장소도 포함시킴
# - image는 <img src="..."> 태그에 그대로 넣을 사진 파일 이름
#   (images 폴더를 만들고 같은 이름의 사진 파일을 넣어야 실제로 보임)
interests = {
    "역사": [
        {"name": "경복궁", "region": "서울", "image": "images/gyeongbokgung.jpg"},
        {"name": "종묘", "region": "서울", "image": "images/jongmyo.jpg"},
        {"name": "수원화성", "region": "경기 수원", "image": "images/suwon_hwaseong.jpg"}
    ],
    "자연": [
        {"name": "남산공원", "region": "서울", "image": "images/namsan_park.jpg"},
        {"name": "남이섬", "region": "강원 춘천", "image": "images/nami_island.jpg"},
        {"name": "설악산", "region": "강원 속초", "image": "images/seoraksan.jpg"}
    ],
    "쇼핑": [
        {"name": "명동", "region": "서울", "image": "images/myeongdong.jpg"},
        {"name": "동대문", "region": "서울", "image": "images/dongdaemun.jpg"},
        {"name": "스타필드 하남", "region": "경기 하남", "image": "images/starfield_hanam.jpg"}
    ],
    "음식": [
        {"name": "광장시장", "region": "서울", "image": "images/gwangjang_market.jpg"},
        {"name": "이태원", "region": "서울", "image": "images/itaewon.jpg"},
        {"name": "전주한옥마을", "region": "전북 전주", "image": "images/jeonju_hanok.jpg"}
    ],
    "전시": [
        {"name": "국립중앙박물관", "region": "서울", "image": "images/national_museum.jpg"},
        {"name": "예술의전당", "region": "서울", "image": "images/seoul_arts_center.jpg"},
        {"name": "아쿠아플라넷 여수", "region": "전남 여수", "image": "images/aquaplanet_yeosu.jpg"}
    ]
}

# [데이터 2] 예산 코스 (번호 : 코스 이름, 하루 비용, 어울리는 호텔, 호텔 사진, 추천 장소)
budget_courses = {
    "1": {
        "name": "5만원 알뜰 코스",
        "cost": 50000,
        "hotel": "게스트하우스 서울",
        "hotel_image": "images/hotel_budget.jpg",
        "places": ["광장시장", "명동", "북촌한옥마을"]
    },
    "2": {
        "name": "10만원 알찬 코스",
        "cost": 100000,
        "hotel": "3성급 호텔 종로",
        "hotel_image": "images/hotel_mid.jpg",
        "places": ["경복궁", "한강공원", "홍대"]
    },
    "3": {
        "name": "20만원 프리미엄 코스",
        "cost": 200000,
        "hotel": "5성급 호텔 강남",
        "hotel_image": "images/hotel_premium.jpg",
        "places": ["북한산", "이태원", "동대문"]
    }
}

# [데이터 3] 환율표 (1원을 각 통화로 바꿀 때 곱하는 비율)
exchange_rate = {
    "USD": 0.00075,
    "JPY": 0.11,
    "EUR": 0.00069
}

# 예산 코스 함수(recommend_budget)에서 정한 값을
# 환율 계산 함수(convert_currency)도 이어서 써야 하므로
# 두 함수가 공유하는 값으로 파일 맨 위에 미리 선언해둠 (아직 계산 전이므로 기본값 0)
day_cost = 0


def create_html_page(filename, title, image_path, description):
    """
    [기능] 제목 + <img src="..."> 사진 + 설명을 담은 html 파일을 만들어서 저장함
    [이유] 파이썬 콘솔 화면 안에서는 사진을 직접 보여줄 수 없기 때문에,
           배운 <img src="..."> 태그로 사진이 들어간 html 파일을 만들고
           그 파일을 웹 브라우저로 열어서 사진을 확인하게 하기 위함
           (파이썬 문법은 open, write, close처럼 이미 배운 파일 다루기만 사용함)
    """
    html_content = "<html>\n"
    html_content += "<head><meta charset='utf-8'><title>" + title + "</title></head>\n"
    html_content += "<body>\n"
    html_content += "<h1>" + title + "</h1>\n"
    html_content += '<img src="' + image_path + '" width="400">\n'   # 배운 img src 태그 그대로 사용
    html_content += "<p>" + description + "</p>\n"
    html_content += "</body>\n</html>"

    f = open(filename, "w", encoding="utf-8")   # 쓰기 모드로 html 파일 열기
    f.write(html_content)                        # html 내용을 파일에 작성
    f.close()                                    # 다 쓴 파일은 반드시 닫아줌

    print(f"\n'{filename}' 파일이 생성되었습니다. 웹 브라우저로 열어서 사진을 확인하세요.")


def main_screen():
    """
    [기능] 메뉴 화면(1~4번)을 출력하고, 사용자가 입력한 번호를 반환만 함
    [이유] "메뉴를 보여주는 것"은 하나의 기능이므로 여기서 담당하지만,
           "그 번호로 무엇을 할지 결정하는 것"은 main.py에서 하도록
           일부러 if/elif 없이 입력값만 반환함
    """
    print("\n===== 외국인 방문객을 위한 여행코스 제안 프로그램 =====")
    print("1. 관심사별 여행지 추천 (사진 보기)")
    print("2. 예산에 맞는 호텔 & 코스 추천 (사진 보기)")
    print("3. 예상 비용 환율 변환")
    print("4. 종료")
    return input("원하는 번호를 입력하세요: ")


def recommend_place():
    """
    [기능] 관심사(역사/자연/쇼핑/음식/전시)를 번호로 고르면 장소 목록을 보여주고,
           장소를 하나 더 고르면 사진이 담긴 html 파일을 만들어줌
    [이유] 관심사 -> 장소 두 단계로 나눈 이유는 관심사마다 장소가 여러 개이므로,
           그중 어떤 장소의 사진을 볼지 정확히 골라야 하기 때문
    """
    interest_list = list(interests.keys())

    print("\n관심사를 선택하세요:")
    for idx, name in enumerate(interest_list, start=1):
        print(f"{idx}. {name}")
    choice = input("번호 입력: ")

    if not (choice.isdigit() and 1 <= int(choice) <= len(interest_list)):
        print("등록되지 않은 번호입니다.")
        return

    selected_interest = interest_list[int(choice) - 1]
    place_list = interests[selected_interest]

    print(f"\n[{selected_interest}] 관련 추천 여행지:")
    for idx, place in enumerate(place_list, start=1):
        print(f"{idx}. {place['name']} ({place['region']})")

    place_choice = input("사진으로 볼 장소 번호 입력: ")

    if place_choice.isdigit() and 1 <= int(place_choice) <= len(place_list):
        selected_place = place_list[int(place_choice) - 1]
        description = f"{selected_place['region']}에 위치한 {selected_place['name']}입니다."
        create_html_page("place_result.html", selected_place["name"], selected_place["image"], description)
    else:
        print("등록되지 않은 번호입니다.")


def recommend_budget():
    """
    [기능] 3가지 예산 코스를 전부 보여준 뒤, 번호로 하나를 고르면
           코스 정보를 출력하고 호텔 사진이 담긴 html 파일을 만들어줌
    [이유] 예산에 맞는 "호텔"과 "장소"를 하나의 코스 안에 묶어서
           한 번에 안내하고, 호텔 사진도 함께 보여주기 위함
    """
    global day_cost

    print("\n원하는 예산 코스를 선택하세요:")
    for key, course in budget_courses.items():
        print(f"{key}. {course['name']} ({course['cost']:,}원) - 추천 호텔: {course['hotel']}")

    choice = input("코스 번호 입력: ")

    if choice in budget_courses:
        selected = budget_courses[choice]
        day_cost = selected["cost"]
        print(f"\n[{selected['name']}] 선택")
        print(f"하루 예상 비용: {day_cost:,}원")
        print(f"추천 호텔: {selected['hotel']}")
        print("추천 코스 장소:", ", ".join(selected["places"]))

        description = f"하루 예상 비용 {day_cost:,}원 / 추천 장소: " + ", ".join(selected["places"])
        create_html_page("budget_result.html", selected["hotel"], selected["hotel_image"], description)
    else:
        print("등록되지 않은 코스 번호입니다.")


def convert_currency():
    """
    [기능] 예산 코스에서 계산된 하루 비용(day_cost)을
           원하는 통화로 환산해서 보여줌
    [이유] day_cost가 아직 계산되지 않았을 수도 있으므로(=0),
           그 경우를 먼저 걸러내는 if 검사를 포함함
    """
    if day_cost == 0:
        print("\n먼저 '예산에 맞는 호텔 & 코스 추천' 기능을 실행해서 하루 비용을 계산해주세요.")
        return

    currency_list = list(exchange_rate.keys())

    print("\n통화를 선택하세요:")
    for idx, code in enumerate(currency_list, start=1):
        print(f"{idx}. {code}")
    choice = input("번호 입력: ")

    if choice.isdigit() and 1 <= int(choice) <= len(currency_list):
        selected_currency = currency_list[int(choice) - 1]
        converted = round(day_cost * exchange_rate[selected_currency], 2)
        print(f"환산 비용: 약 {converted} {selected_currency}")
    else:
        print("등록되지 않은 번호입니다.")