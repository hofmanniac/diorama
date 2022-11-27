from pprint import pprint
from diorama import Diorama
from util import Util
from copy import deepcopy


class CoreActions:

    diorama = None
    util = Util()
    debug = False

    def __init__(self, diorama: Diorama):
        self.diorama = diorama

    def describe_current_scene(self) -> list:

        results = []

        # get the current location
        location = self.diorama.get_viewpoint_location()
        if location is None:
            return

        location_text = location["text"] if "text" in location else None
        if location_text is None:
            location_text = location["item"] if "item" in location else ""
        results = self.util.aggregate(
            results, "you are in " + location_text + ":\n")

        options = self.diorama.find_item_by_name("options")
        if options is None:
            options = {}
        brevity = options["brevity"] if "brevity" in options else False
        visited = location["visited"] if "visited" in location else False

        if brevity == False or visited == False:
            if "description" in location:
                description = self.diorama.evaluate(location["description"])
                results = self.util.aggregate(results, description)

        # todo - keep track of this in the actor or in a list, to support multiple actors
        location["visited"] = True

        # describe items in the location
        for scene in self.diorama.scenes:
            for item in scene["items"]:
                if "location" not in item:
                    continue
                if item["location"] == location["item"]:
                    if "description" not in item:
                        continue
                    description = self.diorama.evaluate(item["description"])
                    # added_text = True
                    results = self.util.aggregate(results, description)

        contents_description = self.describe_location_contents()
        results = self.util.aggregate(results, contents_description)

        return results

    def describe_location_contents(self) -> list:

        # get the current location
        # location = self.diorama.get_viewpoint_location()
        # if location is None:
        #     return

        # items = self.diorama.find_items_by_template(
        #     {"location": location["item"]})

        items = self.diorama.get_viewpoint_items()

        if len(items) == 0:
            return

        text = ""
        for item in items:
            if item["item"] == "player":
                continue
            item_name = item["text"] if "text" in item else item["item"]
            text += item_name + ", "
        text = str.removesuffix(text, ", ")
        if len(text) > 0:
            text = "you see " + text

        return text

    def process_enter(self, event):

        destination_text = event["item"] if "item" in event else None
        if destination_text is None:
            return

        location = self.diorama.get_viewpoint_location()
        if location is None:
            return

        # find all locations within this location
        possible_destinations = self.diorama.find_items_by_template(
            {"location": location["item"]})

        # figure out which location matches the destination
        # todo - maybe combine this into find_item_by_template?
        for possible_destination in possible_destinations:
            match_score = self.diorama.fuzzy_match_item(
                possible_destination, destination_text)
            if match_score > 0:
                self.diorama.set_attribute("player", "location",
                                           possible_destination["item"])
                break

    def process_exit(self, event):

        # not used for now, but later could add some "exiting area" events
        # origin_text = event["item"] if "item" in event else None
        # if origin_text is None:
        #     return

        location = self.diorama.get_viewpoint_location()
        if location is None:
            return

        exit_location = location["location"]
        self.diorama.set_attribute("player", "location", exit_location)

    def get_cross_direction(self, direction: str):

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

        return cross_direction

    def process_go(self, event):

        # which direction should we try to go?
        direction = event["direction"] if "direction" in event else None
        if direction is None:
            return

        # get current location
        location = self.diorama.get_viewpoint_location()
        if location is None:
            return

        # check if the new direction is in the current location
        new_location_prop = location[direction] if direction in location else None
        new_location = None

        # if the new location is an anonymous object
        if type(new_location_prop) is dict:

            new_location = deepcopy(new_location_prop)

            # instantiate the new location
            new_location = self.diorama.enhance_item_with_concept_info(
                new_location)

            # set the cross direction to the current location
            # (so the actor can return)
            cross_direction = self.get_cross_direction(direction)
            new_location[cross_direction] = location["item"]
            if "item" not in new_location:
                new_location["item"] = "#" + location["item"] + "-" + direction

        # otherwise the new location is a named location
        elif type(new_location_prop) is str:

            new_location = self.diorama.find_item_by_name(
                new_location_prop)

            # if not, check other scenes and items for cross-reference location
            if new_location is None:

                cross_direction = self.get_cross_direction(direction)

                new_location = self.diorama.find_items_by_template(
                    {cross_direction: location["item"]}, stop_after_first=True)

        # if we were able unable to resolve the new location
        if new_location is None:
            return ["You can't go in that direction."]

        # accumulate the effects of this action
        effects = []

        # process going to location effects
        if "effects" in new_location:
            for effect in new_location["effects"]:
                if not self.util.unifies(effect, event):
                    continue
                do_effects = None
                do_effects = self.util.listify(effect["do"])
                for do_effect in do_effects:
                    sub_effects = self.diorama.evaluate(do_effect)
                    effects = self.util.aggregate(effects, sub_effects)

        # move the actor there
        if type(new_location_prop) is str:
            self.diorama.set_attribute(
                "player", "location", new_location["item"])
        elif type(new_location_prop) is dict:
            self.diorama.set_attribute("player", "location", new_location)

        # describe the current scene at this new location
        description = self.describe_current_scene()
        self.util.aggregate(effects, description)

        return effects

    def process_say(self, event: dict):
        # self.output_text(event["text"])
        return event["text"]

    def process_take(self, event: dict):

        results = None

        items = self.util.listify(event["item"])

        items_taken = []
        items_not_portable = []

        for item in items:

            # if item is portable
            portable = self.diorama.get_attribute(item, "portable", False)
            if portable:
                # then change location to player
                self.diorama.set_attribute(item, "location", "player")

                # remove previous location (on, in, etc.)
                self.diorama.remove_attribute(item, "on")
                self.diorama.remove_attribute(item, "in")

                # report success
                items_taken = self.util.aggregate(items_taken, item)
            else:
                self.util.output_debug(
                    "TAKE: Item is not portable.", debug_flag=self.debug)
                items_not_portable = self.util.aggregate(
                    items_not_portable, item)

        text = ""
        if len(items_taken) > 0:
            text = "You take " + self.util.textify_list(items_taken) + "."
            results = self.util.aggregate(results, text)

        if len(items_not_portable) > 0:
            text = self.util.textify_list(items_not_portable) + " won't budge."
            text = str.replace(" " + text, " a ", " the ")
            text = str.replace(" " + text, " A ", " The ")
            text = str.strip(text)

            results = self.util.aggregate(results, text)

        return results

    def process_inventory(self, event):

        names = None
        items = self.diorama.find_items_by_template({"location": "player"})
        if items is None:
            return "You are empty handed."

        for item in items:
            if "text" in item:
                names = self.util.aggregate(names, item["text"])

        if len(names) > 0:
            text = self.util.textify_list(names)
            text = "You are carrying: " + text
            return text

    def process_examine(self, event):

        results = None

        event_item = event["item"] if "item" in event else None

        if event_item is None:
            results = self.describe_current_scene()

        else:
            items = self.util.listify(event_item)
            for item in items:
                if "description" in item:
                    description = self.diorama.evaluate(item["description"])
                    results = self.util.aggregate(results, description)
                else:
                    results = self.util.aggregate(
                        results, "you see nothing special.")

        return results

    def process_set(self, event):
        parts = str.split(event["item"], ".")
        value = self.diorama.evaluate(event["to"])
        self.diorama.set_attribute(parts[0], parts[1], value)

    def process_print(self, event):
        item = event["item"]
        pprint(item)
        print("")
