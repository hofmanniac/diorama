import json
from pprint import pprint


class Parser:

    parse_config = None
    debug = False

    def output_debug(self, *args):
        if self.debug:
            print(*args)

    def load_from_file(self, filename):
        if filename is None:
            return
        with open(filename) as file:
            file_contents = json.load(file)
            self.parse_config = file_contents

    def find_word_categories(self, token: str) -> list:

        result = []

        word_categories = self.parse_config["word-categories"]

        for word_category_key in word_categories.keys():
            if token in word_categories[word_category_key]:
                result.append(word_category_key)

        return result

    def unifies(self, template_token, token):

        self.output_debug(".comparing", token, "to", template_token)

        if template_token == "#item":
            word_categories = self.find_word_categories(token)
            if len(word_categories) == 0:
                return True
            else:
                return False

        elif str.startswith(template_token, "#"):
            word_category_name = template_token
            word_categories = self.parse_config["word-categories"]
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

    def process_replacements(self, text: str):

        new_text = " " + text + " "

        for moniker in self.parse_config["replacements"]:
            with_token = moniker["with"]
            at_start_only = moniker["at-start-only"] if "at-start-only" in moniker else False
            for moniker_token in moniker["replace"]:
                if at_start_only:
                    if str.startswith(new_text, " " + moniker_token + " "):
                        new_text = " " + with_token + " " + \
                            new_text[len(moniker_token) + 2:]
                else:
                    new_text = str.replace(
                        new_text, " " + moniker_token + " ", " " + with_token + " ")

        new_text = str.strip(new_text)

        return new_text

    def process_shortcuts(self, text: str):

        new_text = text

        for moniker in self.parse_config["shortcuts"]:
            for_token = moniker["for"]
            shortcut_found = False
            for moniker_token in moniker["shortcut"]:
                if new_text == moniker_token:
                    new_text = for_token
                    shortcut_found = True
                    break
                # new_text = str.replace(
                #     new_text, " " + moniker_token + " ", " " + for_token + " ")

            # could keep going, to find shortcuts on top of shortcuts,
            # but no need for now
            if shortcut_found == True:
                break

        new_text = str.strip(new_text)

        return new_text

    def parse_text(self, text: str):

        self.output_debug(self, "")
        self.output_debug("PARSING:", text, "--------------------")

        text = self.process_replacements(text)
        text = self.process_shortcuts(text)

        tokens = str.split(text, " ")

        for phrase in self.parse_config["phrases"]:

            phrase_template = phrase["phrase"]
            self.output_debug("")
            self.output_debug(f"Analyzing '{phrase_template}'...")

            phrase_tokens = str.split(phrase_template)

            result = {}
            is_match = True
            phrase_idx = 0

            for idx, token in enumerate(tokens):

                if phrase_idx > len(phrase_tokens) - 1:
                    break

                phrase_token = phrase_tokens[phrase_idx]

                # if on #item phrase_token,
                # peek ahead if the next phrase_token matches the current token
                # if so, commit the info to the result and advance the phrase idx
                # (try to move off of #item matching if possible)
                already_matched = False
                if "item" in result and phrase_token == "#item" and phrase_idx < len(phrase_tokens) - 1:
                    next_phrase_token = phrase_tokens[phrase_idx + 1]
                    if self.unifies(next_phrase_token, token):
                        phrase_idx += 1
                        phrase_token = next_phrase_token
                        already_matched = True

                if already_matched or self.unifies(phrase_token, token):

                    # if phrase token is a literal and we're at the first position
                    # then assume that this is tha action (verb)
                    if str.startswith(phrase_token, "#") == False and idx == 0:
                        result["action"] = token

                    # else set the property identified by the phrase token
                    elif str.startswith(phrase_token, "#"):

                        # set the initial property
                        if phrase_token[1:] not in result:
                            result[phrase_token[1:]] = token

                        # append to the property if this is the next time around
                        # (typically, happens for #item)
                        else:
                            result[phrase_token[1:]] += " " + token

                    # if this is not an #item, move to the next phrase token
                    # (stay on phrase token if it is an #item)
                    if phrase_token != "#item":
                        phrase_idx += 1

                    # if we're looking for an #item but we're also at the end
                    # then consider it a "success" and move counter to the next phrase token
                    # then the check below will see that we've used up all the phrase tokens
                    elif phrase_token == "#item" and idx == len(tokens) - 1:
                        phrase_idx += 1

                else:
                    self.output_debug(
                        "..SKIP - token does not unify with phrase token")
                    is_match = False
                    break

            # not a match
            if not is_match:
                continue  # next phrase

            # did not match all tokens
            if idx < len(tokens) - 1:
                self.output_debug(
                    "..SKIP: Sequence does not use all tokens in the input")
                continue  # next phrase

            # did not match all pattern tokens
            if phrase_idx <= len(phrase_tokens) - 1:
                self.output_debug(
                    "..SKIP: Sequence does not use all tokens in the phrase pattern")
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

    # parse_config = load_file("parsing.json")

    def run_console(self):
        while True:
            print("")
            text = input(": ")
            parse = self.parse_text(text)
            pprint(parse)

        # parse = parse_text("go north")
        # print(parse)

        # parse = parse_text("examine coffee")
        # print(parse)

        # parse = parse_text("examine the holographic projector")
        # print(parse)

        # parse = parse_text("turn on projector")
        # print(parse)
