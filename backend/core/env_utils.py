import os

def update_env_file(key: str, value: str, env_path: str | None = None) -> bool:
    """
    Safely update or add an environment variable key-value pair in a .env file.
    Updates os.environ[key] as well.
    """
    os.environ[key] = value

    if env_path is None:
        # Search common locations
        candidates = ["backend/.env", ".env"]
        for cand in candidates:
            if os.path.exists(cand):
                env_path = cand
                break
        if not env_path:
            env_path = "backend/.env" if os.path.exists("backend") else ".env"

    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    # Form formatted value string
    # Wrap in single quotes if value contains spaces or quotes (e.g., JSON string)
    if "\n" in value:
        formatted_val = value.replace("\n", "")
    else:
        formatted_val = value

    if "'" not in formatted_val:
        entry_str = f"{key}='{formatted_val}'\n"
    elif '"' not in formatted_val:
        entry_str = f'{key}="{formatted_val}"\n'
    else:
        # Escape double quotes
        escaped = formatted_val.replace('"', '\\"')
        entry_str = f'{key}="{escaped}"\n'

    key_found = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"# {key}="):
            new_lines.append(entry_str)
            key_found = True
        else:
            new_lines.append(line)

    if not key_found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append(entry_str)

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        return True
    except Exception as e:
        print(f"Warning: Failed to write to {env_path}: {e}")
        return False
