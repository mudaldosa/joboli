todos = []

while True:
    print("\n[To Do List]")
    print("1. 할 일 추가")
    print("2. 할 일 보기")
    print("3. 종료")

    choice = input("메뉴 선택: ")

    if choice == "1":
        todo = input("할 일을 입력하세요: ")
        todos.append(todo)
        print("추가되었습니다!")

    elif choice == "2":
    
        if len(todos) == 0:
            print("할 일이 없습니다.")
        else:
            for i in range(len(todos)):
                print(f"{i+1}. {todos[i]}")

    elif choice == "3":
        print("프로그램 종료!")
        break

    else:
        print("잘못된 입력입니다.")