import json
import copy
import time
from pprint import pprint, pformat
from termcolor import colored

loop = True

scenes = []
globals = {}
debug = False


def unifies(template: dict, candidate: dict):
    unifies = True
    for template_key in template.keys():
        if template_key in ['do', 'if', 'else', 'equals']:
            continue
        if template_key in candidate:
            if candidate[template_key] is None and template[template_key] is not None:
                unifies = False
                break
            if type(candidate[template_key]) is str:
                if template[template_key] != candidate[template_key]:
                    unifies = False
                    break
            elif type(candidate[template_key]) is dict:
                item = candidate[template_key]
                if "item" in candidate[template_key]:
                    if template[template_key] != item["item"]:
                        unifies = False
                        break
            elif type(candidate[template_key]) is list:
                item_in_list = False
                for item in candidate[template_key]:
                    if template[template_key] == item["item"]:
                        item_in_list = True
                        break
                if item_in_list == False:
                    unifies = False
                    break
        else:
            if template[template_key] == "#-":
                continue  # ok - missing data
            unifies = False
            break
    return unifies


def load_file(filename):
    if filename is None:
        return
    with open(filename) as f:
        scene = json.load(f)
        scenes.append(scene)
        # print("LOADED:", filename)


def process_look(parsed_text):
    for scene in scenes:
        for item in scene["items"]:
            print(item["item"])


def process_item_effects(event):

    effects = []

    for scene in scenes:

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

                if unifies(candidate_effect, event) == False:
                    continue

                # effect matched - add the effects
                new_effects = evaluate(candidate_effect)
                if type(new_effects) is not list:
                    new_effects = [new_effects]

                # for new_effect in new_effects:
                #     if type(new_effect) is dict:
                #         new_effect["actor"] = item["item"]

                effects = aggregate(effects, new_effects)

                # new_effects = []

                # if "if" in candidate_effect:
                #     sub_effects = process_if(candidate_effect)
                #     aggregate(new_effects, sub_effects)
                # else:
                #     do_portion = candidate_effect["do"]
                #     aggregate(new_effects, do_portion)

                # for new_effect in new_effects:
                #     if type(new_effect) is dict:
                #         new_effect["actor"] = item["item"]

                # # if len(new_effects) > 0:
                # #     output_debug(
                # #         {"event": event, "matched": candidate_effect})

                # aggregate(effects, new_effects)

    return effects


def find_item_by_name(name: str):
    for scene in scenes:
        for item in scene["items"]:
            if item["item"] == name:
                return item
    return None


def find_item_by_fuzzy_match(name: str):
    name = str.replace(name, "the ", "")
    for scene in scenes:
        for item in scene["items"]:
            if fuzzy_match(item, name):
                return item
            if "aka" in item:
                for aka_item in item["aka"]:
                    if str.lower(aka_item) == str.lower(name):
                        return item
    return None


def find_item_by_template(template: dict):
    for scene in scenes:
        for item in scene["items"]:
            if unifies(template, item):
                return item
    return None


def find_items_by_template(template: dict):
    items = []
    for scene in scenes:
        for item in scene["items"]:
            if unifies(template, item):
                items.append(item)
    return items


def get_attribute(item: dict, attribute: str):
    result = item[attribute] if attribute in item else None
    return result


def process_set(event):
    parts = str.split(event["item"], ".")
    value = evaluate(event["to"])
    update_attribute(parts[0], parts[1], value)


def output_text(message):

    messages = []
    if type(message) is str:
        messages = [message]
    elif type(message) is list:
        messages = message

    for message in messages:
        for char in message:
            print(str.upper(char), end="")
            # time.sleep(.03)
        if char != '\n':
            # print(" ", end="")
            print("")
            print("")


def output_debug(message, event: dict):
    if debug == False:
        return
    # text = pformat(event)
    # print("")
    # text = colored(text, 'green')
    # print(text)
    print("")
    print(message, ":", sep="")
    pprint(event)
    print("")


def resolve_token_value(token: str):

    parts = str.split(token, ".")

    item = None
    value = None
    polarity = True
    for part in parts:
        if item is None:
            if str.startswith(part, "!"):
                polarity = False
                part = part[1:]
            item = find_item_by_name(part)
        else:
            value = item[part] if part in item else None

    if polarity == False:
        if value is None:
            value = False
        value = not(value)

    return value


def process_if(event):

    passed = False

    if_value = evaluate(event["if"])
    if if_value == "None":
        if_value = False

    equals_clause = event["equals"] if "equals" in event else None
    if equals_clause is not None:
        equals_value = evaluate(equals_clause)
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
        return evaluate(event["do"])
    else:
        if "else" in event:
            # return event["else"]
            return evaluate(event["else"])


def aggregate(main_list: list, new_value):

    if new_value is None:
        return main_list

    if main_list is None:
        main_list = []

    if type(main_list) is not list:
        main_list = [main_list]

    if type(new_value) is list:
        main_list.extend(new_value)
    else:
        main_list.append(new_value)

    return main_list


def get_location_of(item_name: str):

    # get player
    item = find_item_by_name(item_name)
    if item is None:
        return None

    # get location
    location_name = item["location"] if "location" in item else None
    if location_name is None:
        return None

    # get that location
    location = find_item_by_name(location_name)
    return location


def update_attribute(item_name: str, attribute_name: str, value: any):
    item = find_item_by_name(item_name)
    item[attribute_name] = value


def fuzzy_match(item: dict, keyword_text: str):

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


def process_enter(event):

    destination_text = event["item"] if "item" in event else None
    if destination_text is None:
        return

    location = get_location_of("player")
    if location is None:
        return

    # find all locations within this location
    possible_destinations = find_items_by_template(
        {"location": location["item"]})

    # figure out which location matches the destination
    # todo - maybe combine this into find_item_by_template?
    for possible_destination in possible_destinations:
        is_match = fuzzy_match(possible_destination, destination_text)
        if is_match:
            update_attribute("player", "location",
                             possible_destination["item"])
            break


def process_exit(event):

    # not used for now, but later could add some "exiting area" events
    # origin_text = event["item"] if "item" in event else None
    # if origin_text is None:
    #     return

    location = get_location_of("player")
    if location is None:
        return

    exit_location = location["location"]
    update_attribute("player", "location", exit_location)


def process_go(event):

    # which direction should we try to go?
    direction = event["item"] if "item" in event else None
    if direction is None:
        return

    # get current location
    location = get_location_of("player")
    if location is None:
        return

    # check if the new direction is in the current location
    new_location_name = location[direction] if direction in location else None
    new_location = find_item_by_name(new_location_name)

    # if not, check other scenes and items for cross-reference location
    if new_location_name is None:

        cross_direction = None
        cross_direction = "south" if direction == "north" and cross_direction == None else cross_direction
        cross_direction = "north" if direction == "south" and cross_direction == None else cross_direction
        cross_direction = "east" if direction == "west" and cross_direction == None else cross_direction
        cross_direction = "west" if direction == "east" and cross_direction == None else cross_direction

        cross_direction = "northeast" if direction == "southwest" and cross_direction == None else cross_direction
        cross_direction = "southwest" if direction == "northeast" and cross_direction == None else cross_direction

        cross_direction = "northwest" if direction == "southeast" and cross_direction == None else cross_direction
        cross_direction = "southeast" if direction == "northwest" and cross_direction == None else cross_direction

        cross_direction = "up" if direction == "down" and cross_direction == None else cross_direction
        cross_direction = "down" if direction == "up" and cross_direction == None else cross_direction

        cross_direction = "inside" if direction == "outside" and cross_direction == None else cross_direction
        cross_direction = "outside" if direction == "inside" and cross_direction == None else cross_direction

        new_location = find_item_by_template(
            {cross_direction: location["item"]})

        if new_location is not None:
            new_location_name = new_location["item"]

    if new_location_name is not None and new_location is not None:

        effects = []

        # process going to location effects
        # todo - refactor this
        if "effects" in new_location:
            for effect in new_location["effects"]:
                if unifies(effect, event):
                    do_effects = None
                    if type(effect["do"]) is list:
                        do_effects = effect["do"]
                    else:
                        do_effects = [effect["do"]]

                    for do_effect in do_effects:
                        sub_effects = evaluate(do_effect)
                        effects = aggregate(effects, sub_effects)

        # move the player there
        update_attribute("player", "location", new_location_name)

        # description = describe_current_scene()
        # aggregate(effects, description)

        return effects
    else:
        return ["You can't go in that direction."]


def process_say(event: dict):
    output_text(event["text"])


def process_find_all(event: dict):
    effects = []
    template = event["find-all"]
    items = find_items_by_template(template)
    for item in items:
        actions = event["do"]
        if type(actions) is not list:
            actions = [actions]
        for action in actions:
            action_copy = copy.deepcopy(action)
            for key in action_copy.keys():
                # sub values
                # todo - quick for now, will make this better
                action_copy[key] = str.replace(
                    action_copy[key], "@item.name", item["item"])
            effects.append(action_copy)
    return effects


def listify(item):
    if item is None:
        return None
    if type(item) is list:
        return item
    else:
        return [item]


def process_examine(event):

    results = None

    event_item = event["item"] if "item" in event else None

    if event_item is None:
        results = describe_current_scene()

    else:
        items = listify(event_item)
        for item in items:
            if "description" in item:
                description = evaluate(item["description"])
                results = aggregate(results, description)

    return results


def process_event(event: dict):
    '''Executes the actions in the event / action. In general, you should use 'evaluate' instead of this function, and only use this function if you need to run a single action.'''
    output_debug("PROCESSING", event)

    if type(event) is str:
        output_text(event)
        return

    effects = []

    # process item effects - before action effects

    # process item effects - instead of action effects
    item_effects = process_item_effects(event)
    effects = aggregate(effects, item_effects)

    if len(item_effects) == 0:

        action_effects = None

        if event["action"] == "go":
            action_effects = process_go(event)
        elif event["action"] == "enter":
            action_effects = process_enter(event)
        elif event["action"] == "exit":
            action_effects = process_exit(event)
        elif event["action"] == "say":
            action_effects = process_say(event)
        elif event["action"] == "set":
            action_effects = process_set(event)
        elif event["action"] == "examine":
            action_effects = process_examine(event)

        if action_effects is None:
            action_effects = []

        effects = aggregate(effects, action_effects)

    return effects


def evaluate_text(text: str):
    tokens = str.split(text, " ")
    result = ""
    for token in tokens:
        if str.find(token, ".") > 0 and not str.endswith(token, ".") and not str.startswith(token, "."):
            token = resolve_token_value(token)
        result = result + str(token) + " "
    result = str.strip(result)
    if result == "True":
        return True
    elif result == "False":
        return False
    else:
        return result


def evaluate(value):

    results = []

    if type(value) is str:
        return evaluate_text(value)

    elif type(value) is bool:
        return value

    elif type(value) is dict:
        if "find-all" in value:
            sub_result = process_find_all(value)
        elif "if" in value:
            sub_result = process_if(value)
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
        results = aggregate(results, sub_result)

    elif type(value) is list:
        for sub_value in value:
            sub_result = evaluate(sub_value)
            results = aggregate(results, sub_result)

    if len(results) == 1:
        return results[0]
    else:
        return results


def assert_event(event: dict):
    '''Run all events and their triggered events until no additional events are triggered.'''
    event_queue = [event]

    while len(event_queue) > 0:
        queued_event = event_queue.pop(0)
        sub_effects = process_event(queued_event)
        event_queue = aggregate(event_queue, sub_effects)


def find_items_by_word(text: str):

    items = None
    effects = None

    for scene in scenes:

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
                sub_items = find_items_by_template({"isa": word_text})
                if sub_items is None:
                    continue

                # check if we found multiple matches for singular word
                if len(sub_items) > 1 and "plural-of" not in word:
                    return None, {"ask": "Which " + text + "?"}

                # else keep collecting all matched items
                else:
                    items = aggregate(items, sub_items)

    return items, effects


def find_item_by_text(text: str):

    if text is None:
        return None, None

    # find item by fuzzy match (text and akas)
    resolved_item = find_item_by_fuzzy_match(text)

    # find item by item name
    if resolved_item is None:
        resolved_item = find_item_by_name(text)

    # # pull name out of resolved
    # if resolved_item is not None:
    #     resolved_item = resolved_item["item"]

    # try by word lookups e.g. {"word": "vehicle", "aka": ["car", "truck"]}
    if resolved_item is None:
        resolved_item, effect = find_items_by_word(text)
        return resolved_item, effect

    return resolved_item, None


def parse_text(text):

    # say - just return the rest of the text
    if str.startswith(text, "say "):
        text = text[4:]
        return {"action": "say", "text": text}

    # expand shortcuts
    if text == "n" or text == "north":
        text = "go north"
    elif text == "s" or text == "south":
        text = "go south"
    elif text == "e" or text == "east":
        text = "go east"
    elif text == "w" or text == "west":
        text = "go west"
    elif text == "u" or text == "up":
        text = "go up"
    elif text == "d" or text == "down":
        text = "go down"
    elif text == "ne" or text == "northeast":
        text = "go northeast"
    elif text == "nw" or text == "northwest":
        text = "go northwest"
    elif text == "se" or text == "southeast":
        text = "go southeast"
    elif text == "sw" or text == "southwest":
        text = "go southwest"

    tokens = text.split(" ")
    action = None
    item_text = None

    for token in tokens:
        if action is None:
            action = token
        elif token == "on" or token == "off":
            action += " " + token
        elif item_text is None:
            if token == "to":
                action += + " " + token
            else:
                item_text = token
        else:
            item_text = item_text + " " + token

    if action is None:
        return None

    if action == "x" or action == "look" or action == "l":
        action = "examine"
    elif action == "walk" or action == "head":
        action = "go"

    if item_text is None:
        return {"action": action}

    return {"action": action, "item": item_text}


def process_text(text, previous_result=None):

    input_event = parse_text(text)
    output_debug(f"PARSED: '{text}'", input_event)

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
        resolved_item, effect = find_item_by_text(item_text)

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
        assert_event(input_event)


def describe_current_scene():

    results = []

    # describe the location
    location = get_location_of("player")
    if location is None:
        return

    location_text = location["text"] if "text" in location else location["item"]
    results = aggregate(results, "you are in " + location_text + ":\n")

    options = find_item_by_name("options")
    if options is None:
        options = {}
    brevity = options["brevity"] if "brevity" in options else False
    visited = location["visited"] if "visited" in location else False

    # added_text = False

    if brevity == False or visited == False:
        if "description" in location:
            description = evaluate(location["description"])
            # added_text = True
            results = aggregate(results, description)

    location["visited"] = True

    # description = resolve_value("player.location.description")
    # output_text(description)

    # describe items in the location
    for scene in scenes:
        for item in scene["items"]:
            if "location" not in item:
                continue
            if item["location"] == location["item"]:
                if "description" not in item:
                    continue
                description = evaluate(item["description"])
                # added_text = True
                results = aggregate(results, description)

    # if added_text == True:
    #     results = aggregate(results, "\n")
    return results


def run_game():

    # start wth an initial description
    print("")
    description = describe_current_scene()
    output_text(description)

    # will store info coming back from processing
    # to handle UI input and output
    result = None

    # keep looping FOREVER :)
    while True:

        # ask for what to do
        text = input(": ")
        print("")

        # process this
        result = process_text(text, result)

        # if there's a result, output it
        if result is not None:
            if type(result) == str:
                output_text(result)
            elif "ask" in result:
                output_text(result["ask"] + "\n")


def test_game(inputs: list):
    for input in inputs:
        describe_current_scene()
        print(":", input)
        process_text(input)
        time.sleep(2)
    describe_current_scene()


def run_console():

    while(loop):
        text = input("YOU: ")
        result = process_text(text)
        process_text("advance time")

# process_text("load samples/story1.json")
# process_text("start world")
# process_text("talk to naomi")
# process_text("load samples/dog.json")

# process_text("load samples/inform7/ch3_1.json")

# process_text("load samples/inform7/chapter_3/ex_002.json")
# process_text("start game")

# process_text("load samples/inform7/chapter_3/ex_003.json")

# process_text("load samples/inform7/chapter_3/ex_004.json")
# test_game(["s", "n", "s"])

# process_text("load samples/inform7/chapter_3/ex_005.json")
# test_game(["s", "e", "e", "s", "enter the feathers", "exit the feathers"])

# process_text("load samples/inform7/chapter_3/ex_006.json")

# process_text("load samples/inform7/chapter_3/ex_007.json")

# process_text("load samples/inform7/chapter_3/ex_008.json")

# process_text("load samples/inform7/chapter_3/ex_009.json")


# process_text("load samples/inform7/chapter_3/ex_010.json")

# load_file("rules.json")
load_file("samples/inform7/chapter_3/ex_011.json")
# process_text("load rules.json")
# process_text("load samples/inform7/chapter_3/ex_011.json")


run_game()


# run_console()
