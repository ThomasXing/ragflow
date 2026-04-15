#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
"""
Unit test package initialization

Install stubs for heavy dependencies before running tests.
"""

import importlib.util
import sys
import types
import warnings

# Suppress pkg_resources deprecation warning
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API.*",
    category=UserWarning,
)


def _make_stub_getattr(module_name):
    """Create a stub __getattr__ for modules that should not be used in tests."""
    def __getattr__(attr_name):
        message = f"{module_name}.{attr_name} is stubbed in tests"

        class _Stub:
            def __init__(self, *_args, **_kwargs):
                raise RuntimeError(message)

            def __call__(self, *_args, **_kwargs):
                raise RuntimeError(message)

            def __getattr__(self, _name):
                raise RuntimeError(message)

        setattr(sys.modules[module_name], attr_name, _Stub)
        return _Stub

    return __getattr__


def _install_rag_llm_stubs():
    """Install stubs for rag.llm modules to avoid loading heavy dependencies."""
    rag_llm = sys.modules.get("rag.llm")
    if rag_llm is not None and getattr(rag_llm, "_rag_llm_stubbed", False):
        return

    # Create rag package if not exists
    try:
        rag_pkg = importlib.import_module("rag")
    except Exception:
        rag_pkg = types.ModuleType("rag")
        rag_pkg.__path__ = []
        rag_pkg.__package__ = "rag"
        rag_pkg.__file__ = __file__
        sys.modules["rag"] = rag_pkg

    # Create rag.llm stub
    llm_pkg = types.ModuleType("rag.llm")
    llm_pkg.__path__ = []
    llm_pkg.__package__ = "rag.llm"
    llm_pkg.__file__ = __file__
    sys.modules["rag.llm"] = llm_pkg
    rag_pkg.llm = llm_pkg

    llm_pkg.__getattr__ = _make_stub_getattr("rag.llm")

    # Stub submodules
    for submodule in ("cv_model", "chat_model", "embedding_model", "rerank_model", "seq2txt_model", "tts_model", "ocr_model"):
        full_name = f"rag.llm.{submodule}"
        sub_mod = sys.modules.get(full_name)
        if sub_mod is None or not isinstance(sub_mod, types.ModuleType):
            sub_mod = types.ModuleType(full_name)
            sys.modules[full_name] = sub_mod
        sub_mod.__package__ = "rag.llm"
        sub_mod.__file__ = __file__
        sub_mod.__getattr__ = _make_stub_getattr(full_name)
        setattr(llm_pkg, submodule, sub_mod)

    llm_pkg._rag_llm_stubbed = True


def _install_deepdoc_stubs():
    """Install stubs for deepdoc modules."""
    # Create deepdoc stub if needed
    if "deepdoc" not in sys.modules:
        deepdoc_pkg = types.ModuleType("deepdoc")
        deepdoc_pkg.__path__ = []
        deepdoc_pkg.__package__ = "deepdoc"
        sys.modules["deepdoc"] = deepdoc_pkg

    # Create deepdoc.parser stub
    if "deepdoc.parser" not in sys.modules:
        parser_pkg = types.ModuleType("deepdoc.parser")
        parser_pkg.__path__ = []
        parser_pkg.__package__ = "deepdoc.parser"
        sys.modules["deepdoc.parser"] = parser_pkg
        sys.modules["deepdoc"].parser = parser_pkg


def _install_scholarly_stub():
    """Install stub for scholarly module."""
    if "scholarly" in sys.modules:
        return
    stub = types.ModuleType("scholarly")

    def _stub(*_args, **_kwargs):
        raise RuntimeError("scholarly is stubbed in tests")

    stub.scholarly = _stub
    sys.modules["scholarly"] = stub


# Install all stubs at import time
_install_rag_llm_stubs()
_install_deepdoc_stubs()
_install_scholarly_stub()
