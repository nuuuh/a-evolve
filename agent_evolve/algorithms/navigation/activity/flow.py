"""Runtime-level ObjectFlow / ControlFlow dataclasses.

These mirror ``FlowSpec`` but carry parsed source/target endpoints for
convenience.  Constructed during validation; used by the runtime for
wire lookup.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Endpoint:
    """A parsed ``node_id.pin`` or bare ``parameter_id``."""

    node: str          # node id OR parameter id
    pin: str | None    # pin name, or None if the endpoint is a parameter

    @classmethod
    def parse(cls, raw: str) -> Endpoint:
        if "." in raw:
            node, pin = raw.split(".", 1)
            return cls(node=node, pin=pin)
        return cls(node=raw, pin=None)

    def __str__(self) -> str:
        return f"{self.node}.{self.pin}" if self.pin else self.node


@dataclass(frozen=True)
class ObjectFlow:
    source: Endpoint
    target: Endpoint


@dataclass(frozen=True)
class ControlFlow:
    source: Endpoint
    target: Endpoint
