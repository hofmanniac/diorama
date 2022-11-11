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


def unifies(fact: dict, candidate: dict):
    unifies = True
    for key in fact.keys():
        if key == "do":
            continue
        if key in candidate:
            if fact[key] != candidate[key]:
                unifies = False
                break
        else:
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
            print(item["name"])


def process_item_effects(event):

    effects = []

    for scene in scenes:

        # look for item effects
        for item in scene["items"]:

            # if no effects - keep going
            if "effects" not in item:
                continue

            item_name = item["name"]

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
                        new_effect["actor"] = item["name"]

                if len(new_effects) > 0:
                    output_debug(
                        {"event": event, "matched": candidate_effect})

                effects.extend(new_effects)

    return effects


def find_item_by_name(name: str):
    for scene in scenes:
        for item in scene["items"]:
            if item["name"] == name:
                return item
    return None


def find_item_by_template(template: dict):
    for scene in scenes:
        for item in scene["items"]:
            if unifies(template, item):
                return item
    return None


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
        sub_effects = process_event(effect)
        if sub_effects is None:
            continue
        if len(sub_effects) == 0:
            continue
        new_effects.extend(sub_effects)

    return new_effects


def output_text(text: str):
    for char in text:
        print(str.upper(char), end="")
        time.sleep(.03)
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
    event = parse_text(text)
    # print(f"PARSED: '{text}' AS {event}")

    process_event(event)


# def resolve_value(path: str):
#     parts = str.split(path, '.')
#     current = None
#     for part in parts:
#         if current is None:
#             item = find_item_by_name(part)
#         else:
#             prop =


def run_console():

    while(loop):
        text = input("YOU: ")
        process_text(text)
        process_text("advance time")


def describe_current_scene():

    # describe the location
    location = get_location_of("player")
    description = location["description"]
    output_text(description)

    # description = resolve_value("player.location.description")
    # output_text(description)

    # describe items in the location
    for scene in scenes:
        for item in scene["items"]:
            if "location" not in item:
                continue
            if item["location"] == location["name"]:
                if "description" not in item:
                    continue
                description = item["description"]
                output_text(description)


def get_location_of(item_name: str):

    # get player's location
    item = find_item_by_name(item_name)
    location_name = item["location"]

    # describe the location
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

    # check if the new direction is in the current location
    new_location_name = location[direction] if direction in location else None

    # if not, check other scenes and items for cross-reference location
    if new_location_name is None:
        cross_direction = None
        cross_direction = "south" if direction == "north" and cross_direction == None else cross_direction
        cross_direction = "north" if direction == "south" and cross_direction == None else cross_direction
        cross_direction = "east" if direction == "west" and cross_direction == None else cross_direction
        cross_direction = "west" if direction == "east" and cross_direction == None else cross_direction

        new_location = find_item_by_template(
            {cross_direction: location["name"]})

        if new_location is not None:
            new_location_name = new_location["name"]

    if new_location_name is not None:
        update_attribute("player", "location", new_location_name)


def process_event(event: dict):

    if event["action"] == "load":
        load_scene(event)
    elif event["action"] == "go":
        process_go(event)


def run_game():

    while True:
        describe_current_scene()
        text = input(": ")
        event = parse_text(text)
        pprint(event)
        process_event(event)


# process_text("load samples/story1.json")
# process_text("start world")
# process_text("talk to naomi")
# process_text("load samples/dog.json")
process_text("load samples/inform7/ch3_1.json")

run_game()

# run_console()
