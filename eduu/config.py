import os.path

from typing import List, Optional


API_ID: int = 3487995
API_HASH: str = "7b9f1868c1e90b7408d48445f1e89603"
TOKEN: str = "1793418448:AAG_85y0JOrfyuXOCs-dkmufe_FEZiATaBA"

log_chat: int = -803830916
sudoers: List[int] = [983756079]
super_sudoers: List[int] = [983756079]

prefix: List[str] = ["/", "!", ".", "$", "-"]

disabled_plugins: List[str] = []

WORKERS = 24

DATABASE_PATH = os.path.join("eduu", "database", "eduu.db")

TENOR_API_KEY: Optional[str] = "X9HD35B7ZGP6"

sudoers.extend(super_sudoers)
