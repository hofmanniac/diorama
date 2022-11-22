import json

parse_config = None


def load_file(filename):
    if filename is None:
        return
    with open(filename) as file:
        file_contents = json.load(file)
        return file_contents


def unifies(template_token, token):
    output_debug(".comparing", token, "to", template_token)

    if template_token == "#item":
        return True

    elif str.startswith(template_token, "#"):
        word_category_name = template_token
        word_categories = parse_config["word-categories"]
        if word_category_name in word_categories:
            word_category_words = word_categories[word_category_name]
            if token in word_category_words:
                return True
            else:
                return False
        else:
            return True

    elif template_token == token:
        return True

    else:
        return False


def output_debug(*args):
    # print(*args)
    pass


def parse_text(text: str):

    output_debug("")
    output_debug("PARSING:", text, "--------------------")

    tokens = str.split(text, " ")

    for phrase in parse_config["phrases"]:

        phrase_template = phrase["phrase"]
        output_debug("")
        output_debug(f"Analyzing '{phrase_template}'...")

        phrase_tokens = str.split(phrase_template)

        result = {}
        is_match = True
        phrase_idx = 0

        for idx, token in enumerate(tokens):

            if phrase_idx > len(phrase_tokens) - 1:
                break

            phrase_token = phrase_tokens[phrase_idx]

            if unifies(phrase_token, token):
                if idx == 0:
                    result["action"] = token
                else:
                    if phrase_token[1:] not in result:
                        result[phrase_token[1:]] = token
                    else:
                        result[phrase_token[1:]] += " " + token
                if phrase_token != "#item":
                    phrase_idx += 1
            else:
                is_match = False
                break

        # not a match
        if not is_match:
            continue  # next phrase

        # did not match all pattern tokens
        if phrase_idx < len(phrase_tokens) - 1:
            continue  # next phrase

        # if we need to reformat the parse
        if "parse" in phrase:
            new_result = {}
            parse_template = phrase["parse"]
            for key in parse_template.keys():
                new_text = ""
                parse_tokens = str.split(parse_template[key], " ")
                for parse_token in parse_tokens:
                    if str.startswith(parse_token, "#"):
                        new_token = result[parse_token[1:]]
                    else:
                        new_token = parse_token
                    new_text += " " + new_token
                new_result[key] = str.lstrip(new_text)
            result = new_result

        # since this is a match, we can just return now
        break

    return result


parse_config = load_file("parsing.json")

while True:
    text = input(":")
    parse = parse_text(text)
    print(parse)

# parse = parse_text("go north")
# print(parse)

# parse = parse_text("examine coffee")
# print(parse)

# parse = parse_text("examine the holographic projector")
# print(parse)

# parse = parse_text("turn on projector")
# print(parse)
