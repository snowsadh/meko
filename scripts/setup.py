"""Create local settings without overwriting keys the user already supplied."""

from pathlib import Path
import os
import secrets

root = Path(__file__).resolve().parent.parent
path = root / ".env"
existing = path.read_text() if path.exists() else ""
keys = {
    line.split("=", 1)[0].strip()
    for line in existing.splitlines()
    if "=" in line and not line.lstrip().startswith("#")
}
lines = existing.rstrip().splitlines() if existing.strip() else []
for index, line in enumerate(lines):
    key, separator, value = line.partition("=")
    if (
        separator
        and key.strip() in {"JWT_SECRET_KEY", "ENCRYPTION_KEY"}
        and value.strip() in {"", '""', "''"}
    ):
        lines[index] = f"{key.strip()}={secrets.token_hex(32)}"
for line in (root / ".env.example").read_text().splitlines():
    if not line or line.startswith("#"):
        continue
    key, value = line.split("=", 1)
    if key in keys:
        continue
    if key in {"JWT_SECRET_KEY", "ENCRYPTION_KEY"}:
        value = secrets.token_hex(32)
    lines.append(f"{key}={value}")
path.write_text("\n".join(lines) + "\n")
os.chmod(path, 0o600)
print("Local settings prepared. Add the Meko product and OpenAI keys to .env.")
