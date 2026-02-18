from __future__ import annotations

"""내부 통신용 시크릿 검증"""

import os

from fastapi import Header, HTTPException


def verify_secret(x_internal_secret: str = Header(default="")) -> None:
    """Next.js → Python 내부 통신용 시크릿 검증"""
    expected = os.getenv("PYTHON_API_SECRET", "")
    if not expected:
        # 시크릿 미설정 시 개발 모드로 간주하여 통과
        return
    if x_internal_secret != expected:
        raise HTTPException(status_code=403, detail="Invalid internal secret")
