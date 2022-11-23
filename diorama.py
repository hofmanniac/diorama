from util import Util
from copy import deepcopy


class Diorama:

    scenes = []
    util = Util()

    def evaluate(self, value):

        results = []

        if type(value) is str:
            return self.evaluate_text(value)

        elif type(value) is bool:
            return value

        elif type(value) is dict:
            if "find-all" in value:
                sub_result = self.process_find_all(value)
            elif "if" in value:
                sub_result = self.process_if(value)
            elif "action" in value:
                if value["action"] == "set":
                    sub_result = value
                else:
                    if "do" in value:
                        sub_result = value["do"]
                    else:
                        sub_result = value
            else:
                sub_result = value
            results = self.util.aggregate(results, sub_result)

        elif type(value) is list:
            for sub_value in value:
                sub_result = self.evaluate(sub_value)
                results = self.util.aggregate(results, sub_result)

        if len(results) == 1:
            return results[0]
        else:
            return results

    def evaluate_text(self, text: str):

        tokens = str.split(text, " ")
        result = ""
        for token in tokens:
            if str.find(token, ".") > 0 and not str.endswith(token, ".") and not str.startswith(token, "."):
                token = self.resolve_token_value(token)
            result = result + str(token) + " "
        result = str.strip(result)
        if result == "True":
            return True
        elif result == "False":
            return False
        else:
            return result

    def resolve_token_value(self, token: str):

        parts = str.split(token, ".")

        item = None
        value = None
        polarity = True
        for part in parts:
            if item is None:
                if str.startswith(part, "!"):
                    polarity = False
                    part = part[1:]
                item = self.find_item_by_name(part)
            else:
                value = item[part] if part in item else None

        if polarity == False:
            if value is None:
                value = False
            value = not(value)

        return value

    def process_if(self, event):

        passed = False

        if_value = self.evaluate(event["if"])
        if if_value == "None":
            if_value = False

        equals_clause = event["equals"] if "equals" in event else None
        if equals_clause is not None:
            equals_value = self.evaluate(equals_clause)
            if if_value == equals_value:
                passed = True
        else:
            if type(if_value) is bool:
                if if_value:
                    passed = True
            else:
                pass  # anything to do here?

        if passed:
            # return event["do"]
            return self.evaluate(event["do"])
        else:
            if "else" in event:
                # return event["else"]
                return self.evaluate(event["else"])

    def get_attribute(self, item: dict, attribute: str):
        result = item[attribute] if attribute in item else None
        return result

    def update_attribute(self, item_name: str, attribute_name: str, value: any):
        item = self.find_item_by_name(item_name)
        item[attribute_name] = value

    def find_item_by_name(self, name: str):
        for scene in self.scenes:
            for item in scene["items"]:
                if item["item"] == name:
                    return item
        return None

    def find_item_by_fuzzy_match(self, name: str):
        name = str.replace(name, "the ", "")
        for scene in self.scenes:
            for item in scene["items"]:
                if self.fuzzy_match(item, name):
                    return item
                if "aka" in item:
                    for aka_item in item["aka"]:
                        if str.lower(aka_item) == str.lower(name):
                            return item
        return None

    def find_item_by_template(self, template: dict):
        for scene in self.scenes:
            for item in scene["items"]:
                if self.util.unifies(template, item):
                    return item
        return None

    def find_items_by_template(self, template: dict):
        items = []
        for scene in self.scenes:
            for item in scene["items"]:
                if self.util.unifies(template, item):
                    items.append(item)
        return items

    def find_item_by_text(self, text: str):

        if text is None:
            return None, None

        # find item by fuzzy match (text and akas)
        resolved_item = self.find_item_by_fuzzy_match(text)

        # find item by item name
        if resolved_item is None:
            resolved_item = self.find_item_by_name(text)

        # # pull name out of resolved
        # if resolved_item is not None:
        #     resolved_item = resolved_item["item"]

        # try by word lookups e.g. {"word": "vehicle", "aka": ["car", "truck"]}
        if resolved_item is None:
            resolved_item, effect = self.find_items_by_word(text)
            return resolved_item, effect

        return resolved_item, None

    def fuzzy_match(self, item: dict, keyword_text: str):

        item_text = item["text"] if "text" in item else None
        if item_text is None:
            return False

        if str.lower(item_text) == str.lower(keyword_text):
            return True
        else:
            parts = str.split(item_text, " ")
            score = 0
            for part in parts:
                if str.lower(part) == str.lower(keyword_text):
                    score += 1
            if score >= 1:
                return True

        return False

    def find_items_by_word(self, text: str):

        items = None
        effects = None

        for scene in self.scenes:

            for word in scene["words"]:

                word_text = word["word"]

                search_for_word = True if str.lower(
                    word_text) == str.lower(text) else False

                if search_for_word == False and "aka" in word:
                    if type(word["aka"]) is list:
                        search_for_word = True if str.lower(
                            text) in [str.lower(aka) for aka in word["aka"]] else False
                    elif type(word["aka"]) is str:
                        search_for_word = True if str.lower(
                            text) == str.lower(word["aka"]) else False

                if search_for_word:

                    if "plural-of" in word:
                        word_text = word["plural-of"]

                    # find items that are this type of word (isa)
                    sub_items = self.find_items_by_template({"isa": word_text})
                    if sub_items is None:
                        continue

                    # check if we found multiple matches for singular word
                    if len(sub_items) > 1 and "plural-of" not in word:
                        return None, {"ask": "Which " + text + "?"}

                    # else keep collecting all matched items
                    else:
                        items = self.util.aggregate(items, sub_items)

        return items, effects

    def get_location_of(self, item_name: str):

        # get player
        item = self.find_item_by_name(item_name)
        if item is None:
            return None

        # get location
        location_name = item["location"] if "location" in item else None
        if location_name is None:
            return None

        # get that location
        location = self.find_item_by_name(location_name)
        return location

    def process_find_all(self, event: dict):
        effects = []
        template = event["find-all"]
        items = self.find_items_by_template(template)
        for item in items:
            actions = event["do"]
            if type(actions) is not list:
                actions = [actions]
            for action in actions:
                action_copy = deepcopy(action)
                for key in action_copy.keys():
                    # sub values
                    # todo - quick for now, will make this better
                    action_copy[key] = str.replace(
                        action_copy[key], "@item.name", item["item"])
                effects.append(action_copy)
        return effects
