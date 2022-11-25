import copy
import time
from pprint import pprint, pformat
from termcolor import colored
from phrase_parser import Parser
from core_actions import CoreActions
from diorama import Diorama
from util import Util


class DioramaEngine:

    diorama = Diorama()
    globals = {}
    debug = False
    parser = Parser()
    core_actions = CoreActions(diorama)
    util = Util()

    def __init__(self) -> None:
        pass

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
                # time.sleep(.03)
            if len(message) > 0 and char != '\n':
                # print(" ", end="")
                print("")
                print("")

    def output_debug(self, message, event: dict):
        if self.debug == False:
            return
        # text = pformat(event)
        # print("")
        # text = colored(text, 'green')
        # print(text)
        print("")
        print(message, ":", sep="")
        pprint(event)
        print("")

    def process_event(self, event: dict):
        '''Executes the actions in the event / action. In general, you should use 'evaluate' instead of this function, and only use this function if you need to run a single action.'''
        self.output_debug("PROCESSING", event)

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

    def process_text(self, text, previous_result=None):

        input_event = self.parser.parse_text(text)
        # input_event = parse_text(text)
        self.output_debug(f"PARSED: '{text}'", input_event)

        # if an ask came back, send it back to the caller immediately
        # if input_event is not None and "ask" in input_event:
        #     return input_event

        # if could not parse the text and an ask exists
        # try sticking the text into that and use it as the event
        if input_event is None and previous_result is not None:
            if type(previous_result) is not dict:
                pass
            if "ask" not in previous_result:
                pass
            input_event = previous_result["place-answer-into"]
            for key in input_event.keys():
                if input_event[key] == "#":
                    input_event[key] = text

        # if there is an item, try to resolve it
        if "item" in input_event:

            # try to resolve the item referenced
            item_text = input_event["item"]
            resolved_item, effect = self.diorama.find_item_by_text(item_text)

            # if not able to resolve because a new ask occured (need more info to continue)
            if effect is not None and "ask" in effect:
                input_event["item"] = "#"
                effect["place-answer-into"] = input_event
                return effect

            # if item is still not resolved
            if resolved_item is None:
                return "I don't see anything like that."

            input_event["item"] = resolved_item

        # now assert the action
        if "action" in input_event:
            self.assert_event(input_event)

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
                self.parser.debug = True
                self.output_text("debug is now on")
                continue
            elif str.lower(text) == "debug off":
                self.debug = False
                self.parser.debug = False
                self.output_text("debug is now off")
                continue

            # process this
            result = self.process_text(text, result)

            # if there's a result, output it
            if result is not None:
                if type(result) == str:
                    self.output_text(result)
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
