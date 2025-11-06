import os

def extract_appended_data(filepath: str, output_dir: str) -> str | None:
    with open(filepath, "rb") as f:
        data = f.read()

    ext = os.path.splitext(filepath)[1].lower()
    eof_signature = None

    if ext == ".png":
        eof_signature = b"\x00\x00\x00\x00IEND\xaeB`\x82"
    elif ext in [".jpg", ".jpeg"]:
        eof_signature = b"\xff\xd9"
    else:
        return None  # Only PNG/JPG supported for now

    eof_index = data.find(eof_signature)
    if eof_index == -1:
        return None

    append_start = eof_index + len(eof_signature)
    if append_start >= len(data):
        return None  # No appended data

    appended_data = data[append_start:]
    output_path = os.path.join(output_dir, "appended.bin")
    with open(output_path, "wb") as out:
        out.write(appended_data)

    return "appended.bin"
