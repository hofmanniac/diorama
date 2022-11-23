from diorama_engine import DioramaEngine
from phrase_parser import Parser

def test_engine():
    diorama_engine = DioramaEngine()
    diorama_engine.use_parser("parsing.json")

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
    diorama_engine.load_file("samples/inform7/chapter_3/ex_011.json")
    # process_text("load rules.json")
    # process_text("load samples/inform7/chapter_3/ex_011.json")

    diorama_engine.run_console()

    # run_console()

def test_parser():
    
    parser = Parser()
    parser.load_file("parsing.json")
    
    parser.run_console()
    
# test_engine()

test_parser()

