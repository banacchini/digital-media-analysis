"""Exploratory Data Analysis (EDA) on RentFriends database structure and schema metadata.

This module inspects and visualizes the database structure documented in
`data/processed/metadata.txt` to evaluate the feasibility of investigating hypotheses
H1 through H5 from `docs/rentfriends_hipotezy_karta_eksploracji.md`.

Note:
- Does NOT read parquet files directly. All structural information is parsed from metadata.txt.
- Provides only visualizations and schema join models; substantive analytical interpretation
  is left to the researcher.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt

# Brand colour palette from STYLEGUIDE.md
COLOR_BG = "#F4F2EE"
COLOR_CARD_BG = "#FFFFFF"
COLOR_TEXT_BLACK = "#0F0F0F"
COLOR_TEXT_GRAY = "#595959"
COLOR_PURPLE = "#A247E3"
COLOR_PURPLE_INK = "#8B34C4"
COLOR_BLUE = "#234CE0"
COLOR_PINK = "#E95BD2"
COLOR_HAIRLINE = "#D5D2CB"


@dataclass
class TableMetadata:
    """Represents schema metadata for a database table."""

    name: str
    file_name: str
    column_count: int
    columns: list[str]
    column_types: dict[str, str]

    def get_column_category(self, col: str) -> str:
        """Classify a column into its analytical category."""
        if col.endswith("_key") or col in ("user_key", "listing_key", "chat_key"):
            return "Key / ID"
        if col in (
            "day",
            "created_day",
            "chat_created_day",
            "first_message_day",
            "hours_to_first_message",
        ):
            return "Temporal"
        if col in (
            "direction",
            "from_match",
            "is_active",
            "target_type",
            "version",
            "change_type",
        ):
            return "Interaction / Status"
        if col in ("bio", "bio_length", "changed_fields"):
            return "Bio / Content"
        if col in (
            "sex",
            "age_band",
            "city",
            "district",
            "budget",
            "room_type",
            "search_goal",
            "move_in_month_offset",
        ):
            return "Demographics / Goals"
        if col in (
            "cleanliness",
            "smoking",
            "alcohol",
            "lifestyle",
            "daily_routine",
            "noise_level",
            "work_from_home",
            "interests",
        ):
            return "Lifestyle / Interests"
        return "Listing Attributes"


@dataclass
class Relationship:
    """Represents a foreign-key or logical join relationship between two tables."""

    source_table: str
    source_column: str
    target_table: str
    target_column: str
    cardinality: str
    label: str


@dataclass
class HypothesisMapping:
    """Maps a research hypothesis to relevant database constructs, joins, and columns."""

    hypothesis_id: str
    short_title: str
    one_liner: str
    target_construct: str
    required_tables: list[str]
    required_joins: list[str]
    mapped_columns: dict[str, list[str]]
    temporal_granularity: str
    structural_availability: str


def parse_metadata_file(filepath: Path | str) -> dict[str, TableMetadata]:
    """Parse table schemas and column types from data/processed/metadata.txt.

    Args:
        filepath: Path to metadata.txt.

    Returns:
        Dictionary mapping table name (e.g. 'users') to TableMetadata.
    """
    path = Path(filepath)
    if not path.exists():
        msg = f"Metadata file not found at: {path}"
        raise FileNotFoundError(msg)

    content = path.read_text(encoding="utf-8")
    table_blocks = content.split("============================================================")

    tables: dict[str, TableMetadata] = {}

    for block in table_blocks:
        block = block.strip()
        if not block:
            continue

        file_match = re.search(r"File:\s*([a-zA-Z0-9_\-]+\.parquet)", block)
        if not file_match:
            continue
        file_name = file_match.group(1)
        table_name = file_name.replace(".parquet", "")

        cols_match = re.search(r"Columns\s*\((\d+)\):\s*(\[.*?\])", block)
        if not cols_match:
            continue
        col_count = int(cols_match.group(1))
        columns_raw = cols_match.group(2)
        columns = [c.strip().strip("'\"") for c in columns_raw.strip("[]").split(",") if c.strip()]

        col_types: dict[str, str] = {}
        for line in block.splitlines():
            line_str = line.strip()
            if (
                not line_str
                or line_str.startswith("File:")
                or line_str.startswith("---")
                or line_str.startswith("Columns")
                or line_str.startswith("dtype:")
            ):
                continue
            parts = line_str.split()
            if len(parts) >= 2 and parts[0] in columns:
                col_types[parts[0]] = parts[1]

        tables[table_name] = TableMetadata(
            name=table_name,
            file_name=file_name,
            column_count=col_count,
            columns=columns,
            column_types=col_types,
        )

    return tables


def get_schema_relationships() -> list[Relationship]:
    """Return all defined relational joins between tables based on key columns."""
    return [
        Relationship("swipes", "user_key", "users", "user_key", "N:1", "Swiper user"),
        Relationship("swipes", "target_user_key", "users", "user_key", "N:1", "Target user"),
        Relationship(
            "swipes", "target_listing_key", "listings", "listing_key", "N:1", "Target listing"
        ),
        Relationship("matches", "user_a_key", "users", "user_key", "N:1", "Matched User A"),
        Relationship("matches", "user_b_key", "users", "user_key", "N:1", "Matched User B"),
        Relationship("chats", "user_a_key", "users", "user_key", "N:1", "Chat Participant A"),
        Relationship("chats", "user_b_key", "users", "user_key", "N:1", "Chat Participant B"),
        Relationship("chats", "first_sender_key", "users", "user_key", "N:1", "First sender"),
        Relationship(
            "chats", "source_listing_key", "listings", "listing_key", "N:1", "Listing context"
        ),
        Relationship(
            "profile_history", "user_key", "users", "user_key", "N:1", "Profile history owner"
        ),
        Relationship("listings", "owner_key", "users", "user_key", "N:1", "Listing owner"),
    ]


def join_table_schemas(
    left: TableMetadata,
    right: TableMetadata,
    left_on: str,
    right_on: str,
    joined_name: str,
    suffixes: tuple[str, str] = ("_left", "_right"),
) -> TableMetadata:
    """Simulate joining two table schemas to demonstrate the resulting feature space.

    Args:
        left: Left TableMetadata.
        right: Right TableMetadata.
        left_on: Column in left table.
        right_on: Column in right table.
        joined_name: Identifier for the resulting joined schema.
        suffixes: Suffixes for overlapping column names.

    Returns:
        TableMetadata representing the schema of the joined table.
    """
    if left_on not in left.columns:
        msg = f"Join key '{left_on}' missing in left table '{left.name}'"
        raise KeyError(msg)
    if right_on not in right.columns:
        msg = f"Join key '{right_on}' missing in right table '{right.name}'"
        raise KeyError(msg)

    new_columns: list[str] = []
    new_types: dict[str, str] = {}

    for c in left.columns:
        c_name = f"{c}{suffixes[0]}" if c in right.columns and c != left_on else c
        new_columns.append(c_name)
        new_types[c_name] = left.column_types.get(c, "unknown")

    for c in right.columns:
        if c == right_on and left_on == right_on:
            continue
        c_name = f"{c}{suffixes[1]}" if c in left.columns else c
        new_columns.append(c_name)
        new_types[c_name] = right.column_types.get(c, "unknown")

    return TableMetadata(
        name=joined_name,
        file_name=f"{joined_name}.virtual",
        column_count=len(new_columns),
        columns=new_columns,
        column_types=new_types,
    )


def get_hypothesis_mappings() -> list[HypothesisMapping]:
    """Define structural mapping for hypotheses H1 through H5 against the database schema."""
    return [
        HypothesisMapping(
            hypothesis_id="H1",
            short_title="Lifestyle vs Age/Interests",
            one_liner="Lifestyle compatibility predicts match stronger than age & interests.",
            target_construct="y_match (matches) / y_right (swipes.direction)",
            required_tables=["users", "swipes", "matches"],
            required_joins=[
                "matches JOIN users (as User A)",
                "matches JOIN users (as User B)",
                "swipes JOIN users (as Sender) JOIN users (as Target)",
            ],
            mapped_columns={
                "Lifestyle": [
                    "cleanliness",
                    "smoking",
                    "alcohol",
                    "lifestyle",
                    "daily_routine",
                    "noise_level",
                    "work_from_home",
                ],
                "Demographics": ["sex", "age_band"],
                "Interests": ["interests"],
                "Outcome": ["matches.day", "swipes.direction"],
            },
            temporal_granularity="Static profiles paired with event day in matches/swipes",
            structural_availability="Directly joinable via user keys (users JOIN swipes / matches)",
        ),
        HypothesisMapping(
            hypothesis_id="H2",
            short_title="Demographics as Gatekeeper",
            one_liner="Demographic match (gender, age) is an entry gate, not a preference.",
            target_construct="y_right (swipes.direction) conditioned on gender/age pairs",
            required_tables=["users", "swipes", "matches"],
            required_joins=[
                "swipes JOIN users (Sender: user_key) JOIN users (Receiver: target_user_key)",
            ],
            mapped_columns={
                "Demographics A": ["users.sex (sender)", "users.age_band (sender)"],
                "Demographics B": ["users.sex (target)", "users.age_band (target)"],
                "Outcome": ["swipes.direction", "matches.day"],
                "Controls": ["cleanliness", "smoking", "alcohol", "interests"],
            },
            temporal_granularity="Pair-level directional swipes with day resolution",
            structural_availability="Directly joinable via swipes user keys",
        ),
        HypothesisMapping(
            hypothesis_id="H3",
            short_title="Two-Sided vs One-Sided Fit",
            one_liner="Match is determined by bilateral compatibility (minimum fit).",
            target_construct="P(match) explained by min(fit_A->B, fit_B->A) vs fit_A, fit_B",
            required_tables=["swipes", "users", "matches"],
            required_joins=[
                "swipes (A→B, day) JOIN swipes (B→A, day) [reciprocal pair join]",
                "swipes JOIN historical swipes prior to day",
            ],
            mapped_columns={
                "Pair Actions": ["swipes.direction (A->B)", "swipes.direction (B->A)"],
                "Time / Sequence": ["swipes.day", "matches.day"],
                "Profile Basis": ["users.* (profile traits)"],
            },
            temporal_granularity="Integer day only (no sub-day timestamps in swipes/matches)",
            structural_availability="Daily granularity; sub-day ordering cannot be resolved",
        ),
        HypothesisMapping(
            hypothesis_id="H4",
            short_title="Selectivity Reciprocity",
            one_liner="User selectivity concordance predicts reciprocity beyond traits.",
            target_construct="P(B right | A right) modeled by selectivity difference |s_A - s_B|",
            required_tables=["swipes", "matches", "users"],
            required_joins=[
                "swipes aggregated by user_key & day -> user_selectivity table",
                "pair_swipes JOIN user_selectivity (A) JOIN user_selectivity (B)",
            ],
            mapped_columns={
                "Behavioral Aggregates": ["swipes.user_key", "swipes.direction", "swipes.day"],
                "Outcome": ["swipes.direction (mutual)", "matches.day"],
                "Baseline Controls": ["users.sex", "users.age_band", "users.lifestyle"],
            },
            temporal_granularity="Integer day (permits rolling daily selectivity metrics)",
            structural_availability="Aggregated user selectivity joined to pair records",
        ),
        HypothesisMapping(
            hypothesis_id="H5",
            short_title="Bio Content & Effort",
            one_liner="Bio text content and elaboration provide signal beyond structured fields.",
            target_construct="y_right / y_match explained by bio effort and semantic similarity",
            required_tables=["users", "profile_history", "swipes", "matches"],
            required_joins=[
                "users (as A) JOIN users (as B) JOIN matches",
                "swipes JOIN profile_history (user_key, version/day) [for history snapshot]",
            ],
            mapped_columns={
                "Bio Features": ["users.bio", "users.bio_length"],
                "History / Version": [
                    "profile_history.version",
                    "profile_history.day",
                    "profile_history.changed_fields",
                    "profile_history.bio",
                ],
                "Structured Controls": ["users.interests", "users.lifestyle", "users.cleanliness"],
                "Outcome": ["swipes.direction", "matches.day"],
            },
            temporal_granularity="Snapshot in users; versioned history with day in profile_history",
            structural_availability="bio & bio_length present in users and profile_history",
        ),
    ]


def plot_relational_schema_erd(
    tables: dict[str, TableMetadata],
    relationships: list[Relationship],
    output_path: Path | None = None,
) -> plt.Figure:
    """Create an Entity-Relationship Diagram (ERD) of database tables and join paths."""
    fig, ax = plt.subplots(figsize=(16, 11), facecolor=COLOR_BG)
    ax.set_facecolor(COLOR_BG)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 11)
    ax.axis("off")

    positions = {
        "users": (5.5, 6.2, 5.0, 4.2),
        "swipes": (0.5, 6.2, 4.2, 3.8),
        "matches": (5.5, 2.5, 4.0, 2.5),
        "chats": (11.0, 6.2, 4.5, 4.2),
        "profile_history": (0.5, 0.8, 4.5, 4.5),
        "listings": (11.0, 1.2, 4.5, 4.2),
    }

    colors = {
        "users": COLOR_PURPLE,
        "swipes": COLOR_BLUE,
        "matches": COLOR_PURPLE_INK,
        "chats": COLOR_PINK,
        "profile_history": "#5A6268",
        "listings": "#17A2B8",
    }

    ax.text(
        0.5,
        10.6,
        "RentFriends Database Schema & Join Relationships",
        fontsize=18,
        fontweight="bold",
        color=COLOR_TEXT_BLACK,
    )
    ax.text(
        0.5,
        10.25,
        "Parsed from data/processed/metadata.txt | Basis for evaluating hypotheses H1-H5",
        fontsize=11,
        color=COLOR_TEXT_GRAY,
    )

    for tbl_name, (x, y, w, h) in positions.items():
        if tbl_name not in tables:
            continue
        tbl = tables[tbl_name]
        theme_col = colors.get(tbl_name, COLOR_PURPLE)

        # Main table card
        rect = patches.FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.08,rounding_size=0.15",
            facecolor=COLOR_CARD_BG,
            edgecolor=COLOR_HAIRLINE,
            linewidth=1.2,
        )
        ax.add_patch(rect)

        # Header banner
        header_h = 0.55
        header_rect = patches.FancyBboxPatch(
            (x, y + h - header_h),
            w,
            header_h,
            boxstyle="round,pad=0.08,rounding_size=0.12",
            facecolor=theme_col,
            edgecolor=theme_col,
        )
        ax.add_patch(header_rect)

        ax.text(
            x + 0.15,
            y + h - header_h / 2,
            f"{tbl.name}.parquet ({tbl.column_count} cols)",
            color="white",
            fontsize=10.5,
            fontweight="bold",
            va="center",
        )

        # Column list
        max_display_cols = 13
        line_spacing = (h - header_h - 0.25) / min(len(tbl.columns), max_display_cols)
        curr_y = y + h - header_h - 0.22

        for _i, col in enumerate(tbl.columns[:max_display_cols]):
            col_type = tbl.column_types.get(col, "")
            is_key = col.endswith("_key") or col in ("user_key", "listing_key", "chat_key")
            is_day = "day" in col or col == "hours_to_first_message"

            col_color = COLOR_TEXT_BLACK
            tag = ""
            if is_key:
                col_color = COLOR_PURPLE_INK
                tag = " [KEY]"
            elif is_day:
                col_color = COLOR_BLUE
                tag = " [TIME]"

            ax.text(x + 0.18, curr_y, f"{col}{tag}", fontsize=8.2, color=col_color, va="center")
            ax.text(
                x + w - 0.18,
                curr_y,
                col_type,
                fontsize=7.8,
                color=COLOR_TEXT_GRAY,
                ha="right",
                va="center",
            )
            curr_y -= line_spacing

        if len(tbl.columns) > max_display_cols:
            remaining = len(tbl.columns) - max_display_cols
            ax.text(
                x + w / 2,
                y + 0.15,
                f"... + {remaining} more attributes",
                fontsize=7.8,
                color=COLOR_TEXT_GRAY,
                ha="center",
                style="italic",
            )

    # Draw logical join lines/arrows
    join_arrows = [
        ((4.7, 8.2), (5.5, 8.2), "user_key", COLOR_BLUE),
        ((4.7, 7.5), (5.5, 7.5), "target_user_key", COLOR_BLUE),
        ((7.5, 5.0), (7.5, 6.2), "user_a_key, user_b_key", COLOR_PURPLE_INK),
        ((11.0, 8.2), (10.5, 8.2), "user_a_key, user_b_key", COLOR_PINK),
        ((2.7, 5.3), (5.5, 6.5), "user_key", "#5A6268"),
        ((11.0, 3.2), (10.5, 6.5), "owner_key -> user_key", "#17A2B8"),
        ((4.7, 6.5), (11.0, 3.8), "target_listing_key", COLOR_BLUE),
        ((13.2, 6.2), (13.2, 5.4), "source_listing_key", COLOR_PINK),
    ]

    for (x1, y1), (x2, y2), _lbl, arrow_color in join_arrows:
        arrow = patches.FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="->,head_width=3.5,head_length=5",
            connectionstyle="arc3,rad=-0.12",
            color=arrow_color,
            linewidth=1.4,
            alpha=0.85,
        )
        ax.add_patch(arrow)

    # Legend
    leg_x, leg_y = 5.5, 0.4
    leg_box = patches.FancyBboxPatch(
        (leg_x, leg_y),
        4.8,
        0.65,
        boxstyle="round,pad=0.05,rounding_size=0.1",
        facecolor=COLOR_CARD_BG,
        edgecolor=COLOR_HAIRLINE,
    )
    ax.add_patch(leg_box)
    ax.text(
        leg_x + 0.2,
        leg_y + 0.35,
        "Legend:",
        fontsize=8.5,
        fontweight="bold",
        color=COLOR_TEXT_BLACK,
        va="center",
    )
    ax.text(
        leg_x + 1.0,
        leg_y + 0.35,
        "[KEY] Join/Identifier",
        fontsize=8,
        color=COLOR_PURPLE_INK,
        va="center",
    )
    ax.text(
        leg_x + 2.5,
        leg_y + 0.35,
        "[TIME] Temporal Day",
        fontsize=8,
        color=COLOR_BLUE,
        va="center",
    )
    ax.text(
        leg_x + 3.8,
        leg_y + 0.35,
        "Arrow: FK JOIN PK",
        fontsize=8,
        color=COLOR_TEXT_GRAY,
        va="center",
    )

    plt.tight_layout()
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=200, bbox_inches="tight")
    return fig


def plot_hypothesis_schema_matrix(
    mappings: list[HypothesisMapping],
    output_path: Path | None = None,
) -> plt.Figure:
    """Create a structured matrix visualization mapping hypotheses H1-H5 to database features."""
    fig, ax = plt.subplots(figsize=(16, 9), facecolor=COLOR_BG)
    ax.set_facecolor(COLOR_BG)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10)
    ax.axis("off")

    ax.text(
        0.5,
        9.5,
        "Hypothesis-to-Schema Mapping & Feasibility Matrix",
        fontsize=18,
        fontweight="bold",
        color=COLOR_TEXT_BLACK,
    )
    ax.text(
        0.5,
        9.15,
        "Mapping theoretical constructs in docs/rentfriends_hipotezy_karta_eksploracji.md",
        fontsize=11,
        color=COLOR_TEXT_GRAY,
    )

    columns = [
        ("Hypothesis & Focus", 3.2),
        ("Target Variable / Proxy", 2.6),
        ("Required Tables & Joins", 3.6),
        ("Key Schema Columns", 3.8),
        ("Temporal Resolution", 2.2),
    ]

    curr_x = 0.5
    header_y = 8.4
    row_height = 1.35

    for title, width in columns:
        hdr_rect = patches.FancyBboxPatch(
            (curr_x, header_y),
            width - 0.08,
            0.5,
            boxstyle="round,pad=0.04,rounding_size=0.08",
            facecolor=COLOR_PURPLE,
            edgecolor=COLOR_PURPLE,
        )
        ax.add_patch(hdr_rect)
        ax.text(
            curr_x + (width - 0.08) / 2,
            header_y + 0.25,
            title,
            color="white",
            fontsize=9.5,
            fontweight="bold",
            ha="center",
            va="center",
        )
        curr_x += width

    y_pos = header_y - row_height - 0.08
    for m in mappings:
        curr_x = 0.5

        # Col 1: Hypothesis
        w1 = columns[0][1]
        card1 = patches.FancyBboxPatch(
            (curr_x, y_pos),
            w1 - 0.08,
            row_height,
            boxstyle="round,pad=0.04,rounding_size=0.1",
            facecolor=COLOR_CARD_BG,
            edgecolor=COLOR_HAIRLINE,
        )
        ax.add_patch(card1)
        ax.text(
            curr_x + 0.15,
            y_pos + row_height - 0.28,
            f"{m.hypothesis_id}: {m.short_title}",
            fontsize=10.5,
            fontweight="bold",
            color=COLOR_PURPLE_INK,
        )
        ax.text(
            curr_x + 0.15,
            y_pos + 0.2,
            m.one_liner,
            fontsize=7.8,
            color=COLOR_TEXT_GRAY,
            wrap=True,
        )
        curr_x += w1

        # Col 2: Target Variable
        w2 = columns[1][1]
        card2 = patches.FancyBboxPatch(
            (curr_x, y_pos),
            w2 - 0.08,
            row_height,
            boxstyle="round,pad=0.04,rounding_size=0.1",
            facecolor=COLOR_CARD_BG,
            edgecolor=COLOR_HAIRLINE,
        )
        ax.add_patch(card2)
        ax.text(
            curr_x + 0.15,
            y_pos + row_height / 2,
            m.target_construct,
            fontsize=8.5,
            color=COLOR_TEXT_BLACK,
            fontweight="semibold",
            va="center",
        )
        curr_x += w2

        # Col 3: Required Tables & Joins
        w3 = columns[2][1]
        card3 = patches.FancyBboxPatch(
            (curr_x, y_pos),
            w3 - 0.08,
            row_height,
            boxstyle="round,pad=0.04,rounding_size=0.1",
            facecolor=COLOR_CARD_BG,
            edgecolor=COLOR_HAIRLINE,
        )
        ax.add_patch(card3)
        join_text = "\n".join(f"• {j}" for j in m.required_joins)
        ax.text(
            curr_x + 0.15,
            y_pos + row_height / 2,
            join_text,
            fontsize=8.0,
            color=COLOR_TEXT_BLACK,
            va="center",
        )
        curr_x += w3

        # Col 4: Key Schema Columns
        w4 = columns[3][1]
        card4 = patches.FancyBboxPatch(
            (curr_x, y_pos),
            w4 - 0.08,
            row_height,
            boxstyle="round,pad=0.04,rounding_size=0.1",
            facecolor=COLOR_CARD_BG,
            edgecolor=COLOR_HAIRLINE,
        )
        ax.add_patch(card4)
        col_lines = []
        for cat, cols in m.mapped_columns.items():
            col_lines.append(f"{cat}: {', '.join(cols[:4])}")
        ax.text(
            curr_x + 0.15,
            y_pos + row_height / 2,
            "\n".join(col_lines[:3]),
            fontsize=7.8,
            color=COLOR_TEXT_BLACK,
            va="center",
        )
        curr_x += w4

        # Col 5: Temporal Resolution
        w5 = columns[4][1]
        card5 = patches.FancyBboxPatch(
            (curr_x, y_pos),
            w5 - 0.08,
            row_height,
            boxstyle="round,pad=0.04,rounding_size=0.1",
            facecolor=COLOR_CARD_BG,
            edgecolor=COLOR_HAIRLINE,
        )
        ax.add_patch(card5)
        is_daily_only = "Integer day" in m.temporal_granularity
        pill_col = COLOR_PINK if is_daily_only else COLOR_BLUE
        ax.text(
            curr_x + 0.15,
            y_pos + row_height / 2,
            m.temporal_granularity,
            fontsize=7.8,
            color=pill_col,
            fontweight="semibold",
            va="center",
        )

        y_pos -= row_height + 0.08

    plt.tight_layout()
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=200, bbox_inches="tight")
    return fig


def plot_joined_table_pipelines(
    tables: dict[str, TableMetadata],
    output_path: Path | None = None,
) -> plt.Figure:
    """Visualize how tables join into feature spaces for H1/H2, H3/H4, and H5."""
    fig, axes = plt.subplots(3, 1, figsize=(15, 11), facecolor=COLOR_BG)
    fig.suptitle(
        "Relational Table Join Pipelines for Hypothesis Testing",
        fontsize=16,
        fontweight="bold",
        color=COLOR_TEXT_BLACK,
        y=0.98,
    )

    for ax in axes:
        ax.set_facecolor(COLOR_BG)
        ax.axis("off")
        ax.set_xlim(0, 15)
        ax.set_ylim(0, 3)

    # Pipeline 1: H1 & H2
    ax1 = axes[0]
    ax1.text(
        0.2,
        2.7,
        "Pipeline 1 (H1 & H2): Bilateral Profile Feature Construction",
        fontsize=11,
        fontweight="bold",
        color=COLOR_PURPLE,
    )

    p_ua = patches.FancyBboxPatch(
        (0.5, 0.5),
        3.2,
        1.8,
        boxstyle="round,pad=0.08",
        facecolor=COLOR_CARD_BG,
        edgecolor=COLOR_HAIRLINE,
    )
    ax1.add_patch(p_ua)
    ax1.text(0.7, 1.9, "users (User A)", fontweight="bold", color=COLOR_PURPLE_INK, fontsize=9.5)
    ax1.text(
        0.7,
        1.5,
        "• user_key (PK)\n• sex, age_band\n• lifestyle (7 cols)\n• interests",
        fontsize=8,
        color=COLOR_TEXT_BLACK,
    )

    p_sw = patches.FancyBboxPatch(
        (5.5, 0.5),
        3.4,
        1.8,
        boxstyle="round,pad=0.08",
        facecolor=COLOR_CARD_BG,
        edgecolor=COLOR_HAIRLINE,
    )
    ax1.add_patch(p_sw)
    ax1.text(
        5.7, 1.9, "swipes / matches (Pairs)", fontweight="bold", color=COLOR_BLUE, fontsize=9.5
    )
    ax1.text(
        5.7,
        1.5,
        "• user_key / user_a_key\n• target_user_key / user_b_key\n• direction (y_right)\n• day",
        fontsize=8,
        color=COLOR_TEXT_BLACK,
    )

    p_ub = patches.FancyBboxPatch(
        (10.7, 0.5),
        3.2,
        1.8,
        boxstyle="round,pad=0.08",
        facecolor=COLOR_CARD_BG,
        edgecolor=COLOR_HAIRLINE,
    )
    ax1.add_patch(p_ub)
    ax1.text(10.9, 1.9, "users (User B)", fontweight="bold", color=COLOR_PURPLE_INK, fontsize=9.5)
    ax1.text(
        10.9,
        1.5,
        "• user_key (PK)\n• sex, age_band\n• lifestyle (7 cols)\n• interests",
        fontsize=8,
        color=COLOR_TEXT_BLACK,
    )

    ax1.annotate(
        "",
        xy=(5.4, 1.4),
        xytext=(3.8, 1.4),
        arrowprops={"arrowstyle": "->", "color": COLOR_PURPLE, "lw": 1.5},
    )
    ax1.annotate(
        "",
        xy=(9.0, 1.4),
        xytext=(10.6, 1.4),
        arrowprops={"arrowstyle": "->", "color": COLOR_PURPLE, "lw": 1.5},
    )
    ax1.text(4.2, 1.55, "JOIN user_a", fontsize=8, color=COLOR_PURPLE)
    ax1.text(9.4, 1.55, "JOIN user_b", fontsize=8, color=COLOR_PURPLE)

    # Pipeline 2: H3 & H4
    ax2 = axes[1]
    ax2.text(
        0.2,
        2.7,
        "Pipeline 2 (H3 & H4): Reciprocal Swipes & Historical Selectivity Join",
        fontsize=11,
        fontweight="bold",
        color=COLOR_BLUE,
    )

    p_sw1 = patches.FancyBboxPatch(
        (0.5, 0.5),
        3.2,
        1.8,
        boxstyle="round,pad=0.08",
        facecolor=COLOR_CARD_BG,
        edgecolor=COLOR_HAIRLINE,
    )
    ax2.add_patch(p_sw1)
    ax2.text(0.7, 1.9, "swipes (A → B)", fontweight="bold", color=COLOR_BLUE, fontsize=9.5)
    ax2.text(
        0.7,
        1.45,
        "• user_key (A)\n• target_user_key (B)\n• direction_A\n• day_A",
        fontsize=8,
        color=COLOR_TEXT_BLACK,
    )

    p_agg = patches.FancyBboxPatch(
        (5.5, 0.5),
        3.4,
        1.8,
        boxstyle="round,pad=0.08",
        facecolor=COLOR_CARD_BG,
        edgecolor=COLOR_HAIRLINE,
    )
    ax2.add_patch(p_agg)
    ax2.text(
        5.7, 1.9, "swipes_agg (Selectivity)", fontweight="bold", color=COLOR_PINK, fontsize=9.5
    )
    ax2.text(
        5.7,
        1.45,
        "• user_key\n• rate_right = mean(dir)\n• count()\n• grouped by day window",
        fontsize=8,
        color=COLOR_TEXT_BLACK,
    )

    p_sw2 = patches.FancyBboxPatch(
        (10.7, 0.5),
        3.2,
        1.8,
        boxstyle="round,pad=0.08",
        facecolor=COLOR_CARD_BG,
        edgecolor=COLOR_HAIRLINE,
    )
    ax2.add_patch(p_sw2)
    ax2.text(10.9, 1.9, "swipes (B → A)", fontweight="bold", color=COLOR_BLUE, fontsize=9.5)
    ax2.text(
        10.9,
        1.45,
        "• user_key (B)\n• target_user_key (A)\n• direction_B\n• day_B",
        fontsize=8,
        color=COLOR_TEXT_BLACK,
    )

    ax2.annotate(
        "",
        xy=(5.4, 1.4),
        xytext=(3.8, 1.4),
        arrowprops={"arrowstyle": "<->", "color": COLOR_PINK, "lw": 1.5},
    )
    ax2.annotate(
        "",
        xy=(9.0, 1.4),
        xytext=(10.6, 1.4),
        arrowprops={"arrowstyle": "<->", "color": COLOR_PINK, "lw": 1.5},
    )
    ax2.text(4.1, 1.55, "JOIN user_key", fontsize=8, color=COLOR_PINK)
    ax2.text(9.2, 1.55, "JOIN user_key", fontsize=8, color=COLOR_PINK)

    # Pipeline 3: H5
    ax3 = axes[2]
    ax3.text(
        0.2,
        2.7,
        "Pipeline 3 (H5): Versioned Bio Snapshot & Match Correlation",
        fontsize=11,
        fontweight="bold",
        color="#5A6268",
    )

    p_ph = patches.FancyBboxPatch(
        (0.5, 0.5),
        3.5,
        1.8,
        boxstyle="round,pad=0.08",
        facecolor=COLOR_CARD_BG,
        edgecolor=COLOR_HAIRLINE,
    )
    ax3.add_patch(p_ph)
    ax3.text(0.7, 1.9, "profile_history", fontweight="bold", color="#5A6268", fontsize=9.5)
    ax3.text(
        0.7,
        1.45,
        "• user_key, version\n• day (edit timestamp)\n• bio (text)\n• bio_length (int32)",
        fontsize=8,
        color=COLOR_TEXT_BLACK,
    )

    p_swp = patches.FancyBboxPatch(
        (5.8, 0.5),
        3.4,
        1.8,
        boxstyle="round,pad=0.08",
        facecolor=COLOR_CARD_BG,
        edgecolor=COLOR_HAIRLINE,
    )
    ax3.add_patch(p_swp)
    ax3.text(
        6.0, 1.9, "swipes / matches (Day T)", fontweight="bold", color=COLOR_BLUE, fontsize=9.5
    )
    ax3.text(
        6.0,
        1.45,
        "• user_key, target_user_key\n• decision day T\n• direction / match",
        fontsize=8,
        color=COLOR_TEXT_BLACK,
    )

    p_usr = patches.FancyBboxPatch(
        (10.8, 0.5),
        3.2,
        1.8,
        boxstyle="round,pad=0.08",
        facecolor=COLOR_CARD_BG,
        edgecolor=COLOR_HAIRLINE,
    )
    ax3.add_patch(p_usr)
    ax3.text(
        11.0, 1.9, "users (Current Profile)", fontweight="bold", color=COLOR_PURPLE, fontsize=9.5
    )
    ax3.text(
        11.0,
        1.45,
        "• current bio & length\n• structured traits\n• baseline comparison",
        fontsize=8,
        color=COLOR_TEXT_BLACK,
    )

    ax3.annotate(
        "",
        xy=(5.7, 1.4),
        xytext=(4.1, 1.4),
        arrowprops={"arrowstyle": "->", "color": "#5A6268", "lw": 1.5},
    )
    ax3.annotate(
        "",
        xy=(9.3, 1.4),
        xytext=(10.7, 1.4),
        arrowprops={"arrowstyle": "<-", "color": COLOR_PURPLE, "lw": 1.5},
    )
    ax3.text(4.4, 1.55, "JOIN user_key (day <= T)", fontsize=7.8, color="#5A6268")
    ax3.text(9.6, 1.55, "JOIN user_key", fontsize=7.8, color=COLOR_PURPLE)

    plt.tight_layout()
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=200, bbox_inches="tight")
    return fig


def plot_temporal_granularity_comparison(
    output_path: Path | None = None,
) -> plt.Figure:
    """Visualize temporal resolution across tables to address feasibility of H3 and H4."""
    fig, ax = plt.subplots(figsize=(14, 7), facecolor=COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    time_features = [
        ("swipes", "day", "int32", "Daily integer (0, 1, 2...)", "H1, H2, H3, H4"),
        ("matches", "day", "int32", "Daily integer", "H1, H2, H3, H4"),
        ("chats", "chat_created_day", "int32", "Daily integer", "H1, H2 (funnel)"),
        ("chats", "first_message_day", "float64", "Daily float", "Chat latency"),
        ("chats", "hours_to_first_message", "float64", "Hourly float", "First message speed"),
        ("profile_history", "day", "int32", "Daily integer", "H5 (profile edits)"),
        ("listings", "created_day", "int32", "Daily integer", "Listing age"),
    ]

    labels = [f"{t[0]}.{t[1]}" for t in time_features]
    y_pos = list(range(len(labels)))[::-1]

    for i, y in enumerate(y_pos):
        tbl, col, dtype, grain, hyps = time_features[i]
        is_subday = "hourly" in grain.lower()
        bar_col = COLOR_PINK if is_subday else COLOR_BLUE

        bar_len = 10 if is_subday else 6
        rect = patches.FancyBboxPatch(
            (0.5, y - 0.25),
            bar_len,
            0.5,
            boxstyle="round,pad=0.03,rounding_size=0.1",
            facecolor=bar_col,
            edgecolor=bar_col,
            alpha=0.85,
        )
        ax.add_patch(rect)

        ax.text(
            0.7,
            y,
            f"{tbl}.{col} ({dtype})",
            color="white",
            fontweight="bold",
            fontsize=9.5,
            va="center",
        )
        ax.text(
            bar_len + 0.8,
            y,
            f"Grain: {grain} | Relevant: {hyps}",
            color=COLOR_TEXT_BLACK,
            fontsize=9.0,
            va="center",
        )

    ax.set_xlim(0, 16)
    ax.set_ylim(-1, len(labels))
    ax.axis("off")

    ax.text(
        0.5,
        len(labels) - 0.3,
        "Temporal Resolution & Timestamp Availability Across Tables",
        fontsize=16,
        fontweight="bold",
        color=COLOR_TEXT_BLACK,
    )
    ax.text(
        0.5,
        len(labels) - 0.75,
        "Crucial for H3 & H4: Evaluates sequence vs daily aggregation support",
        fontsize=10.5,
        color=COLOR_TEXT_GRAY,
    )

    note_rect = patches.FancyBboxPatch(
        (0.5, -0.8),
        15.0,
        0.7,
        boxstyle="round,pad=0.04,rounding_size=0.08",
        facecolor=COLOR_CARD_BG,
        edgecolor=COLOR_HAIRLINE,
    )
    ax.add_patch(note_rect)
    ax.text(
        0.7,
        -0.45,
        "Key Observation: Swipes and matches carry 'day' (integer), but NO sub-day timestamps.\n"
        "Hourly resolution exists exclusively in 'chats.hours_to_first_message'.",
        fontsize=8.5,
        color=COLOR_PURPLE_INK,
        va="center",
    )

    plt.tight_layout()
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=200, bbox_inches="tight")
    return fig


def plot_table_column_composition(
    tables: dict[str, TableMetadata],
    output_path: Path | None = None,
) -> plt.Figure:
    """Plot column category composition breakdown across all tables."""
    categories = [
        "Key / ID",
        "Demographics / Goals",
        "Lifestyle / Interests",
        "Bio / Content",
        "Temporal",
        "Interaction / Status",
        "Listing Attributes",
    ]

    cat_colors = {
        "Key / ID": COLOR_PURPLE_INK,
        "Demographics / Goals": COLOR_PURPLE,
        "Lifestyle / Interests": COLOR_BLUE,
        "Bio / Content": COLOR_PINK,
        "Temporal": "#20C997",
        "Interaction / Status": "#FFC107",
        "Listing Attributes": "#6C757D",
    }

    table_names = list(tables.keys())
    data: dict[str, list[int]] = {cat: [] for cat in categories}

    for name in table_names:
        tbl = tables[name]
        counts: dict[str, int] = {cat: 0 for cat in categories}
        for col in tbl.columns:
            cat = tbl.get_column_category(col)
            counts[cat] = counts.get(cat, 0) + 1
        for cat in categories:
            data[cat].append(counts[cat])

    fig, ax = plt.subplots(figsize=(13, 7), facecolor=COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    bottom = [0] * len(table_names)
    bar_width = 0.55

    for cat in categories:
        values = data[cat]
        ax.bar(
            table_names,
            values,
            bar_width,
            bottom=bottom,
            label=cat,
            color=cat_colors[cat],
            edgecolor=COLOR_BG,
            linewidth=0.8,
        )
        bottom = [b + v for b, v in zip(bottom, values, strict=True)]

    ax.set_title(
        "Column Category Composition Across Tables (from metadata.txt)",
        fontsize=15,
        fontweight="bold",
        color=COLOR_TEXT_BLACK,
        pad=15,
    )
    ax.set_ylabel("Number of Columns", fontsize=11, color=COLOR_TEXT_BLACK)
    ax.tick_params(colors=COLOR_TEXT_BLACK)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLOR_HAIRLINE)
    ax.spines["bottom"].set_color(COLOR_HAIRLINE)
    ax.grid(axis="y", linestyle="--", alpha=0.35, color=COLOR_TEXT_GRAY)

    for i, name in enumerate(table_names):
        total = tables[name].column_count
        ax.text(
            i,
            total + 0.4,
            f"{total} cols",
            ha="center",
            fontsize=9.5,
            fontweight="bold",
            color=COLOR_TEXT_BLACK,
        )

    ax.legend(
        loc="upper left",
        bbox_to_anchor=(1.01, 1),
        facecolor=COLOR_CARD_BG,
        edgecolor=COLOR_HAIRLINE,
        fontsize=9.5,
    )

    plt.tight_layout()
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=200, bbox_inches="tight")
    return fig


def generate_all_visualizations(
    metadata_path: Path | str = "data/processed/metadata.txt",
    save_dir: Path | str = "reports/figures",
) -> list[Path]:
    """Parse schema metadata, perform schema joins, and generate all visualization figures.

    Args:
        metadata_path: Path to metadata.txt.
        save_dir: Directory where figures will be saved.

    Returns:
        List of generated figure file paths.
    """
    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)

    tables = parse_metadata_file(metadata_path)
    relationships = get_schema_relationships()
    mappings = get_hypothesis_mappings()

    fig_paths: list[Path] = []

    # 1. Relational ERD
    erd_path = save_path / "01_relational_schema_erd.png"
    fig_erd = plot_relational_schema_erd(tables, relationships, erd_path)
    plt.close(fig_erd)
    fig_paths.append(erd_path)

    # 2. Hypothesis-to-Schema Matrix
    matrix_path = save_path / "02_hypothesis_schema_matrix.png"
    fig_mat = plot_hypothesis_schema_matrix(mappings, matrix_path)
    plt.close(fig_mat)
    fig_paths.append(matrix_path)

    # 3. Joined Table Pipelines
    pipelines_path = save_path / "03_joined_table_pipelines.png"
    fig_pipe = plot_joined_table_pipelines(tables, pipelines_path)
    plt.close(fig_pipe)
    fig_paths.append(pipelines_path)

    # 4. Temporal Granularity Comparison
    temporal_path = save_path / "04_temporal_granularity.png"
    fig_temp = plot_temporal_granularity_comparison(temporal_path)
    plt.close(fig_temp)
    fig_paths.append(temporal_path)

    # 5. Table Column Composition
    composition_path = save_path / "05_table_column_composition.png"
    fig_comp = plot_table_column_composition(tables, composition_path)
    plt.close(fig_comp)
    fig_paths.append(composition_path)

    return fig_paths


def main() -> None:
    """CLI entrypoint for running structural EDA visualizations."""
    metadata_path = Path("data/processed/metadata.txt")
    figures_dir = Path("reports/figures")

    generated = generate_all_visualizations(metadata_path, figures_dir)
    for p in generated:
        print(f"Figure saved: {p}")


if __name__ == "__main__":
    main()
