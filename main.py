from os import remove
from random import choice, choices, randint
from re import escape, Match, search, sub
from requests import get
from sys import argv


lists = {}
global_settings = {"name": None,
                   "author": None,
                   "description": None,
                   "picture": None,
                   "amount": 1,
                   "button": None}
inclusion_depth = 0
roots = []
all_roots = False
weights = []


def main():
    global roots, weights

    root = parse_file(argv[1])
    roots.append(root)

    if all_roots:
        roots = list(lists.keys())

    if len(argv) > 2:
        root = argv[2]
        if root not in roots:
            print(f"Invalid root: {root}\nTry a different root or verify your generator file.")
            return

    for _ in range(int(global_settings["amount"])):
        print(replace_elements(choices(lists[root], weights=[i["chance"] for i in lists[root]])[0]["element"]))


def replace_elements(string):
    elements = []
    i = 0

    while i < len(string):
        if string[i] != '[':
            i += 1
            continue

        depth = 0

        for j in range(i + 1, len(string)):
            if string[j] == '[':
                depth += 1
            elif string[j] == ']':
                depth -= 1
                if depth < 0:
                    elements.append(string[i:j + 1])
                    i = j + 1
                    break

    for element in elements:
        string = sub(escape(element), fill_ref, string, count=1)

    return string


def fill_ref(match):
    match = match[0] if isinstance(match, Match) else match
    match = match[1:] if match[0] == '[' else match
    match = match[:-1] if match[-1] == ']' else match
    refs = match.split('|')

    if len(refs) == 1:
        return check_options(refs[0])

    ref = choice(refs)

    if ref[0] != '[':
        return ref

    return fill_ref(ref.strip("[]"))


identifiers = {}


def check_options(ref):
    args = ref.split(',')

    if args[0][0] == '#':
        if (element := identifiers.get(args[0][1:])) is None:
            element = args[0]
    else:
        element = choices(lists[args[0]], weights=[i["chance"] for i in lists[args[0]]])[0]["element"]

    for arg in args[1:]:
        if arg[0] == '#':
            identifiers[arg[1:]] = element

    return element


def parse_file(filename):
    global all_roots

    current_list = None
    
    with open(filename, "r") as infile:
        for line in infile:
            if line[0] == '\n':
                continue

            if line[0] == '$':
                ref = line[1:].strip()
                args = ref.split()

                if args[0] in global_settings:
                    global_settings[args[0]] = ref[ref.find(':') + 1:].strip()
                elif args[0] == "include":
                    get_inclusion(args[1])
                elif ref == "all roots":
                    all_roots = True
                elif ref[0] == '+':
                    current_list = ref[1:]
                elif ref[0] == '>':
                    roots.append(ref[1:])
                else:
                    lists[ref] = []
                    current_list = ref
            
            elif current_list is not None:
                if match := search(r"\{(\d+)%\}", line):
                    line = line[:match.start()]

                append_dict = {"element": line.strip(), "attrs": {}, "chance": 100}

                lists[current_list].append(append_dict)

    return current_list


def get_inclusion(arg):
    global inclusion_depth

    if search(r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|"
              r"(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))",
              arg):
        response = get(arg)

        if response.status_code == 200:
            inclusion_depth += 1
            filename = f"temp_{inclusion_depth}.txt"

            with open(filename, "wb") as outfile:
                outfile.write(response.content)

            parse_file(filename)
            remove(filename)
            inclusion_depth -= 1
        else:
            print(f"Error, could not fetch file at: {arg}\n")


if __name__ == "__main__":
    main()
