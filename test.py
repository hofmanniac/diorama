from diorama_engine import DioramaEngine
from phrase_parser import Parser


def test_engine():
    diorama_engine = DioramaEngine()
    diorama_engine.load_parser("parsing.json")

    # file = "samples/inform7/ch3_1.json"
    # file = "samples/inform7/chapter_03/ex_002.json"
    # file = "samples/inform7/chapter_03/ex_003.json"
    # file = "samples/inform7/chapter_03/ex_004.json"
    # test_game(["s", "n", "s"])

    # file = "samples/inform7/chapter_03/ex_005.json"
    # test_game(["s", "e", "e", "s", "enter the feathers", "exit the feathers"])

    # file = "samples/inform7/chapter_03/ex_006.json"
    # file = "samples/inform7/chapter_03/ex_007.json"
    # file = "samples/inform7/chapter_03/ex_008.json"
    # file = "samples/inform7/chapter_03/ex_009.json"
    # file = "samples/inform7/chapter_03/ex_010.json"
    # diorama_engine.diorama.load_file("samples/inform7/chapter_03/ex_011.json")

    # file = "samples/inform7/chapter_03/ex_012.json"
    # file = "samples/inform7/chapter_04/ex_043.json"
    file = "samples/inform7/chapter_04/ch04_02.json"

    diorama_engine.load_scene(file)

    diorama_engine.run_console()

    # diorama_engine.run_test("43")


def test_parser():

    parser = Parser()
    parser._load_from_file("parsing.json")

    parser.run_console()


test_engine()

# test_parser()
