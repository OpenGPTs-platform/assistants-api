from typing import List, Any


def context_trimmer(
    item_list: List[Any], max_length: int, trim_start: bool
) -> List[Any]:
    def calculate_length(items: List[Any]) -> int:
        return len(str(items))

    trimmed_list = item_list[:]

    while calculate_length(trimmed_list) > max_length:
        if trim_start:
            trimmed_list.pop(0)
        else:
            trimmed_list.pop()

    return trimmed_list
