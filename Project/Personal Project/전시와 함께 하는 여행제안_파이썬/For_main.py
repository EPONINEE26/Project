# ===================================================
# main.py
# - [프로젝트명] 외국인 방문객을 위한 여행코스 제안 프로그램
# - 실행부: main_screen()으로 번호를 받고,
#   그 번호(choice)에 따라 어떤 기능 함수를 부를지 여기서 if/elif로 결정함
# - 각 기능의 세부 동작(입력, 검사, 출력)은
#   전부 For_Func.py 함수 안에서 처리되므로 여기서는 호출만 함
# ===================================================

from For_Func import main_screen, recommend_place, recommend_budget, convert_currency

# 4번(종료)을 선택하기 전까지 계속 메뉴로 돌아와야 하므로 while 반복문 사용
while True:
    choice = main_screen()

    if choice == "1":
        recommend_place()
    elif choice == "2":
        recommend_budget()
    elif choice == "3":
        convert_currency()
    elif choice == "4":
        print("\n프로그램을 종료합니다.")
        break
    else:
        print("\n1~4 사이의 번호만 입력해주세요.")