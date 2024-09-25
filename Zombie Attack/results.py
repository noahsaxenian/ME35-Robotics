def read_results():
    with open("zombie_results.txt", "r") as f:
        array_str = f.read()
    print(array_str)
    return array_str

read_results()