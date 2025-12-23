from __future__ import annotations
from typing import Iterable
import gradio as gr
from gradio.themes.base import Base
from gradio.themes.utils import colors, fonts, sizes

class CustomTheme(Base):
    def __init__(
        self,
        *,
        primary_hue: colors.Color | str = colors.indigo,
        secondary_hue: colors.Color | str = colors.blue,
        neutral_hue: colors.Color | str = colors.slate,
        spacing_size: sizes.Size | str = sizes.spacing_md,
        radius_size: sizes.Size | str = sizes.radius_lg,
        text_size: sizes.Size | str = sizes.text_md,
        font: fonts.Font | str | Iterable[fonts.Font | str] = (
            fonts.GoogleFont("Inter"),
            "ui-sans-serif",
            "system-ui",
            "sans-serif",
        ),
        font_mono: fonts.Font | str | Iterable[fonts.Font | str] = (
            fonts.GoogleFont("JetBrains Mono"),
            "ui-monospace",
            "Consolas",
            "monospace",
        ),
    ):
        super().__init__(
            primary_hue=primary_hue,
            secondary_hue=secondary_hue,
            neutral_hue=neutral_hue,
            spacing_size=spacing_size,
            radius_size=radius_size,
            text_size=text_size,
            font=font,
            font_mono=font_mono,
        )
        super().set(
            body_background_fill="white",
            body_background_fill_dark="*neutral_950",
            body_text_color="*neutral_950",
            body_text_color_dark="*neutral_50",
            background_fill_primary="white",
            background_fill_primary_dark="*neutral_900",
            background_fill_secondary="#f9fafb",
            background_fill_secondary_dark="*neutral_800",
            border_color_primary="#e5e7eb",
            border_color_primary_dark="*neutral_700",
            block_background_fill="white",
            block_background_fill_dark="*neutral_900",
            block_label_background_fill="white",
            block_label_background_fill_dark="*neutral_900",
            input_background_fill="white",
            input_background_fill_dark="*neutral_800",
            button_primary_background_fill="*primary_600",
            button_primary_background_fill_hover="*primary_700",
            button_primary_text_color="white",
            button_secondary_background_fill="white",
            button_secondary_background_fill_hover="#f3f4f6",
            button_secondary_text_color="*neutral_800",
            block_title_text_color="*neutral_800",
            block_title_text_color_dark="*neutral_200",
            block_label_text_color="*neutral_500",
            block_label_text_color_dark="*neutral_400",
            input_border_color="#e5e7eb",
            input_border_color_dark="*neutral_700",
            input_border_width="1px",
            input_shadow="0 1px 2px 0 rgb(0 0 0 / 0.05)",
            input_shadow_focus="0 0 0 2px *primary_500",
        )
