# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union
from weakref import ref

import anki.buildinfo
from anki._backend.generated import RustBackendGenerated
from anki.dbproxy import Row as DBRow
from anki.dbproxy import ValueForDB
from anki.errors import backend_exception_to_pylib
from anki.utils import from_json_bytes, to_json_bytes

from . import backend_pb2 as pb
from . import rsbridge
from .fluent import GeneratedTranslations, LegacyTranslationEnum

# pylint: disable=c-extension-no-member
assert rsbridge.buildhash() == anki.buildinfo.buildhash


class RustBackend(RustBackendGenerated):
    """
    Python bindings for Anki's Rust libraries.

    Please do not access methods on the backend directly - they may be changed
    or removed at any time. Instead, please use the methods on the collection
    instead. Eg, don't use col._backend.all_deck_config(), instead use
    col.decks.all_config()

    If you need to access a backend method that is not currently accessible
    via the collection, please send through a pull request that adds a
    public method.
    """

    def __init__(
        self,
        langs: Optional[List[str]] = None,
        server: bool = False,
    ) -> None:
        # pick up global defaults if not provided
        if langs is None:
            langs = [anki.lang.currentLang]

        init_msg = pb.BackendInit(
            preferred_langs=langs,
            server=server,
        )
        self._backend = rsbridge.open_backend(init_msg.SerializeToString())

    def db_query(
        self, sql: str, args: Sequence[ValueForDB], first_row_only: bool
    ) -> List[DBRow]:
        return self._db_command(
            dict(kind="query", sql=sql, args=args, first_row_only=first_row_only)
        )

    def db_execute_many(self, sql: str, args: List[List[ValueForDB]]) -> List[DBRow]:
        return self._db_command(dict(kind="executemany", sql=sql, args=args))

    def db_begin(self) -> None:
        return self._db_command(dict(kind="begin"))

    def db_commit(self) -> None:
        return self._db_command(dict(kind="commit"))

    def db_rollback(self) -> None:
        return self._db_command(dict(kind="rollback"))

    def _db_command(self, input: Dict[str, Any]) -> Any:
        try:
            return from_json_bytes(self._backend.db_command(to_json_bytes(input)))
        except Exception as e:
            err_bytes = bytes(e.args[0])
        err = pb.BackendError()
        err.ParseFromString(err_bytes)
        raise backend_exception_to_pylib(err)

    def translate(
        self, key: Union[LegacyTranslationEnum, int], **kwargs: Union[str, int, float]
    ) -> str:
        int_key = key if isinstance(key, int) else key.value
        return self.translate_string(translate_string_in(key=int_key, **kwargs))

    def format_time_span(
        self,
        seconds: Any,
        context: Any = 2,
    ) -> str:
        print(
            "please use col.format_timespan() instead of col.backend.format_time_span()"
        )
        return self.format_timespan(seconds=seconds, context=context)

    def _run_command(self, service: int, method: int, input: Any) -> bytes:
        input_bytes = input.SerializeToString()
        try:
            return self._backend.command(service, method, input_bytes)
        except Exception as e:
            err_bytes = bytes(e.args[0])
        err = pb.BackendError()
        err.ParseFromString(err_bytes)
        raise backend_exception_to_pylib(err)


def translate_string_in(
    key: int, **kwargs: Union[str, int, float]
) -> pb.TranslateStringIn:
    args = {}
    for (k, v) in kwargs.items():
        if isinstance(v, str):
            args[k] = pb.TranslateArgValue(str=v)
        else:
            args[k] = pb.TranslateArgValue(number=v)
    return pb.TranslateStringIn(key=key, args=args)


class Translations(GeneratedTranslations):
    def __init__(self, backend: ref[RustBackend]):
        self.backend = backend

    def __call__(self, *args: Any, **kwargs: Any) -> str:
        "Mimic the old col.tr / TR interface"
        return self.backend().translate(*args, **kwargs)

    def _translate(
        self, module: int, translation: int, args: Dict[str, Union[str, int, float]]
    ) -> str:
        return self.backend().translate(module * 1000 + translation, **args)
