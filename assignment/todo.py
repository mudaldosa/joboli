# 리스트를 각각 관리하면 설명하기 훨씬 쉽습니다!
todos = []
priorities = [] # 중요도를 따로 저장하는 리스트

while True:
    print("\n[나의 할 일 관리자]")
    print("1. 추가 / 2. 보기 / 3. 수정 / 4. 삭제 / 5. 종료")

    choice = input("선택: ")

    if choice == "1":
        todo = input("할 일: ")
        # 중요도를 물어보고 바로 리스트에 넣기
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
                # 두 리스트에서 같은 번호를 꺼내서 보여주기
                print(f"{i+1}. [{priorities[i]}] {todos[i]}")

    elif choice == "3": # 수정 기능
        idx = int(input("수정할 번호: ")) - 1
        if 0 <= idx < len(todos):
            new_text = input("수정할 내용: ")
            todos[idx] = new_text # 리스트의 특정 위치 값만 바꾸기
            print("수정되었습니다.")
        else:
            print("번호를 확인해주세요.")

    elif choice == "4": # 삭제 기능
        idx = int(input("삭제할 번호: ")) - 1
        if 0 <= idx < len(todos):
            todos.pop(idx)
            priorities.pop(idx) # 중요도 리스트도 같이 삭제해줘야 순서가 맞음!
            print("삭제 완료.")

    elif choice == "5":
        print("안녕히 계세요!")
        break