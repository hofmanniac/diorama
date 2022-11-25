from diorama_engine import DioramaEngine
from phrase_parser import Parser


def test_engine():
    diorama_engine = DioramaEngine()
    diorama_engine.parser.load_from_file("parsing.json")

    # process_text("load samples/inform7/ch3_1.json")
    # process_text("load samples/inform7/chapter_03/ex_002.json")
    # process_text("load samples/inform7/chapter_03/ex_003.json")
    # process_text("load samples/inform7/chapter_03/ex_004.json")
    # test_game(["s", "n", "s"])

    # process_text("load samples/inform7/chapter_03/ex_005.json")
    # test_game(["s", "e", "e", "s", "enter the feathers", "exit the feathers"])

    # process_text("load samples/inform7/chapter_03/ex_006.json")
    # process_text("load samples/inform7/chapter_03/ex_007.json")
    # process_text("load samples/inform7/chapter_03/ex_008.json")
    # process_text("load samples/inform7/chapter_03/ex_009.json")
    # process_text("load samples/inform7/chapter_03/ex_010.json")
    # diorama_engine.diorama.load_file("samples/inform7/chapter_03/ex_011.json")
    diorama_engine.diorama.load_from_file(
        "samples/inform7/chapter_03/ex_012.json")

    diorama_engine.run_console()

    # diorama_engine.run_test("43")


def test_parser():

    parser = Parser()
    parser.load_from_file("parsing.json")

    parser.run_console()


test_engine()

# test_parser()
