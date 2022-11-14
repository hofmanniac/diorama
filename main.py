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
            if template[template_key] != candidate[template_key]:
                unifies = False
                break
        else:
            if template[template_key] == "#-":
                continue  # ok - missing data
            unifies = False
            break
    return unifies


def load_scene(parsed_text):
    filename = parsed_text["item"]
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

                for new_effect in new_effects:
                    if type(new_effect) is dict:
                        new_effect["actor"] = item["item"]

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
    for scene in scenes:
        for item in scene["items"]:
            if fuzzy_match(item, name):
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
    value = event["to"]
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
            time.sleep(.03)
        if char != '\n':
            print(" ", end="")
    # print("")


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


def process_examine(event):
    item = find_item_by_fuzzy_match(event["item"])
    if item is None:
        return
    if "description" in item:
        description = evaluate(item["description"])
        return description


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

        if event["action"] == "load":
            action_effects = load_scene(event)
        elif event["action"] == "go":
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

    elif type(value) is dict:
        if "find-all" in value:
            sub_result = process_find_all(value)
        elif "if" in value:
            sub_result = process_if(value)
        elif "action" in value:
            sub_result = value["do"]
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

    # for queued_event in event_queue:
    #     sub_effects = process_event(queued_event)
    #     # sub_effects = evaluate(queued_event)
    #     new_items = aggregate(event_queue, sub_effects)
    #     event_queue.extend(new_items)


def parse_text(text):

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
    item = None

    for token in tokens:
        if action is None:
            action = token
        elif item is None:
            if token == "to":
                action = action + " " + token
            else:
                item = token
        else:
            item = item + " " + token

    result = {"action": action, "item": item}
    return result


def process_text(text):

    # print("")
    input_event = parse_text(text)
    # print(f"PARSED: '{text}' AS {event}")
    # pprint(input_event)

    # if "item" in input_event:
    #     input_item = input_event["item"]
    #     item = find_item_by_name(input_item)
    #     if item is None:
    #         item = find_item_by_fuzzy_match(input_item)
    #     if item is not None:
    #         input_event["referenced_item"] = input_item
    #         input_event["item"] = item["item"]

    assert_event(input_event)


def describe_current_scene():

    results = []

    # describe the location
    location = get_location_of("player")
    if location is None:
        return

    location_text = location["text"] if "text" in location else location["item"]
    results = aggregate(results, location_text + "\n")

    options = find_item_by_name("options")
    if options is None:
        options = {}
    brevity = options["brevity"] if "brevity" in options else False
    visited = location["visited"] if "visited" in location else False

    added_text = False

    if brevity == False or visited == False:
        if "description" in location:
            description = evaluate(location["description"])
            added_text = True
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
                added_text = True
                results = aggregate(results, description)

    if added_text == True:
        results = aggregate(results, "\n")
    return results


def run_game():

    while True:
        print("")
        description = describe_current_scene()
        output_text(description)
        text = input(": ")
        print("")
        process_text(text)
        print("")


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
        process_text(text)
        process_text("advance time")

# process_text("load samples/story1.json")
# process_text("start world")
# process_text("talk to naomi")
# process_text("load samples/dog.json")

# process_text("load samples/inform7/ch3_1.json")

# process_text("load samples/inform7/ex_002.json")
# process_text("start game")


# process_text("load samples/inform7/ex_003.json")

# process_text("load samples/inform7/ex_004.json")
# test_game(["s", "n", "s"])

# process_text("load samples/inform7/ex_005.json")
# test_game(["s", "e", "e", "s", "enter the feathers", "exit the feathers"])

# process_text("load samples/inform7/ex_006.json")

process_text("load samples/inform7/ex_007.json")

# process_text("load samples/inform7/ex_008.json")


run_game()


# run_console()
