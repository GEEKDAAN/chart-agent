from app.agents.chart_agent_state import ChartAgentState
from app.domain.colors import COLOR_HEX_TO_LABEL, COLOR_NAME_TO_HEX
from app.schemas.chart import ChartSpec


def resolve_style_updates(state: ChartAgentState, chart: ChartSpec) -> dict[str, str]:
    message = state["user_message"]
    exclusion_updates = _style_updates_from_exclusion_message(message, chart)
    if exclusion_updates:
        return exclusion_updates

    all_target_updates = _style_updates_from_all_targets_message(message, chart)
    if all_target_updates:
        return all_target_updates

    argument_updates = _style_updates_from_decision_arguments(state, chart)
    if argument_updates:
        return argument_updates

    message_updates = _style_updates_from_message(message, chart)
    if message_updates:
        return message_updates

    target = _resolve_style_target(message, chart)
    color = _first_color_in_text(message)
    if color:
        return {target: color}

    raise ValueError("未识别到要修改的颜色。")


def color_label(color: str) -> str:
    return COLOR_HEX_TO_LABEL.get(color, color)


def _style_updates_from_decision_arguments(state: ChartAgentState, chart: ChartSpec) -> dict[str, str]:
    decision = state.get("decision")
    if not decision:
        return {}
    arguments = decision.arguments or {}
    updates: dict[str, str] = {}

    raw_updates = arguments.get("updates")
    if isinstance(raw_updates, list):
        for raw_update in raw_updates:
            if not isinstance(raw_update, dict):
                continue
            target = _normalize_style_target(raw_update.get("target"), chart)
            color = _normalize_color(raw_update.get("color"))
            if target and color:
                updates[target] = color

    raw_colors = arguments.get("colors")
    if isinstance(raw_colors, dict):
        for raw_target, raw_color in raw_colors.items():
            target = _normalize_style_target(raw_target, chart)
            color = _normalize_color(raw_color)
            if target and color:
                updates[target] = color

    target = _normalize_style_target(arguments.get("target"), chart)
    color = _normalize_color(arguments.get("color"))
    if target and color:
        updates[target] = color

    return updates


def _style_updates_from_exclusion_message(message: str, chart: ChartSpec) -> dict[str, str]:
    color = _first_color_in_text(message)
    if not color or not _mentions_remaining_targets(message):
        return {}

    targets = _style_target_values(chart)
    excluded = [target for target in targets if _is_excluded_target(message, target)]
    if not excluded:
        return {}

    return {target: color for target in targets if target not in excluded}


def _style_updates_from_all_targets_message(message: str, chart: ChartSpec) -> dict[str, str]:
    color = _first_color_in_text(message)
    if not color or not _mentions_all_targets(message):
        return {}

    targets = _style_target_values(chart)
    return {target: color for target in targets}


def _style_updates_from_message(message: str, chart: ChartSpec) -> dict[str, str]:
    targets = _style_targets_in_message(message, chart)
    if not targets:
        return {}

    colors_in_message = _colors_in_text(message)
    updates: dict[str, str] = {}
    for index, target in enumerate(targets):
        target_position = message.find(target)
        next_positions = [
            message.find(next_target)
            for next_target in targets[index + 1 :]
            if message.find(next_target) > target_position
        ]
        segment_end = min(next_positions) if next_positions else len(message)
        segment = message[target_position:segment_end]
        color = _first_color_in_text(segment)
        if not color and len(colors_in_message) == 1:
            color = colors_in_message[0]
        if color:
            updates[target] = color
    return updates


def _style_targets_in_message(message: str, chart: ChartSpec) -> list[str]:
    matches: list[tuple[int, str]] = []
    for value in _style_target_values(chart):
        position = message.find(value)
        if position >= 0 and value not in [target for _, target in matches]:
            matches.append((position, value))
    return [target for _, target in sorted(matches, key=lambda item: item[0])]


def _normalize_style_target(value: object, chart: ChartSpec) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    for target in _style_target_values(chart):
        if target == text:
            return target
    return None


def _resolve_style_target(message: str, chart: ChartSpec) -> str:
    for target in _style_target_values(chart):
        if target in message:
            return target
    targets = _style_target_values(chart)
    return targets[0] if targets else "default"


def _style_target_values(chart: ChartSpec) -> list[str]:
    target_key = chart.encoding.x or chart.encoding.category
    values: list[str] = []
    if target_key:
        for row in chart.data.rows:
            value = row.get(target_key)
            if isinstance(value, str) and value not in values:
                values.append(value)
    if values:
        return values

    for row in chart.data.rows:
        for value in row.values():
            if isinstance(value, str) and value not in values:
                values.append(value)
    return values


def _mentions_remaining_targets(message: str) -> bool:
    return any(keyword in message for keyword in ["其他", "其余", "剩下", "剩余", "以外", "之外", "都", "全部", "所有"])


def _mentions_all_targets(message: str) -> bool:
    return any(keyword in message for keyword in ["全部", "所有", "全都", "都"])


def _is_excluded_target(message: str, target: str) -> bool:
    patterns = [
        f"除{target}",
        f"除了{target}",
        f"{target}外",
        f"{target}以外",
        f"{target}之外",
        f"不包括{target}",
        f"排除{target}",
    ]
    return any(pattern in message for pattern in patterns)


def _colors_in_text(text: str) -> list[str]:
    colors: list[tuple[int, str]] = []
    lowered = text.lower()
    for name, color in COLOR_NAME_TO_HEX.items():
        position = lowered.find(name.lower())
        if position >= 0:
            colors.append((position, color))
    deduped: list[str] = []
    for _, color in sorted(colors, key=lambda item: item[0]):
        if color not in deduped:
            deduped.append(color)
    return deduped


def _first_color_in_text(text: str) -> str | None:
    colors = _colors_in_text(text)
    return colors[0] if colors else None


def _normalize_color(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.startswith("#"):
        return text
    return COLOR_NAME_TO_HEX.get(text.lower()) or COLOR_NAME_TO_HEX.get(text)
