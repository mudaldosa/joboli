todos = [] # 할일 저장하는 리스트
priorities = [] # 중요도 저장하는 리스트

while True:
    print("\n[나의 할 일 관리자]")
    print("1. 추가 / 2. 보기 / 3. 수정 / 4. 삭제 / 5. 종료")

    choice = input("선택: ")

    if choice == "1":
        todo = input("할 일: ")
       
        p = input("중요한가요? (별표 표시하려면 1 입력): ")
        
        todos.append(todo)
        if p == "1":
            priorities.append("★")
        else:
            priorities.append("  ")
        print("등록 완료!")

    elif choice == "2":
        if len(todos) == 0:
            print("목록이 비어있어요.")
        else:
            for i in range(len(todos)):
               
                print(f"{i+1}. [{priorities[i]}] {todos[i]}")

    elif choice == "3": 
        idx = int(input("수정할 번호: ")) - 1
        if 0 <= idx < len(todos):
            new_text = input("수정할 내용: ")
            todos[idx] = new_text # 리스트의 특정 위치 값만 수정
            print("수정되었습니다.")
        else:
            print("번호를 확인해주세요.")

    elif choice == "4": 
        idx = int(input("삭제할 번호: ")) - 1
        if 0 <= idx < len(todos):
            todos.pop(idx)
            priorities.pop(idx) # pop 이용 삭제 기능
            print("삭제 완료.")

    elif choice == "5":
        print("안녕히 계세요!")
        break