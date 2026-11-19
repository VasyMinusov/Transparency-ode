"""LSB-стеганография для PNG-иконки приложения.

Встраивание: python stego_lsb.py embed icon.png "фраза"
Извлечение:  python stego_lsb.py extract icon.png

Детерминировано: одинаковая иконка и фраза -> одинаковый файл.
PNG без потерь: сообщение не разрушается при копировании.
"""
import sys
import numpy as np
from PIL import Image


def embed(path: str, phrase: str) -> None:
    payload = len(phrase.encode("utf-8")).to_bytes(4, "big") + phrase.encode("utf-8")
    bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))
    img = Image.open(path).convert("RGB")
    arr = np.array(img)
    flat = arr.reshape(-1)
    if len(bits) > flat.size:
        raise SystemExit("сообщение не помещается в иконку")
    flat[: len(bits)] = (flat[: len(bits)] & 0xFE) | bits
    Image.fromarray(arr.reshape(img.height, img.width, 3), "RGB").save(path)
    print(f"Встроено {len(bits)} бит в {path}")


def extract(path: str) -> None:
    flat = np.array(Image.open(path).convert("RGB")).reshape(-1)
    length = int.from_bytes(np.packbits(flat[:32] & 1).tobytes(), "big")
    need = (4 + length) * 8
    raw = np.packbits(flat[:need] & 1).tobytes()
    print(f"Извлечено: «{raw[4:4 + length].decode('utf-8')}»")


if __name__ == "__main__":
    if sys.argv[1] == "embed":
        embed(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "extract":
        extract(sys.argv[2])
    else:
        raise SystemExit("usage: stego_lsb.py embed|extract icon.png [phrase]")
