import json
import copy
import time
from pprint import pprint, pformat
from termcolor import colored

loop = True

scenes = []
globals = {}


def parse_text(text):

    # expand shortcuts
    if text == "n":
        text = "go north"
    elif text == "s":
        text = "go south"
    elif text == "e":
        text = "go east"
    elif text == "w":
        text = "go west"

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

    result = {"action": action, "item": item}
    return result


def unifies(template: dict, candidate: dict):
    unifies = True
    for template_key in template.keys():
        if template_key == "do":
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

                do_portion = candidate_effect["do"]

                new_effects = []
                if type(do_portion) is dict:
                    new_effects.append(do_portion)
                elif type(do_portion) is list:
                    new_effects.extend(do_portion)
                for new_effect in new_effects:
                    if type(new_effect) is dict:
                        new_effect["actor"] = item["item"]

                # if len(new_effects) > 0:
                #     output_debug(
                #         {"event": event, "matched": candidate_effect})

                effects.extend(new_effects)

    return effects


def find_item_by_name(name: str):
    for scene in scenes:
        for item in scene["items"]:
            if item["item"] == name:
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
    item_name = event["item"]
    globals[item_name] = event["to"]


def process_event_old(event):

    if type(event) is str:
        output_text(event)
        return None

    action = get_attribute(event, "action")

    if action is None:
        return None

    if action == "load":
        load_scene(event)
    elif action == "look":
        process_look(event)
    elif action == "go":
        process_go(event)
    elif action == "set":
        process_set(event)
    elif action == "say":
        text = f"{event['actor']}: \"{event['phrase']}\""
        output_text(text)
    else:
        if "actor" in event:
            if "item" in event:
                output_text(
                    f'{event["actor"]}: {event["action"]} {event["item"]}')
            elif "prop" in event:
                output_text(
                    f'{event["actor"]}: {event["action"]} {event["prop"]}')
    effects = process_item_effects(event)

    new_effects = []
    for effect in effects:
        # print("EFFECT:", effect)
        sub_effects = process_event_old(effect)
        if sub_effects is None:
            continue
        if len(sub_effects) == 0:
            continue
        new_effects.extend(sub_effects)

    return new_effects


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
        print(" ", end="")
    print("")


def output_debug(event: dict):
    # pass
    text = pformat(event)
    print("")
    text = colored(text, 'green')
    print(text)
    print("")


def process_text(text):

    print("")
    input_event = parse_text(text)
    # print(f"PARSED: '{text}' AS {event}")
    pprint(input_event)

    assert_event(input_event)


def process_if(event):

    if_part = event["if"]
    parts = str.split(if_part, ".")

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

    if value is None:
        value = False

    if polarity == False:
        value = not(value)

    if type(value) is bool:
        if value:
            return event["do"]


def evaluate(value):

    if type(value) is str:
        return value

    elif type(value) is dict:
        if "if" in value:
            effects = process_if(value)
            return effects

    elif type(value) is list:
        sub_results = []
        for sub_value in value:
            sub_result = evaluate(sub_value)
            if sub_result is not None:
                if type(sub_result) is list:
                    sub_results.extend(sub_result)
                else:
                    sub_results.append(sub_result)
        return sub_results


def run_console():

    while(loop):
        text = input("YOU: ")
        process_text(text)
        process_text("advance time")


def describe_current_scene():

    # describe the location
    location = get_location_of("player")
    if location is None:
        return

    location_text = location["text"] if "text" in location else location["item"]
    output_text(location_text)

    options = find_item_by_name("options")
    if options is None:
        options = {}
    brevity = options["brevity"] if "brevity" in options else False
    visited = location["visited"] if "visited" in location else False

    if brevity == False or visited == False:
        # description = location["description"]
        description = evaluate(location["description"])
        output_text(description)

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
                description = item["description"]
                output_text(description)


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

    if new_location_name is not None:
        update_attribute("player", "location", new_location_name)
    else:
        return "You can't go in that direction."


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


def process_say(event: dict):
    output_text(event["text"])


def assert_event(event: dict):
    '''Run all events and their triggered events until no additional events are triggered.'''
    event_queue = [event]

    for queued_event in event_queue:
        sub_effects = process_event(queued_event)
        if sub_effects is None:
            continue
        event_queue.extend(sub_effects)


def process_event(event: dict):

    effects = None

    if "find-all" in event:
        effects = process_find_all(event)
    elif event["action"] == "load":
        effects = load_scene(event)
    elif event["action"] == "go":
        effects = process_go(event)
    elif event["action"] == "say":
        effects = process_say(event)
    else:
        effects = process_item_effects(event)

    if effects is not None and type(effects) is not list:
        if type(effects) is str:
            effects = {"action": "say", "text": effects}
        effects = [effects]

    return effects


def run_game():

    while True:
        describe_current_scene()
        text = input(": ")
        process_text(text)


# process_text("load samples/story1.json")
# process_text("start world")
# process_text("talk to naomi")
# process_text("load samples/dog.json")

# process_text("load samples/inform7/ch3_1.json")

# process_text("load samples/inform7/ex_002.json")
# process_text("start game")

# process_text("load samples/inform7/ex_003.json")

process_text("load samples/inform7/ex_004.json")

run_game()

# run_console()
