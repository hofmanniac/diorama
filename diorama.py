from typing import Union
from util import Util
from copy import deepcopy
import json


class Diorama:

    scenes = []
    util = Util()
    viewpoint = None
    debug = False

    def _load_from_file(self, filename) -> None:
        if filename is None:
            return
        with open(filename) as f:
            scene = json.load(f)
            self.scenes.append(scene)

            # print("LOADED:", filename)
            self.viewpoint = self.find_item_by_name("player")

            if self.viewpoint is None:

                self.viewpoint = {"item": "player"}
                first_location = self.find_items_by_template(
                    {"isa": "room"}, stop_after_first=True)
                if first_location is not None:
                    self.viewpoint["location"] = first_location["item"]

                if len(self.scenes) > 0:
                    first_scene = self.scenes[0]
                else:
                    first_scene = {"name": "default"}
                    self.scenes = [first_scene]

                if "items" in first_scene:
                    first_scene["items"].append(self.viewpoint)
                else:
                    first_scene["items"] = [self.viewpoint]

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

    def collect_actions(self):
        actions = None
        for scene in self.scenes:
            for item in scene["items"]:
                if "effects" not in item:
                    continue
                for effect in item["effects"]:
                    action = effect["action"] if "action" in effect else None
                    if action is not None:
                        actions = self.util.aggregate(actions, action)
        return actions

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

    def get_attribute(self, item: dict, attribute: str, default=None):
        result = item[attribute] if attribute in item else default
        return result

    def set_attribute(self, item: any, attribute_name: str, value: any):
        if item is None:
            return
        if item is list:
            return  # loop here instead?

        if type(item) is str:
            item = self.find_item_by_name(item)
            if item is None:
                return

        item[attribute_name] = value

    def remove_attribute(self, item: dict, attribute_name: str):
        if attribute_name in item:
            del item[attribute_name]

    def find_item_by_name(self, name: str, from_viewpoint: dict = None):
        search_items = self._get_search_items(from_viewpoint)
        if search_items is None:
            return None
        for item in search_items:
            if item["item"] == name:
                return item
        return None

    def _get_search_items(self, from_viewpoint: dict = None):
        '''Searches all items for the specified viewpoint. If no viewpoint is specified,
        then searches all items in all scenes.'''
        if from_viewpoint is not None:
            return self.get_viewpoint_items(from_viewpoint)
        else:
            items = []
            for scene in self.scenes:
                items = self.util.aggregate(items, scene["items"])
            return items

    def find_items_by_fuzzy_match(self, name: str, stop_after_first: bool = False, from_viewpoint: dict = None) -> Union[list, None]:

        items = None

        name = str.replace(name, "the ", "")

        search_items = self._get_search_items(from_viewpoint)

        for item in search_items:

            if self.fuzzy_match(item, name):
                items = self.util.aggregate(items, item)
                if stop_after_first:
                    return items

            if "aka" in item:
                for aka_item in item["aka"]:
                    if str.lower(aka_item) == str.lower(name):
                        items = self.util.aggregate(items, item)
                        if stop_after_first:
                            return items

        return items

    def find_items_by_template(self, template: dict, stop_after_first: bool = False, from_viewpoint: dict = None) -> Union[list, dict, None]:

        items = None

        search_items = self._get_search_items(from_viewpoint)

        for item in search_items:
            if self.util.unifies(template, item):
                if stop_after_first:
                    return item
                items = self.util.aggregate(items, item)

        return items

    # def find_items_by_template(self, template: dict):
    #     items = None
    #     for scene in self.scenes:
    #         for item in scene["items"]:
    #             if self.util.unifies(template, item):
    #                 items = self.util.aggregate(items, item)
    #     return items

    def find_items_by_text(self, text: str, from_viewpoint: dict = None) -> Union[list, None]:
        '''Find items that match by fuzzy match, by name, or by concept words.

        Does not check for visiblity or other item properies.

        By default, searches all items im all scenes. To search items for a viewpoint only,
        set from_viewpoint.'''

        if text is None:
            return None

        # find item by fuzzy match (text and akas)
        resolved_items = self.find_items_by_fuzzy_match(
            text, from_viewpoint=from_viewpoint)

        # find item by item name
        if resolved_items is None:
            resolved_item = self.find_item_by_name(text, from_viewpoint)
            resolved_items = self.util.listify(resolved_item)

        # try by word lookups e.g. {"word": "vehicle", "aka": ["car", "truck"]}
        if resolved_items is None:
            resolved_items = self.find_items_by_concept(text)

        return resolved_items

    def fuzzy_match(self, item: dict, keyword_text: str):

        item_text = item["text"] if "text" in item else None
        if item_text is None:
            return False

        if str.lower(item_text) == str.lower(keyword_text):
            return True
        else:
            parts = str.split(item_text, " ")
            tokens = str.split(keyword_text, " ")
            score = 0
            for part in parts:
                for token in tokens:
                    if str.lower(part) == str.lower(token):
                        score += 1
            if score >= 1:
                return True

        return False

    def find_items_by_concept(self, text: str):

        items = None

        concepts = self.find_concepts(text)
        if concepts is None:
            return None

        for concept in concepts:
            # find items that are this type of word (isa)
            sub_items = self.find_items_by_template(
                {"isa": concept["concept"]})
            items = self.util.aggregate(items, sub_items)

        return items

    def get_viewpoint_location(self, from_viewpoint: dict = None):

        if from_viewpoint is None:
            from_viewpoint = self.viewpoint

        location_name = from_viewpoint["location"] if "location" in from_viewpoint else None
        if location_name is not None:
            location = self.find_item_by_name(location_name)
            return location

        return None

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

    def enhance_item_with_concept_info(self, item):
        '''Enhances the item with conceptual information from the isa hiearchy. This 
        function will return a copy of the item, to avoid modifying the original.'''

        # if there is no isa information, then just return
        isa = item["isa"] if "isa" in item else None
        if isa is None:
            return item

        # make a copy of the original, to prevent from storing all the hiearchy
        # information back in the original item
        enhanced_item = deepcopy(item)

        # for all concepts
        for scene in self.scenes:

            # if not concepts defined in this scene, then move to the next one
            if "concepts" not in scene:
                continue

            for concept in scene["concepts"]:

                # if this is the concept we want
                if concept["concept"] != isa:
                    continue

                 # walk up the parent isa hierarchy (recursive)
                 # to get properties
                if "isa" in concept:
                    concept = self.enhance_item_with_concept_info(
                        concept)

                # now add properties not already in the item
                for concept_key in concept:

                    # special properties for the concept itself
                    if concept_key in ["concept", "isa", "aka", "akas"]:
                        continue

                    # if the concept property is not already in the item
                    if concept_key not in enhanced_item:
                        enhanced_item[concept_key] = concept[concept_key]
                    else:
                        # consider merge cases (like effects)
                        pass

        return enhanced_item

    def find_concepts(self, text):

        concepts = None

        for scene in self.scenes:

            if "concepts" not in scene:
                continue

            for concept in scene["concepts"]:

                new_concept = deepcopy(concept)

                found = False

                if str.lower(new_concept["concept"]) == str.lower(text):
                    new_concept["matched-qty"] = "singular"
                    found = True

                elif "aka" in new_concept:

                    if type(new_concept["aka"]) is list:
                        if str.lower(text) in [str.lower(aka) for aka in new_concept["aka"]]:
                            new_concept["matched-qty"] = "singular"
                            found = True

                    elif type(new_concept["aka"]) is str:
                        if str.lower(text) == str.lower(new_concept["aka"]):
                            new_concept["matched-qty"] = "singular"
                            found = True

                if found == False and "akas" in new_concept:

                    if type(new_concept["akas"]) is list:
                        if str.lower(
                                text) in [str.lower(aka) for aka in new_concept["akas"]]:
                            new_concept["matched-qty"] = "plural"
                            found = True

                    elif type(new_concept["akas"]) is str:
                        if str.lower(text) == str.lower(new_concept["akas"]):
                            new_concept["matched-qty"] = "plural"
                            found = True

                if found:

                    concepts = self.util.aggregate(concepts, new_concept)

        return concepts

    def get_items_at_location(self, location):

        if location is None:
            return

        items = None

        for scene in self.scenes:
            if "items" not in scene:
                continue

            scene_items = self.filter_items_in_location(
                scene["items"], location)

            if scene_items is None:
                continue

            items = self.util.aggregate(items, scene_items)

            # recursion here to get items in and on items
            for scene_item in scene_items:
                scene_sub_items = self.get_items_at_location(scene_item)
                items = self.util.aggregate(items, scene_sub_items)

        return items

    def get_viewpoint_items(self, from_viewpoint: dict = None):

        if from_viewpoint is None:
            from_viewpoint = self.viewpoint

        items = []

        # get items at the viewpoint's location
        current_location = self.get_viewpoint_location(from_viewpoint)
        location_items = self.get_items_at_location(current_location)
        items = self.util.aggregate(items, location_items)

        # get items in inventory for the viewpoint
        inventory_items = self.find_items_by_template(
            {"location": from_viewpoint})
        items = self.util.aggregate(items, inventory_items)

        items = self.filter_visible_items(items)

        return items

    def filter_visible_items(self, items: list):

        if items is None:
            return

        results = []

        for item in items:

            visible = self.get_attribute(item, "visible", True)
            if visible:
                results = self.util.aggregate(results, item)

        return results

    def filter_items_in_location(self, items: list, location: dict):

        if items is None or location is None:
            return

        results = None

        for item in items:

            if item["item"] == "player":
                continue

            relation = "location" if "location" in item else None
            relation = "on" in "location" if relation is None and "on" in item else relation
            relation = "in" in "location" if relation is None and "off" in item else relation

            if relation in item:
                if item[relation] == location["item"]:
                    results = self.util.aggregate(results, item)

        return results
