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

    def fuzzy_match_text(self, phrase1: str, phrase2: str):

        # could replace this with something more sophisticated, like fuzzywuzzy

        if phrase1 is None or phrase2 is None:
            return 0

        score = 0

        if str.lower(phrase1) == str.lower(phrase2):
            phrase1_tokens = str.split(phrase1, " ")
            score = len(phrase1_tokens)
        else:
            phrase1_tokens = str.split(phrase1, " ")
            phrase2_tokens = str.split(phrase2, " ")
            for part in phrase1_tokens:
                for token in phrase2_tokens:
                    if str.lower(part) == str.lower(token):
                        score += 1

        return score

    def fuzzy_match_list(self, text: str, list_items: list):
        '''Match the text against a list of candidate words. Returns a
        single value of the h8ghest scoring match.'''

        top_score = 0
        for list_item in list_items:
            item_score = self.fuzzy_match_text(text, list_item)
            if item_score > top_score:
                top_score = item_score

        return top_score

    def fuzzy_match_item(self, text: str, item: dict):

        item_text = item["text"] if "text" in item else None
        if item_text is None:
            return False

        text_score = self.fuzzy_match_text(item_text, text)
        aka_score = self.fuzzy_match_list(
            text, item["aka"]) if "aka" in item else 0
        akas_score = self.fuzzy_match_list(
            text, item["akas"]) if "akas" in item else 0

        return max(text_score, aka_score, akas_score)

    def find_items_by_fuzzy_match(self, name: str, stop_after_first: bool = False, from_viewpoint: dict = None) -> Union[list, None]:

        items = None

        name = str.replace(name, "the ", "")

        search_items = self._get_search_items(from_viewpoint)

        for item in search_items:

            fuzzy_match_score = self.fuzzy_match_item(name, item)

            if fuzzy_match_score > 0:
                item["fuzzy-match-sore"] = fuzzy_match_score
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

    def find_concept(self, text):
        '''Find the highest scoring concept for the given text'''
        
        top_concept = None
        
        concepts = self.find_concepts(text)
        if concepts is None:
            return None
        
        top_score = 0
        for concept in concepts:
            if concept["match-score"] > top_score:
                top_score = concept["match-score"]
                top_concept = concept

        return top_concept

    def find_concepts(self, text):

        concepts = None

        for scene in self.scenes:

            if "concepts" not in scene:
                continue

            for concept in scene["concepts"]:

                new_concept = deepcopy(concept)

                found = False

                score = self.fuzzy_match_text(new_concept["concept"], text)
                if score > 0:
                    new_concept["matched-qty"] = "singular"
                    new_concept["match-score"] = score
                    concepts = self.util.aggregate(concepts, new_concept)
                    continue

                score = self.fuzzy_match_list(text, new_concept["aka"])
                if score > 0:
                    new_concept["matched-qty"] = "singular"
                    new_concept["match-score"] = score
                    concepts = self.util.aggregate(concepts, new_concept)
                    continue

                score = self.fuzzy_match_list(text, new_concept["akas"])
                if score > 0:
                    new_concept["matched-qty"] = "plural"
                    new_concept["match-score"] = score
                    concepts = self.util.aggregate(concepts, new_concept)
                    continue

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

    def resolve_and_enhance_item(self, item: dict):

        if "item" not in item:
            return None

        # try to resolve the item referenced
        item_text = item["item"]
        resolved_items = self.find_items_by_text(
            item_text, self.viewpoint)

        # filter for visible items only
        resolved_items = self.filter_visible_items(resolved_items)

        # if item is not resolved
        if resolved_items is None:
            return "I don't see anything like that.\n"

        # check if we found multiple matches for a singular word
        # return for clarification on which one to use
        if resolved_items is not None and len(resolved_items) > 1:
            self.util.output_debug(
                "ITEM RESOLUTION: More than one matching item found", debug_flag=self.debug)
            concept = self.find_concept(item_text)
            # concepts = self.diorama.find_concepts(item_text)
            # concept = concepts[0] if concepts is not None else None
            if (concept is None) or (concept is not None and concept["matched-qty"] == "singular"):
                self.util.output_debug(
                    "ITEM RESOLUTION: Concept not found or concept indicates singular word, clarification needed.", debug_flag=self.debug)
                input_event["item"] = "#"
                return {"ask": "Which one?", "place-answer-into": item}

        # enhance the items with conceptual information (from isa property)
        enhanced_items = []
        for resolved_item in resolved_items:
            # todo - if next items same concept as previous, could speed this up
            enhanced_item = self.enhance_item_with_concept_info(
                resolved_item)
            enhanced_items = self.util.aggregate(
                enhanced_items, enhanced_item)

        # reduce to a single item if possible
        if len(enhanced_items) == 1:
            enhanced_items = enhanced_items[0]

        item["item"] = enhanced_items
