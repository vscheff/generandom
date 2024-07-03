from os import remove
from random import choice, choices, randint
import re
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
identifiers = {}


def main():
    global identifiers, roots, weights

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
        identifiers = {}
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
        if element.lower() in ("[an]", "[s]"):
            continue

        string = re.sub(re.escape(element), fill_ref, string, count=1)

    string = re.sub(r"\[([aA]n)] ([aAeEiIoOuU])", r"\1 \2", string)
    string = re.sub(r"\[([aA])n]", r"\1", string)

    string = re.sub(r"([sxz])\[[sS]]", r"\1es", string)
    string = re.sub(r"([^aeioudgkprt]h)\[[sS]]", r"\1es", string)
    string = re.sub(r"([aeiou])y\[[sS]]", r"\1ies", string)
    string = re.sub(r"(\w+)\[[sS]]", r"\1s", string)

    return string


def fill_ref(match):
    match = match[0] if isinstance(match, re.Match) else match
    match = match[1:] if match[0] == '[' else match
    match = match[:-1] if match[-1] == ']' else match

    if re.search(r"\w+, *%\[[\w|\[\]]+]", match):
        return handle_template(match)

    if result := re.search(r"\A(\d+) *- *(\d+)", match):
        return str(randint(int(result[1]), int(result[2])))

    refs = match.split('|')

    if len(refs) == 1:
        return ' ' if refs[0] == ' ' else check_options(refs[0])

    ref = choice(refs)

    if ref[0] != '[':
        return ref

    return fill_ref(ref.strip("[]"))


def handle_template(match):
    args = [i.strip(',') for i in re.split('%', match)]
    element = choices(lists[args[0]], weights=[i["chance"] for i in lists[args[0]]])[0]
    template = element["element"]

    i = 1
    while template.find(f"%{i}") != -1 and i < len(args):
        template = template.replace(f"%{i}", fill_ref(args[i]))
        i += 1

    return template


def check_options(ref):
    all_cap = ref.isupper()
    capital = ref[0].isupper()
    ref = ref.lower()

    if ref[0] == '#':
        if match := re.search(r"\A#([^,]+)\Z", ref):
            if (element := identifiers.get(match[1])) is None:
                element = ref
            else:
                element = element["element"]
        elif match := re.search(r"\A#([^,]+), *as ([\w]+)\Z", ref):
            if (element := identifiers.get(match[1])) is None:
                element = ref
            elif (element := element["attrs"].get(match[2])) is None:
                element = ref
        elif match := re.search(r"\A#([^,]+), *as (\w+), *or (\w+)", ref):
            if (element := identifiers.get(match[1])) is None:
                element = ref
            elif (element := element["attrs"].get(match[2])) is None:
                element = match[3]
        else:
            element = ref
    else:
        if match := re.search(r"\A([\w ]+), *#(\w+)", ref):
            element = choices(lists[match[1]], weights=[i["chance"] for i in lists[match[1]]])[0]
            identifiers[match[2]] = element
            element = replace_elements(element["element"])
        elif match := re.search(r"\A([\w ]+), *x(\d+) *- *(\d+)", ref):
            k = randint(int(match[2]), int(match[3]))
            elements = choices(lists[match[1]], weights=[i["chance"] for i in lists[match[1]]], k=k)
            element = ''.join(replace_elements(i["element"]) for i in elements)
        elif match := re.search(r"\A([\w ]+), *title", ref):
            element = get_element(match[1]).title()
        elif match := re.search(r"\A([\w ]+), *lower", ref):
            element = get_element(match[1]).lower()
        elif match := re.search(r"\A([\w ]+), *compress", ref):
            element = get_element(match[1]).replace(' ', '')
        elif match := re.search(r"\A([\w ]+), *(first|middle|last) part", ref):
            element = get_element(match[1])
            if match[2] == "first":
                element = element[:len(element) // 3]
            elif match[2] == "middle":
                element = element[len(element) // 3: 2 * len(element) // 3]
            else:
                element = element[2 * len(element) // 3:]
        else:
            element = get_element(ref)

    if all_cap:
        return element.upper()

    if capital:
        return element.capitalize()

    return element


def get_element(ref):
    return replace_elements(choices(lists[ref], weights=[i["chance"] for i in lists[ref]])[0]["element"])

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
                attrs = {i: j for i, j in re.findall(r"{(\w+)\s?:\s?([\w ]+)}", line)}

                if match := re.search(r"{(\d+)%}", line):
                    chance = int(match[1])
                else:
                    chance = 100

                if match := re.search(r"{.*}", line):
                    line = line[:match.start()]

                append_dict = {"element": line.strip(), "attrs": attrs, "chance": chance}

                lists[current_list].append(append_dict)

    return current_list


def get_inclusion(arg):
    global inclusion_depth

    if re.search(r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|"
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
