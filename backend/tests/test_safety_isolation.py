"""Import-boundary test: safety/ must never import an ML/LLM library.

The architecture's core safety property (Section 6.6 of the spec) is that the
deterministic rules layer cannot be influenced by ML output. If this test ever
fails, someone has quietly coupled the safety gate to a model.
"""

import ast
from pathlib import Path

FORBIDDEN_MODULES = {
    "sklearn",
    "xgboost",
    "lifelines",
    "shap",
    "scipy",
    "statsmodels",
    "openai",
    "anthropic",
}

SAFETY_DIR = Path(__file__).resolve().parent.parent / "app" / "safety"


def _imported_root_modules(source: str) -> set[str]:
    tree = ast.parse(source)
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".")[0])
    return roots


def test_safety_module_has_no_ml_or_llm_imports():
    violations = {}
    for py_file in SAFETY_DIR.rglob("*.py"):
        imported = _imported_root_modules(py_file.read_text())
        hit = imported & FORBIDDEN_MODULES
        if hit:
            violations[str(py_file)] = hit

    assert not violations, f"safety/ imported forbidden ML/LLM modules: {violations}"
