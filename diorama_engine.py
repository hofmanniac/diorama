import copy
import time
from pprint import pprint, pformat
from termcolor import colored
from phrase_parser import Parser
from core_actions import CoreActions
from diorama import Diorama
from util import Util
from typing import Union


class DioramaEngine:

    diorama = Diorama()
    globals = {}
    debug = False
    parser = Parser()
    core_actions = CoreActions(diorama)
    util = Util()
    text_delay = 0.01

    def __init__(self) -> None:
        pass

    def load_scene(self, filename):
        self.diorama._load_from_file(filename)
        self._sync_actions_to_parser()

    def load_parser(self, filename):
        self.parser._load_from_file(filename)
        self._sync_actions_to_parser()

    def _sync_actions_to_parser(self):

        if self.parser is None:
            return

        actions = ["go", "enter", "exit", "say",
                   "set", "examine", "take", "print", "inventory"]

        if self.diorama is not None:
            scene_actions = self.diorama.collect_actions()
            actions = self.util.aggregate(actions, scene_actions)

        self.parser.set_word_category("#action", actions)

    def process_item_effects(self, event) -> list:

        effects = []

        for scene in self.diorama.scenes:

            # look for item effects
            for item in scene["items"]:

                # if no effects - keep going
                if "effects" not in item:
                    continue

                item_name = item["item"]

                for effect in item["effects"]:

                    candidate_effect = copy.deepcopy(effect)

                    if "item" not in candidate_effect:
                        if "actor" not in candidate_effect:
                            candidate_effect["item"] = item_name

                    if self.util.unifies(candidate_effect, event) == False:
                        continue

                    # effect matched - add the effects
                    new_effects = self.diorama.evaluate(candidate_effect)
                    if type(new_effects) is not list:
                        new_effects = [new_effects]

                    effects = self.util.aggregate(effects, new_effects)

        return effects

    def output_text(self, message):

        messages = []
        if type(message) is str:
            messages = [message]
        elif type(message) is list:
            messages = message

        for message in messages:
            for char in message:
                print(str.upper(char), end="")
                if self.text_delay > 0:
                    time.sleep(self.text_delay)
            if len(message) > 0 and char != '\n':
                # print(" ", end="")
                print("")
                print("")

    def process_event(self, event: dict):
        '''Executes the actions in the event / action. In general, you should use 'evaluate' instead of this function, and only use this function if you need to run a single action.'''

        self.util.output_debug("PROCESS EVENT:", event, debug_flag=self.debug)

        if type(event) is str:
            self.output_text(event)
            return

        effects = []

        # process item effects - before action effects

        # process item effects - instead of action effects
        item_effects = self.process_item_effects(event)
        effects = self.util.aggregate(effects, item_effects)

        if len(item_effects) == 0:

            action_effects = None

            if event["action"] == "go":
                action_effects = self.core_actions.process_go(event)
            elif event["action"] == "enter":
                action_effects = self.core_actions.process_enter(event)
            elif event["action"] == "exit":
                action_effects = self.core_actions.process_exit(event)
            elif event["action"] == "say":
                action_effects = self.core_actions.process_say(event)
            elif event["action"] == "set":
                action_effects = self.core_actions.process_set(event)
            elif event["action"] == "examine":
                action_effects = self.core_actions.process_examine(event)
            elif event["action"] == "take":
                action_effects = self.core_actions.process_take(event)
            elif event["action"] == "print":
                action_effects = self.core_actions.process_print(event)
            elif event["action"] == "inventory":
                action_effects = self.core_actions.process_inventory(event)

            if action_effects is None:
                action_effects = []

            effects = self.util.aggregate(effects, action_effects)

        return effects

    def assert_event(self, event: dict):
        '''Run all events and their triggered events until no additional events are triggered.'''
        event_queue = [event]

        while len(event_queue) > 0:
            queued_event = event_queue.pop(0)
            sub_effects = self.process_event(queued_event)
            event_queue = self.util.aggregate(event_queue, sub_effects)

    def resolve_and_enhance_item(self, item_text: dict) -> Union[None, dict, list]:

        # try to resolve the item referenced
        resolved_items = self.diorama.find_items_by_text(
            item_text, self.diorama.viewpoint)

        # filter for visible items only
        resolved_items = self.diorama.filter_visible_items(resolved_items)

        # if item is not resolved
        if resolved_items is None:
            return None

        # enhance the items with conceptual information (from isa property)
        enhanced_items = []
        for resolved_item in resolved_items:
            # todo - if next items same concept as previous, could speed this up
            enhanced_item = self.diorama.enhance_item_with_concept_info(
                resolved_item)
            enhanced_items = self.util.aggregate(enhanced_items, enhanced_item)

        # reduce to a single item if possible
        if len(enhanced_items) == 1:
            enhanced_items = enhanced_items[0]

        return enhanced_items

    def process_text(self, text, previous_result=None):

        # parse the text into a more structured form
        # do this before checking the previous_result in case
        # the command is instructing to go in a new direction
        parse_result = self.parser.parse_text(text)
        self.util.output_debug(
            f"PARSED: '{text}'", parse_result, debug_flag=self.debug)

        # if could not parse the text and an previous_result (ask) exists
        # try sticking the text into that and use it as the event
        if parse_result is None and previous_result is not None:
            if type(previous_result) is not dict:
                pass
            if "ask" not in previous_result:
                pass
            parse_result = previous_result["place-answer-into"]
            for key in parse_result.keys():
                if parse_result[key] == "#":
                    parse_result[key] = text

        # still could not parse - ask to rephrase
        if parse_result is None:
            return "I don't quite understand that, could you rephrase?"

        # if there is an item, try to resolve it
        if "item" in parse_result:

            item_text = parse_result["item"]

            # resolve and enhance with conceptual information
            resolved_items = self.resolve_and_enhance_item(
                parse_result["item"])

            if resolved_items is None:
                return "I don't see anything like that.\n"

            # check if we found multiple matches for a singular word
            # return for clarification on which one to use
            if resolved_items is not None and type(resolved_items) is list and len(resolved_items) > 1:
                self.util.output_debug(
                    "ITEM RESOLUTION: More than one matching item found", debug_flag=self.debug)
                concept = self.diorama.find_concept(item_text)
                if (concept is None) or (concept is not None and concept["matched-qty"] == "singular"):
                    self.util.output_debug(
                        "ITEM RESOLUTION: Concept not found or concept indicates singular word, clarification needed.", debug_flag=self.debug)
                    parse_result["item"] = "#"
                    return {"ask": "Which one?", "place-answer-into": parse_result}

            # else we found the item(s) needed to continue
            elif resolved_items is not None:
                parse_result["item"] = resolved_items

        # now assert the action
        if "action" in parse_result:
            self.assert_event(parse_result)

    def run_console(self):

        # start wth an initial description
        print("")
        description = self.core_actions.describe_current_scene()
        self.output_text(description)

        # will store info coming back from processing
        # to handle UI input and output
        result = None

        # keep looping FOREVER :)
        while True:

            # ask for what to do
            text = input(": ")
            print("")

            # engine commands
            if str.lower(text) == "debug on":
                self.debug = True
                self.diorama.debug = True
                self.core_actions.debug = True
                self.parser.debug = True
                self.output_text("debug is now on")
                continue
            elif str.lower(text) == "debug off":
                self.debug = False
                self.diorama.debug = False
                self.core_actions.debug = False
                self.parser.debug = False
                self.output_text("debug is now off")
                continue

            # process this
            result = self.process_text(text, result)

            # if there's a result, output it
            if result is not None:
                if type(result) == str:
                    self.output_text(result + "\n")
                elif "ask" in result:
                    self.output_text(result["ask"] + "\n")

    def run_inputs(self, inputs: list):
        for input in inputs:
            description = self.core_actions.describe_current_scene()
            self.output_text(description)
            print(":", input)
            self.process_text(input)
            time.sleep(2)
        description = self.core_actions.describe_current_scene()
        self.output_text(description)

    def run_test(self, test_name: str):
        for scene in self.diorama.scenes:
            if "tests" not in scene:
                continue
            for test in scene["tests"]:
                if test["test"] != test_name:
                    continue
                steps = test["steps"]
                self.run_inputs(steps)
