from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.meko import BUILD_DATAPACK_ID, DEFAULT_DATAPACK_ID, MekoError, decode_result, product_pack


def test_mcp_result_errors_are_not_empty_context():
    wrapped = lambda payload: SimpleNamespace(isError=False, structuredContent={"result": payload})
    assert decode_result(wrapped('{"results": []}')) == {"results": []}
    for payload in ['{"error": "quota exceeded"}', '{"detail": "permission denied"}', "not json"]:
        with pytest.raises(MekoError):
            decode_result(wrapped(payload))
    with pytest.raises(MekoError):
        product_pack(BUILD_DATAPACK_ID)
    with pytest.raises(MekoError):
        product_pack(DEFAULT_DATAPACK_ID)
    assert product_pack(str(uuid4()))
