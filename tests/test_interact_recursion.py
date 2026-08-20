import importlib
import sys
import types
import unittest
from unittest.mock import Mock, patch


class FakeSignal:
    def __init__(self, *args, **kwargs):
        self.values = []

    def emit(self, value=None):
        self.values.append(value)

    def connect(self, callback):
        self.callback = callback


class FakeThread:
    def __init__(self, *args, **kwargs):
        pass


qtcore = types.ModuleType("PySide6.QtCore")
qtcore.QThread = FakeThread
qtcore.Signal = FakeSignal
pyside = types.ModuleType("PySide6")
pyside.QtCore = qtcore
sys.modules.setdefault("PySide6", pyside)
sys.modules.setdefault("PySide6.QtCore", qtcore)

extra_module = importlib.import_module("BiliWorker.extra")


class RecursionGetListTests(unittest.TestCase):
    def make_worker(self):
        args = {
            "Address": "https://www.bilibili.com/video/BV1xx411c7mD",
            "useCookie": False,
            "cookie": "",
            "useProxy": False,
            "Proxy": {},
            "ProxyAuth": {"inuse": False},
            "imgcache": False,
            "cache_path": "C:/temp",
        }
        worker = extra_module.biliWorker_interact(args)
        worker.now_interact = {
            "bvid": "BVtest",
            "graph_version": "1",
            "node_id": "root",
            "cid": "1",
        }
        return worker

    def fake_get_factory(self, graph, long_chain_len=0):
        def fake_get(url, headers=None, params=None, timeout=None, proxies=None, auth=None):
            node_id = params["node_id"]
            resp = Mock()
            if node_id in graph:
                resp.json.return_value = {"data": {"edges": {"choices": graph[node_id]}}}
            elif long_chain_len and node_id and node_id.startswith("chain"):
                idx = int(node_id[5:])
                if idx + 1 < long_chain_len:
                    resp.json.return_value = {
                        "data": {
                            "edges": {
                                "choices": [
                                    {"node_id": "chain{}".format(idx + 1), "cid": str(100 + idx), "option": "next"},
                                ]
                            }
                        }
                    }
                else:
                    resp.json.return_value = {"data": {"edges": {"choices": []}}}
            else:
                resp.json.return_value = {"data": {}}
            return resp

        return fake_get

    def test_depth_first_order_matches_original_recursion_semantics(self):
        worker = self.make_worker()
        worker.change_method(2, cur_node_id="root", deep=-1)
        graph = {
            "root": [{"node_id": "A", "cid": "10", "option": "goA"}],
            "A": [{"node_id": "B", "cid": "11", "option": "goB"}],
        }
        with patch.object(extra_module.request, "get", side_effect=self.fake_get_factory(graph)):
            result = worker.interact_nodeList()

        self.assertEqual(result["node_id"], "root")
        node_a = result["choices"]["goA"]
        self.assertEqual(node_a["node_id"], "A")
        node_b = node_a["choices"]["goB"]
        self.assertEqual(node_b["node_id"], "B")

        messages = [m for m in worker.business_info.values if "-->" in str(m)]
        self.assertTrue(messages[0].endswith("goA"))
        self.assertTrue(messages[1].endswith("goB"))

        statuses = worker.rthread_status.values
        self.assertEqual(statuses[0]["deep"], 1)
        self.assertEqual(statuses[0]["node_name"], "goA")
        self.assertEqual(statuses[1]["deep"], 2)
        self.assertEqual(statuses[1]["node_name"], "goB")

    def test_cyclic_node_is_marked_and_not_re_expanded(self):
        worker = self.make_worker()
        worker.change_method(2, cur_node_id="root", deep=-1)
        graph = {
            "root": [{"node_id": "A", "cid": "10", "option": "goA"}],
            "A": [{"node_id": "B", "cid": "11", "option": "goB"}],
            "B": [{"node_id": "A", "cid": "10", "option": "backToA"}],
        }
        with patch.object(extra_module.request, "get", side_effect=self.fake_get_factory(graph)):
            result = worker.interact_nodeList()

        node_b = result["choices"]["goA"]["choices"]["goB"]
        back = node_b["choices"]["backToA"]
        self.assertTrue(back.get("cycle"))
        self.assertNotIn("choices", back)

        messages = [m for m in worker.business_info.values if "环形节点" in str(m)]
        self.assertEqual(len(messages), 1)

    def test_deep_chain_does_not_raise_recursion_error(self):
        worker = self.make_worker()
        worker.change_method(2, cur_node_id="root", deep=-1)
        chain_len = 3000
        graph = {
            "root": [{"node_id": "chain0", "cid": "20", "option": "start"}],
        }
        with patch.object(
            extra_module.request,
            "get",
            side_effect=self.fake_get_factory(graph, long_chain_len=chain_len),
        ):
            result = worker.interact_nodeList()

        node = result["choices"]["start"]
        depth = 1
        while node.get("choices"):
            key = next(iter(node["choices"]))
            node = node["choices"][key]
            depth += 1
        self.assertGreaterEqual(depth, chain_len - 1)

    def test_stop_thread_flag_halts_traversal_without_error(self):
        worker = self.make_worker()
        worker.change_method(2, cur_node_id="root", deep=-1)
        graph = {
            "root": [{"node_id": "A", "cid": "10", "option": "goA"}],
            "A": [{"node_id": "B", "cid": "11", "option": "goB"}],
        }

        call_count = {"n": 0}
        real_fake_get = self.fake_get_factory(graph)

        def fake_get(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] > 1:
                worker.kill_rthread()
            return real_fake_get(*args, **kwargs)

        with patch.object(extra_module.request, "get", side_effect=fake_get):
            result = worker.interact_nodeList()

        self.assertIn("choices", result)
        self.assertIn("goA", result["choices"])


if __name__ == "__main__":
    unittest.main()