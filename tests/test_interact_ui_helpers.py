import unittest

from BiliModule.interact_utils import count_chosen_nodes


class CountChosenNodesTests(unittest.TestCase):
    def test_empty_tree(self):
        self.assertEqual(count_chosen_nodes({}), 0)
        self.assertEqual(count_chosen_nodes(None), 0)

    def test_only_parent_selected(self):
        tree = {
            "root": {
                "isChoose": True,
                "cid": "1",
                "choices": {
                    "child": {"isChoose": False, "cid": "2"},
                },
            }
        }
        self.assertEqual(count_chosen_nodes(tree), 1)

    def test_only_child_selected(self):
        tree = {
            "root": {
                "isChoose": False,
                "cid": "1",
                "choices": {
                    "child": {"isChoose": True, "cid": "2"},
                },
            }
        }
        self.assertEqual(count_chosen_nodes(tree), 1)

    def test_all_selected(self):
        tree = {
            "root": {
                "isChoose": True,
                "cid": "1",
                "choices": {
                    "left": {
                        "isChoose": True,
                        "cid": "2",
                        "choices": {
                            "leaf": {"isChoose": True, "cid": "3"},
                        },
                    },
                    "right": {"isChoose": True, "cid": "4"},
                },
            }
        }
        self.assertEqual(count_chosen_nodes(tree), 4)


if __name__ == "__main__":
    unittest.main()
