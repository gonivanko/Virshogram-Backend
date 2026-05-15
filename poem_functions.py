import re
import random
from typing import List, Dict, Any, Optional

def get_poem_parts(text: str, current_level: int = 0, min_lines: int = 3, max_lines: int = 6) -> list[str]:
    dividers: list[str] = ["\n\n", ".\n", "…\n", "!\n", "?\n", ",\n", "\n"]

    if current_level >= len(dividers):
        return [text.strip()] if text.strip() else []

    divider = dividers[current_level]
    parts = []
    buffer = ""
    raw_parts = text.split(divider)
    for i, part in enumerate(raw_parts):
        current_part = buffer + part
        lines_number = len(current_part.split('\n'))
        # print(repr(f"Processing part with {lines_number} lines, buffer: {buffer}"))
        if (lines_number <= max_lines) and (lines_number >= min_lines):
            parts.append(current_part)
            buffer = ""
        elif lines_number < min_lines:
            buffer = current_part + divider
        else:
            parts.extend(get_poem_parts(current_part, current_level + 1, min_lines, max_lines))


    buffer = buffer.split(divider)[0]

    if buffer.strip():
        if parts:
            parts[-1] += buffer  # Доклеюємо до останнього валідного шматка
        else:
            parts.append(buffer)

    return parts

def parse_poem_text(poem_text: str) -> List[Dict[str, Any]]:
    """
    Розбиває текст вірша на рядки та токени, зберігаючи пробіли та розділові знаки.
    """
    lines = poem_text.splitlines()
    parsed_lines = []

    for line in lines:
        trimmed_line = line.strip()
        if not trimmed_line:
            parsed_lines.append({
                "originalLine": line,
                "tokens": [],
                "isEmpty": True
            })
            continue

        # Регулярний вираз:
        # 1. Слова (літери, цифри, апострофи, дефіси)
        # 2. АБО все інше (пробіли, розділові знаки) як окремі токени
        pattern = r"[\w'’`-]+|[^\w'’`]+"
        raw_tokens = re.findall(pattern, trimmed_line)

        tokens = []
        for text in raw_tokens:
            # isWord: True, якщо в токені є хоча б одна літера або цифра
            is_word = any(char.isalnum() for char in text)
            tokens.append({
                "text": text,
                "isWord": is_word
            })

        parsed_lines.append({
            "originalLine": trimmed_line,
            "tokens": tokens,
            "isEmpty": False
        })

    return parsed_lines

def prepare_poem_lines(content: str) -> List[Dict[str, Any]]:
    """
    Готує рядки вірша, обираючи в кожному одне випадкове слово для приховування.
    """
    if not content:
        return []

    lines = parse_poem_text(content)

    for line in lines:
        if line["isEmpty"]:
            continue

        # Знаходимо індекси всіх токенів, які є словами
        word_indexes = [
            idx for idx, token in enumerate(line["tokens"])
            if token["isWord"]
        ]

        if word_indexes:
            random_index = random.choice(word_indexes)
            line["hiddenTokenIndex"] = random_index
            line["correctWord"] = line["tokens"][random_index]["text"]

    return lines

def extract_hidden_words(lines: List[Dict[str, Any]]) -> List[str]:
    """
    Створює масив прихованих слів (банк слів).
    """
    return [
        line["correctWord"]
        for line in lines
        if "hiddenTokenIndex" in line and "correctWord" in line
    ]