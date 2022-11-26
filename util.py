
class Util:

    def aggregate(self, main_list: list, new_value):

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

    def unifies(self, template: dict, candidate: dict) -> bool:
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

    def listify(self, item):
        if item is None:
            return None
        if type(item) is list:
            return item
        else:
            return [item]

    def output_debug(self, *args, debug_flag, newline=True):
        if debug_flag == False:
            return
        # text = pformat(event)
        if newline:
            print("")
        # text = colored(text, 'green')
        # print(text)
        print(*args)

    def textify_list(self, items: list, conjunction="and"):

        if items is None:
            return ""

        if len(items) == 1:
            return self.get_text(items[0])

        if len(items) == 2:
            return self.get_text(items[0]) + " and " + self.get_text(items[1])

        text = str.join(",", items[:-1])
        text += ", " + conjunction + " " + self.get_text(items[-1])
        return text

    def get_text(self, item):
        if type(item) is str:
            return item
        elif type(item) is dict:
            if "text" in item:
                return item["text"]
