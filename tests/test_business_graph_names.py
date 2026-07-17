from ztt.business import _clone_filesystem_rule


def test_business_graph_prototype_names_are_namespaced() -> None:
    rule = {
        "name": "Mounted filesystem discovery",
        "key": "vfs.fs.discovery",
        "item_prototypes": [
            {
                "name": "Filesystem used percentage",
                "key": "vfs.fs.size[{#FSNAME},pused]",
            }
        ],
        "graph_prototypes": [
            {
                "name": "FS [{#FSLABEL}({#FSNAME})]: Space usage graph, in %",
                "graph_items": [
                    {
                        "item": {
                            "host": "WINDOWS_SYSTEM",
                            "key": "vfs.fs.size[{#FSNAME},pused]",
                        }
                    }
                ],
            }
        ],
    }

    bdd = _clone_filesystem_rule(rule, "bdd")
    oracle = _clone_filesystem_rule(rule, "oracle")

    bdd_graph = bdd["graph_prototypes"][0]
    oracle_graph = oracle["graph_prototypes"][0]

    assert bdd_graph["name"].endswith(" - BUSINESS bdd")
    assert oracle_graph["name"].endswith(" - BUSINESS oracle")
    assert bdd_graph["name"] != oracle_graph["name"]
    assert bdd_graph["graph_items"][0]["item"]["key"].startswith("ztt.business.bdd.")
    assert oracle_graph["graph_items"][0]["item"]["key"].startswith(
        "ztt.business.oracle."
    )
