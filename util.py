
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
