with open("x", 'w') as file:
    file.write("foo bar")
    with open("x", 'r') as ffile:
        ffile.read()