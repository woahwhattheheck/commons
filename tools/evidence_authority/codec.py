"""Strict bounded canonical JSON primitives for retained authority evidence."""
from __future__ import annotations
import hashlib, json, re
from typing import Any

MAX_DOCUMENT_BYTES=262_144
MAX_TOTAL_SOURCE_BYTES=2_097_152
MAX_NODES=10_000
MAX_DEPTH=20
MAX_CONTAINER_ITEMS=1_000
MAX_STRING_UTF8_BYTES=65_536
MAX_INTEGER_ABS=9_223_372_036_854_775_807
SHA256_RE=re.compile(r"^[0-9a-f]{64}$")

class AuthorityError(ValueError):
    pass

def strict_text(value:Any,label:str)->str:
    if not isinstance(value,str) or not value: raise AuthorityError(f"{label} must be a non-empty string")
    try: raw=value.encode("utf-8","strict")
    except UnicodeEncodeError as exc: raise AuthorityError(f"{label} must be Unicode scalar text") from exc
    if len(raw)>MAX_STRING_UTF8_BYTES: raise AuthorityError(f"{label} exceeds UTF-8 byte bound")
    return value

def strict_int(value:Any,label:str,*,minimum:int|None=None,maximum:int|None=None)->int:
    if isinstance(value,bool) or not isinstance(value,int): raise AuthorityError(f"{label} must be an integer")
    if abs(value)>MAX_INTEGER_ABS: raise AuthorityError(f"{label} exceeds integer bound")
    if minimum is not None and value<minimum: raise AuthorityError(f"{label} is below minimum")
    if maximum is not None and value>maximum: raise AuthorityError(f"{label} exceeds maximum")
    return value

def _walk(value:Any,*,depth:int=0,budget:list[int]|None=None,label:str="value")->None:
    if budget is None: budget=[0]
    budget[0]+=1
    if budget[0]>MAX_NODES: raise AuthorityError("JSON node bound exceeded")
    if depth>MAX_DEPTH: raise AuthorityError("JSON depth bound exceeded")
    if value is None or isinstance(value,bool): return
    if isinstance(value,int): strict_int(value,label); return
    if isinstance(value,float): raise AuthorityError(f"{label} floats are not admitted")
    if isinstance(value,str): strict_text(value,label); return
    if isinstance(value,list):
        if len(value)>MAX_CONTAINER_ITEMS: raise AuthorityError(f"{label} array item bound exceeded")
        for i,item in enumerate(value): _walk(item,depth=depth+1,budget=budget,label=f"{label}[{i}]")
        return
    if isinstance(value,dict):
        if len(value)>MAX_CONTAINER_ITEMS: raise AuthorityError(f"{label} object item bound exceeded")
        for key,item in value.items():
            strict_text(key,f"{label} key")
            _walk(item,depth=depth+1,budget=budget,label=f"{label}.{key}")
        return
    raise AuthorityError(f"{label} contains unsupported JSON type")

def canonical_bytes(value:Any)->bytes:
    _walk(value)
    try: raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8","strict")
    except (TypeError,ValueError,UnicodeEncodeError) as exc: raise AuthorityError(f"value is not canonical JSON") from exc
    if len(raw)>MAX_DOCUMENT_BYTES: raise AuthorityError("canonical JSON exceeds document byte bound")
    return raw

def sha256_value(value:Any)->str: return hashlib.sha256(canonical_bytes(value)).hexdigest()
def sha256_bytes(raw:bytes)->str:
    if not isinstance(raw,bytes): raise AuthorityError("source material must be bytes")
    return hashlib.sha256(raw).hexdigest()

def _parse_int(token:str)->int:
    digits=token[1:] if token.startswith("-") else token
    if len(digits)>19: raise AuthorityError("integer token exceeds digit bound")
    try: value=int(token)
    except ValueError as exc: raise AuthorityError("invalid integer token") from exc
    return strict_int(value,"integer token")
def _reject_float(token:str): raise AuthorityError,"floating-point JSON numbers are not admitted")