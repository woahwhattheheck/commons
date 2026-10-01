# SPDX-License-Identifier: Apache-2.0
"""Rollback partially installed native MarketPath caches on constructor failure.

Source-only, method-scoped composition. This is NOT an unconditional guarantee
against interruption after constructor return or during rollback itself.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
from pathlib import Path

PREIMAGE = '''    def __init__(self, item, inventory, params, shops, config, now, end):
        self.item,self.inventory,self.params=item,inventory,params
        self.shops,self.config,self.now,self.end=shops,config,now,end
        self.quote=lru_cache(maxsize=2048)(lambda inv:m.market_price(item,inv,params))
        self.single=lru_cache(maxsize=8192)(self._single)
        self.joint=lru_cache(maxsize=8192)(self._joint)
'''
POSTIMAGE = '''    def __init__(self, item, inventory, params, shops, config, now, end):
        try:
            self.item,self.inventory,self.params=item,inventory,params
            self.shops,self.config,self.now,self.end=shops,config,now,end
            self.quote=lru_cache(maxsize=2048)(lambda inv:m.market_price(item,inv,params))
            self.single=lru_cache(maxsize=8192)(self._single)
            self.joint=lru_cache(maxsize=8192)(self._joint)
        except BaseException:
            # A deadline can arrive after single owns its bound-self callback
            # but before the caller receives a model to dispose. Drop only the
            # three partially installed caches, then propagate the SAME error.
            # No global GC, policy change, or cleanup of another live model.
            self.__dict__.pop('joint', None)
            self.__dict__.pop('single', None)
            self.__dict__.pop('quote', None)
            raise
'''


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def init_span(source: str) -> tuple[int, int, str]:
    """Return the exact, undecorated constructor of one top-level MarketPath."""
    tree = ast.parse(source)
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'MarketPath']
    if len(classes) != 1:
        raise ValueError('expected one top-level MarketPath')
    cls = classes[0]
    if cls.decorator_list:
        raise ValueError('decorated MarketPath is not an authenticated consumer')
    nodes = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
             and n.name == '__init__']
    if len(nodes) != 1 or isinstance(nodes[0], ast.AsyncFunctionDef) or nodes[0].decorator_list:
        raise ValueError('expected one synchronous undecorated MarketPath.__init__')
    node = nodes[0]
    lines = source.splitlines(keepends=True)
    start = sum(map(len, lines[:node.lineno - 1]))
    end = sum(map(len, lines[:node.end_lineno]))
    return start, end, source[start:end]


def transform(source: str) -> str:
    """Authenticate the owned method and leave every other byte untouched."""
    if not isinstance(source, str):
        raise TypeError('source must be decoded UTF-8 text')
    start, end, current = init_span(source)
    if current == POSTIMAGE:
        return source
    if current != PREIMAGE:
        raise ValueError('unrecognized MarketPath constructor; explicit rebase required')
    result = source[:start] + POSTIMAGE + source[end:]
    compile(result, '<MarketPath constructor rollback>', 'exec')
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error('source and output must differ; never patch production in place')
    try:
        result = transform(args.source.read_bytes().decode('utf-8')).encode('utf-8')
        # Refuse to overwrite another builder's candidate.
        with args.output.open('xb') as handle:
            handle.write(result)
    except (OSError, UnicodeError, SyntaxError, ValueError) as exc:
        parser.exit(2, f'constructor rollback: {exc}\n')
    print(sha256(result))


if __name__ == '__main__':
    main()
