from __future__ import annotations

import ast
from pathlib import Path


APP_PATH = Path(__file__).parents[1] / "dashboard" / "app.py"


def test_streamlit_cache_does_not_receive_the_supabase_secret() -> None:
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    cached_function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "cached_data"
    )

    parameter_names = [argument.arg for argument in cached_function.args.args]
    assert parameter_names == [
        "supabase_url",
        "supabase_key_configured",
    ]

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "cached_data":
            continue
        assert all(not isinstance(argument, ast.Name) or argument.id != "supabase_key" for argument in node.args)
