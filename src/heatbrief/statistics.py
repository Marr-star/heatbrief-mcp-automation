"""Both extrema, with compatibility for saved comparisons from earlier versions."""

import re


def question_focus(question):
    high = bool(re.search(r"\b(highest|hottest|warmest|maximum|max)\b", question, re.I))
    low = bool(re.search(r"\b(lowest|coldest|coolest|minimum|min)\b", question, re.I))
    return "highest" if high and not low else "lowest" if low and not high else "both"


def highest(comparison):
    ranking = comparison["ranking"]
    value = comparison.get("highest_c", max(row["temperature_c"] for row in ranking))
    names = comparison.get(
        "highest_locations", [row["name"] for row in ranking if row["temperature_c"] == value]
    )
    return value, names


def extrema_narrative(comparison, focus="both"):
    prefix = "Among available readings, " if comparison["incomplete"] else "Among these locations, "
    high_value, high_names = highest(comparison)
    extremes = {
        "lowest": (comparison["lowest_c"], comparison["lowest_locations"]),
        "highest": (high_value, high_names),
    }
    keys = [focus] if focus != "both" else ["lowest", "highest"]
    messages = []
    for key in keys:
        value, names = extremes[key]
        verb = "has" if len(names) == 1 else "tie for"
        messages.append(f"{', '.join(names)} {verb} the {key} temperature at {value:.1f} °C.")
    return prefix + " ".join(messages)
