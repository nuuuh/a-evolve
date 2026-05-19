from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "figure2_icon_pack"
PNG = OUT / "png_1024"
SHEET = OUT / "figure2_icon_sheet.png"
MANIFEST = OUT / "manifest.json"

CANVAS = 2048
EXPORT = 1024

BLUE = "#1646a3"
GREEN = "#16743a"
RED = "#e24222"
ORANGE = "#ef6c1a"
PURPLE = "#4b2e94"
TEAL = "#0b6f7a"
SLATE = "#263238"
GRAY = "#5b6470"
LIGHT = "#f7faff"
WHITE = "#ffffff"
BLACK = "#101828"
_FONT_PATH_CACHE: dict[bool, list[Path]] = {}


def xy(*vals: float) -> tuple[int, ...]:
    return tuple(round(v * CANVAS / 1000) for v in vals)


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if bold not in _FONT_PATH_CACHE:
        preferred = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        candidates = [
            Path("/usr/share/fonts/truetype/dejavu") / preferred,
            Path("/usr/share/fonts/dejavu") / preferred,
            Path("/home/ec2-user/miniconda3/lib/python3.13/site-packages/matplotlib/mpl-data/fonts/ttf") / preferred,
            Path("/home/ec2-user/miniconda3/envs/epilearn/lib/python3.11/site-packages/matplotlib/mpl-data/fonts/ttf") / preferred,
        ]
        _FONT_PATH_CACHE[bold] = [p for p in candidates if p.exists()]
    for name in _FONT_PATH_CACHE[bold]:
        try:
            return ImageFont.truetype(name, round(size * CANVAS / 1000))
        except OSError:
            pass
    return ImageFont.load_default()


def center_text(d: ImageDraw.ImageDraw, text: str, box: tuple[int, int, int, int], fill: str, size: int, bold: bool = True) -> None:
    f = font(size, bold)
    bbox = d.textbbox((0, 0), text, font=f)
    x = box[0] + (box[2] - box[0] - (bbox[2] - bbox[0])) / 2
    y = box[1] + (box[3] - box[1] - (bbox[3] - bbox[1])) / 2 - CANVAS * 0.01
    d.text((x, y), text, font=f, fill=fill)


def font_px(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if bold not in _FONT_PATH_CACHE:
        font(40, bold)
    for name in _FONT_PATH_CACHE[bold]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def tile(d: ImageDraw.ImageDraw, color: str = BLUE, fill: str = WHITE) -> None:
    d.rounded_rectangle(xy(110, 110, 890, 890), radius=xy(58)[0], fill=fill, outline=color, width=xy(24)[0])


def chip(d: ImageDraw.ImageDraw, color: str, text: str) -> None:
    d.rounded_rectangle(xy(115, 320, 885, 680), radius=xy(70)[0], fill=color, outline=color, width=xy(16)[0])
    center_text(d, text, xy(115, 320, 885, 680), WHITE, 150)


def line_arrow(d: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], fill: str, width: int) -> None:
    d.line([start, end], fill=fill, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    size = width * 3.2
    pts = []
    for a in (angle, angle + 2.55, angle - 2.55):
        pts.append((end[0] - math.cos(a) * size, end[1] - math.sin(a) * size))
    d.polygon([end, pts[1], pts[2]], fill=fill)


def draw_bar_chart(d: ImageDraw.ImageDraw) -> None:
    tile(d, BLUE)
    d.line([xy(270, 720), xy(755, 720)], fill=BLUE, width=xy(28)[0])
    for x, h in [(330, 160), (490, 280), (650, 420)]:
        d.rounded_rectangle(xy(x, 720 - h, x + 90, 720), radius=xy(18)[0], fill=BLUE)


def draw_soccer(d: ImageDraw.ImageDraw) -> None:
    tile(d, GREEN)
    d.ellipse(xy(245, 245, 755, 755), outline=BLACK, width=xy(30)[0], fill=WHITE)
    cx, cy = xy(500, 500)
    r = xy(90)[0]
    pts = [(cx + math.cos(-math.pi / 2 + i * 2 * math.pi / 5) * r, cy + math.sin(-math.pi / 2 + i * 2 * math.pi / 5) * r) for i in range(5)]
    d.polygon(pts, fill=BLACK)
    for a in [0, 72, 144, 216, 288]:
        x = 500 + 220 * math.cos(math.radians(a))
        y = 500 + 220 * math.sin(math.radians(a))
        d.line([xy(500, 500), xy(x, y)], fill=BLACK, width=xy(16)[0])


def draw_lock(d: ImageDraw.ImageDraw) -> None:
    tile(d, PURPLE)
    d.rounded_rectangle(xy(285, 455, 715, 760), radius=xy(45)[0], fill=PURPLE)
    d.arc(xy(340, 240, 660, 590), 180, 360, fill=PURPLE, width=xy(70)[0])
    d.ellipse(xy(465, 565, 535, 635), fill=WHITE)
    d.rounded_rectangle(xy(485, 620, 515, 705), radius=xy(12)[0], fill=WHITE)


def draw_trend(d: ImageDraw.ImageDraw) -> None:
    tile(d, RED)
    d.line([xy(260, 720), xy(260, 280)], fill=SLATE, width=xy(22)[0])
    d.line([xy(260, 720), xy(750, 720)], fill=SLATE, width=xy(22)[0])
    pts = [xy(300, 660), xy(415, 560), xy(520, 610), xy(680, 390)]
    d.line(pts, fill=BLACK, width=xy(34)[0], joint="curve")
    line_arrow(d, xy(615, 470), xy(735, 335), BLACK, xy(32)[0])


def draw_globe(d: ImageDraw.ImageDraw) -> None:
    tile(d, ORANGE)
    d.ellipse(xy(245, 245, 755, 755), outline=BLACK, width=xy(30)[0])
    d.arc(xy(345, 245, 655, 755), 90, 270, fill=BLACK, width=xy(22)[0])
    d.arc(xy(345, 245, 655, 755), -90, 90, fill=BLACK, width=xy(22)[0])
    d.line([xy(245, 500), xy(755, 500)], fill=BLACK, width=xy(22)[0])
    d.arc(xy(260, 345, 740, 655), 0, 360, fill=BLACK, width=xy(18)[0])


def draw_chat(d: ImageDraw.ImageDraw) -> None:
    d.rounded_rectangle(xy(95, 235, 690, 600), radius=xy(120)[0], fill=RED)
    d.polygon([xy(280, 600), xy(210, 735), xy(410, 610)], fill=RED)
    d.rounded_rectangle(xy(380, 405, 905, 720), radius=xy(105)[0], fill="#f04d37")
    d.polygon([xy(620, 715), xy(720, 850), xy(735, 700)], fill="#f04d37")
    for x in (265, 390, 515):
        d.ellipse(xy(x - 32, 405, x + 32, 470), fill=WHITE)
    for x in (535, 650, 765):
        d.ellipse(xy(x - 28, 545, x + 28, 602), fill=WHITE)


def draw_person(d: ImageDraw.ImageDraw) -> None:
    tile(d, BLUE)
    d.ellipse(xy(390, 205, 610, 425), fill=BLUE)
    d.rounded_rectangle(xy(260, 480, 740, 775), radius=xy(100)[0], fill=BLUE)
    d.rectangle(xy(260, 630, 740, 775), fill=BLUE)


def draw_clock(d: ImageDraw.ImageDraw) -> None:
    tile(d, GRAY)
    d.ellipse(xy(240, 240, 760, 760), outline=SLATE, width=xy(34)[0], fill=WHITE)
    d.line([xy(500, 500), xy(500, 330)], fill=GREEN, width=xy(26)[0])
    d.line([xy(500, 500), xy(650, 560)], fill=GREEN, width=xy(26)[0])
    d.ellipse(xy(470, 470, 530, 530), fill=GREEN)
    for a in [0, 90, 180, 270]:
        x = 500 + 220 * math.cos(math.radians(a))
        y = 500 + 220 * math.sin(math.radians(a))
        d.ellipse(xy(x - 16, y - 16, x + 16, y + 16), fill=SLATE)


def draw_document(d: ImageDraw.ImageDraw, color: str = BLUE, symbol: str | None = None) -> None:
    tile(d, color)
    d.polygon([xy(320, 165), xy(625, 165), xy(760, 300), xy(760, 835), xy(320, 835)], fill=WHITE, outline=color)
    d.line([xy(625, 165), xy(625, 300), xy(760, 300)], fill=color, width=xy(24)[0])
    for y in (410, 515, 620):
        d.line([xy(395, y), xy(685, y)], fill=color, width=xy(24)[0])
    if symbol:
        center_text(d, symbol, xy(350, 640, 730, 805), color, 150)


def draw_task_board(d: ImageDraw.ImageDraw) -> None:
    tile(d, BLUE)
    d.rounded_rectangle(xy(210, 250, 790, 760), radius=xy(34)[0], fill=WHITE, outline=BLUE, width=xy(20)[0])
    d.rectangle(xy(210, 250, 790, 345), fill="#eaf0ff", outline=BLUE)
    d.line([xy(400, 250), xy(400, 760)], fill=BLUE, width=xy(12)[0])
    d.line([xy(590, 250), xy(590, 760)], fill=BLUE, width=xy(12)[0])
    for y in (450, 565, 680):
        d.line([xy(210, y), xy(790, y)], fill="#aebbdc", width=xy(10)[0])
    for idx, (y, color, label) in enumerate([(390, BLUE, "A"), (505, GREEN, "B"), (620, PURPLE, "C")]):
        d.ellipse(xy(255, y - 35, 325, y + 35), fill=color)
        center_text(d, label, xy(255, y - 38, 325, y + 35), WHITE, 46)
    d.rounded_rectangle(xy(425, 355, 560, 425), radius=xy(20)[0], fill=RED)
    d.rounded_rectangle(xy(425, 470, 560, 540), radius=xy(20)[0], fill=ORANGE)
    d.rounded_rectangle(xy(425, 585, 560, 655), radius=xy(20)[0], fill=GREEN)
    center_text(d, "main", xy(615, 350, 760, 430), BLUE, 42)
    center_text(d, "branch", xy(605, 465, 770, 545), GREEN, 40)
    center_text(d, "branch", xy(605, 580, 770, 660), RED, 40)


def draw_lightbulb(d: ImageDraw.ImageDraw) -> None:
    tile(d, GRAY)
    d.ellipse(xy(330, 205, 670, 545), outline=BLACK, width=xy(30)[0], fill=WHITE)
    d.line([xy(430, 585), xy(570, 585)], fill=BLACK, width=xy(34)[0])
    d.line([xy(455, 660), xy(545, 660)], fill=BLACK, width=xy(34)[0])
    d.line([xy(500, 545), xy(500, 610)], fill=BLACK, width=xy(24)[0])
    for x in (455, 500, 545):
        d.line([xy(x, 545), xy(x, 610)], fill="#c9ccd1", width=xy(14)[0])


def draw_flask(d: ImageDraw.ImageDraw) -> None:
    tile(d, GRAY)
    d.line([xy(420, 190), xy(580, 190)], fill=BLACK, width=xy(30)[0])
    d.line([xy(455, 190), xy(455, 455)], fill=BLACK, width=xy(24)[0])
    d.line([xy(545, 190), xy(545, 455)], fill=BLACK, width=xy(24)[0])
    d.polygon([xy(455, 455), xy(305, 785), xy(695, 785), xy(545, 455)], outline=BLACK, fill=WHITE)
    d.polygon([xy(370, 650), xy(630, 650), xy(695, 785), xy(305, 785)], fill="#dff5e5")
    d.line([xy(455, 455), xy(305, 785), xy(695, 785), xy(545, 455)], fill=BLACK, width=xy(24)[0])
    d.ellipse(xy(450, 700, 495, 745), fill=GREEN)
    d.ellipse(xy(555, 680, 600, 725), fill=GREEN)


def draw_magnifier(d: ImageDraw.ImageDraw) -> None:
    tile(d, GRAY)
    d.ellipse(xy(250, 250, 610, 610), outline=BLACK, width=xy(42)[0], fill=WHITE)
    d.line([xy(560, 560), xy(760, 760)], fill=BLACK, width=xy(55)[0])


def draw_cube(d: ImageDraw.ImageDraw) -> None:
    tile(d, GRAY)
    top = [xy(500, 215), xy(720, 345), xy(500, 475), xy(280, 345)]
    left = [xy(280, 345), xy(500, 475), xy(500, 760), xy(280, 630)]
    right = [xy(720, 345), xy(500, 475), xy(500, 760), xy(720, 630)]
    d.polygon(top, fill="#f2f4f7", outline=BLACK)
    d.polygon(left, fill="#e1e8f5", outline=BLACK)
    d.polygon(right, fill="#d1dae8", outline=BLACK)
    for pts in (top, left, right):
        d.line(pts + [pts[0]], fill=BLACK, width=xy(22)[0])


def draw_database(d: ImageDraw.ImageDraw) -> None:
    tile(d, GRAY)
    for y in (295, 435, 575):
        d.ellipse(xy(290, y - 85, 710, y + 85), outline=BLACK, width=xy(24)[0], fill=WHITE)
        d.rectangle(xy(290, y, 710, y + 120), fill=WHITE)
        d.arc(xy(290, y + 35, 710, y + 205), 0, 180, fill=BLACK, width=xy(24)[0])
        d.line([xy(290, y), xy(290, y + 120)], fill=BLACK, width=xy(24)[0])
        d.line([xy(710, y), xy(710, y + 120)], fill=BLACK, width=xy(24)[0])


def draw_check(d: ImageDraw.ImageDraw) -> None:
    d.ellipse(xy(120, 120, 880, 880), fill=GREEN)
    d.line([xy(300, 520), xy(445, 665), xy(725, 340)], fill=WHITE, width=xy(90)[0], joint="curve")


def draw_x(d: ImageDraw.ImageDraw) -> None:
    d.ellipse(xy(120, 120, 880, 880), fill="#2d2d2d")
    d.line([xy(330, 330), xy(670, 670)], fill=WHITE, width=xy(85)[0])
    d.line([xy(670, 330), xy(330, 670)], fill=WHITE, width=xy(85)[0])


def draw_git_graph(d: ImageDraw.ImageDraw) -> None:
    tile(d, TEAL)
    d.line([xy(285, 315), xy(505, 505), xy(720, 300)], fill=BLACK, width=xy(30)[0])
    d.line([xy(505, 505), xy(505, 760)], fill=BLACK, width=xy(30)[0])
    for x, y, color in [(285, 315, BLUE), (505, 505, GREEN), (720, 300, ORANGE), (505, 760, GREEN)]:
        d.ellipse(xy(x - 55, y - 55, x + 55, y + 55), fill=color, outline=BLACK, width=xy(18)[0])


def draw_create_branch(d: ImageDraw.ImageDraw) -> None:
    tile(d, GREEN)
    d.ellipse(xy(230, 230, 500, 500), fill=GREEN)
    d.line([xy(365, 285), xy(365, 445)], fill=WHITE, width=xy(48)[0])
    d.line([xy(285, 365), xy(445, 365)], fill=WHITE, width=xy(48)[0])
    d.line([xy(385, 625), xy(620, 625), xy(735, 490)], fill=GREEN, width=xy(34)[0])
    for x, y in [(385, 625), (620, 625), (735, 490)]:
        d.ellipse(xy(x - 38, y - 38, x + 38, y + 38), fill=WHITE, outline=GREEN, width=xy(24)[0])


def draw_update(d: ImageDraw.ImageDraw) -> None:
    tile(d, ORANGE)
    d.arc(xy(235, 250, 765, 760), 30, 205, fill=ORANGE, width=xy(58)[0])
    d.arc(xy(235, 250, 765, 760), 210, 25, fill=ORANGE, width=xy(58)[0])
    d.polygon([xy(278, 335), xy(245, 505), xy(400, 430)], fill=ORANGE)
    d.polygon([xy(722, 675), xy(755, 505), xy(600, 580)], fill=ORANGE)


def draw_checkout(d: ImageDraw.ImageDraw) -> None:
    tile(d, TEAL)
    d.rounded_rectangle(xy(210, 275, 790, 725), radius=xy(50)[0], fill="#212832", outline=TEAL, width=xy(24)[0])
    d.line([xy(315, 400), xy(430, 500), xy(315, 600)], fill=WHITE, width=xy(42)[0], joint="curve")
    d.line([xy(485, 600), xy(680, 600)], fill=WHITE, width=xy(42)[0])


def draw_hammer(d: ImageDraw.ImageDraw) -> None:
    tile(d, RED)
    d.polygon([xy(420, 250), xy(695, 405), xy(635, 500), xy(360, 345)], fill=RED)
    d.polygon([xy(315, 360), xy(420, 250), xy(465, 315), xy(365, 425)], fill=RED)
    d.rounded_rectangle(xy(470, 465, 610, 820), radius=xy(45)[0], fill=ORANGE, outline=RED, width=xy(18)[0])
    d.line([xy(540, 470), xy(345, 740)], fill=RED, width=xy(55)[0])


def draw_shield(d: ImageDraw.ImageDraw) -> None:
    tile(d, PURPLE)
    shield = [xy(500, 165), xy(745, 265), xy(710, 560), xy(500, 805), xy(290, 560), xy(255, 265)]
    d.polygon(shield, fill=PURPLE)
    d.line([xy(365, 500), xy(465, 610), xy(655, 380)], fill=WHITE, width=xy(58)[0], joint="curve")


def draw_harness_tree(d: ImageDraw.ImageDraw) -> None:
    tile(d, BLUE)
    d.line([xy(345, 205), xy(345, 820)], fill=BLACK, width=xy(24)[0])
    for y in (220, 360, 500, 640, 780):
        d.ellipse(xy(305, y - 40, 385, y + 40), fill="#333333", outline=BLACK, width=xy(10)[0])
    d.line([xy(345, 360), xy(560, 360), xy(710, 290)], fill=GREEN, width=xy(24)[0])
    d.line([xy(345, 620), xy(560, 620), xy(735, 710)], fill=RED, width=xy(24)[0])
    d.ellipse(xy(690, 250, 770, 330), fill=GREEN, outline=BLACK, width=xy(10)[0])
    d.ellipse(xy(715, 670, 795, 750), fill=RED, outline=BLACK, width=xy(10)[0])


def draw_updated_tree(d: ImageDraw.ImageDraw) -> None:
    tile(d, GREEN)
    draw_harness_tree(d)
    d.rounded_rectangle(xy(560, 560, 875, 875), radius=xy(55)[0], fill=WHITE, outline=GREEN, width=xy(22)[0])
    d.line([xy(625, 720), xy(700, 795), xy(820, 635)], fill=GREEN, width=xy(45)[0])


def draw_router(d: ImageDraw.ImageDraw) -> None:
    tile(d, GREEN)
    center = xy(330, 500)
    for end in [xy(690, 290), xy(690, 500), xy(690, 710)]:
        line_arrow(d, center, end, GREEN, xy(28)[0])
    d.ellipse(xy(245, 415, 415, 585), fill=WHITE, outline=GREEN, width=xy(30)[0])
    d.ellipse(xy(655, 255, 725, 325), fill=BLUE)
    d.ellipse(xy(655, 465, 725, 535), fill=GREEN)
    d.ellipse(xy(655, 675, 725, 745), fill=RED)


def draw_search_docs(d: ImageDraw.ImageDraw) -> None:
    tile(d, BLUE)
    for offset in (0, 115):
        d.rounded_rectangle(xy(235 + offset, 235, 560 + offset, 700), radius=xy(35)[0], fill=WHITE, outline="#aebbdc", width=xy(18)[0])
        for y in (340, 435, 530):
            d.line([xy(290 + offset, y), xy(505 + offset, y)], fill="#9aa5b1", width=xy(18)[0])
    d.ellipse(xy(455, 460, 695, 700), outline=BLACK, width=xy(34)[0])
    d.line([xy(650, 650), xy(785, 785)], fill=BLACK, width=xy(42)[0])


def draw_robot(d: ImageDraw.ImageDraw) -> None:
    tile(d, BLUE)
    d.line([xy(500, 185), xy(500, 285)], fill=GREEN, width=xy(24)[0])
    d.ellipse(xy(465, 150, 535, 220), fill=GREEN)
    d.rounded_rectangle(xy(260, 285, 740, 625), radius=xy(80)[0], fill="#f3f8ff", outline=BLUE, width=xy(28)[0])
    d.ellipse(xy(365, 420, 445, 500), fill=BLACK)
    d.ellipse(xy(555, 420, 635, 500), fill=BLACK)
    d.rounded_rectangle(xy(365, 660, 635, 820), radius=xy(36)[0], fill="#2f3a45", outline=BLUE, width=xy(20)[0])
    d.line([xy(260, 430), xy(175, 430)], fill=BLUE, width=xy(34)[0])
    d.line([xy(740, 430), xy(825, 430)], fill=BLUE, width=xy(34)[0])


def draw_result(d: ImageDraw.ImageDraw) -> None:
    tile(d, GREEN)
    d.ellipse(xy(190, 270, 540, 620), fill=GREEN)
    d.line([xy(285, 455), xy(385, 555), xy(500, 375)], fill=WHITE, width=xy(55)[0])
    center_text(d, "result", xy(500, 360, 830, 590), GREEN, 105)


def draw_branch_chip(d: ImageDraw.ImageDraw, color: str, text: str) -> None:
    d.rounded_rectangle(xy(100, 275, 900, 725), radius=xy(70)[0], fill=WHITE, outline=color, width=xy(28)[0])
    center_text(d, text, xy(135, 275, 865, 725), color, 110)


def draw_artifact_doc(color: str, label: str) -> Callable[[ImageDraw.ImageDraw], None]:
    def _draw(d: ImageDraw.ImageDraw) -> None:
        draw_document(d, color)
        center_text(d, label, xy(165, 690, 835, 870), color, 72)

    return _draw


def draw_artifact_chip(color: str, label: str) -> Callable[[ImageDraw.ImageDraw], None]:
    def _draw(d: ImageDraw.ImageDraw) -> None:
        chip(d, color, label)

    return _draw


ICONS: list[tuple[str, Callable[[ImageDraw.ImageDraw], None]]] = [
    ("task_bar_chart", draw_bar_chart),
    ("task_soccer", draw_soccer),
    ("task_lock", draw_lock),
    ("task_trend", draw_trend),
    ("task_globe", draw_globe),
    ("hitl_chat", draw_chat),
    ("analyst_person", draw_person),
    ("reveal_clock", draw_clock),
    ("document", lambda d: draw_document(d, BLUE)),
    ("task_board", draw_task_board),
    ("research_lightbulb", draw_lightbulb),
    ("research_flask", draw_flask),
    ("research_magnifier", draw_magnifier),
    ("research_cube", draw_cube),
    ("research_database", draw_database),
    ("success_check", draw_check),
    ("failure_x", draw_x),
    ("git_graph", draw_git_graph),
    ("git_create", draw_create_branch),
    ("git_update", draw_update),
    ("git_checkout", draw_checkout),
    ("builder_hammer", draw_hammer),
    ("verifier_shield", draw_shield),
    ("harness_tree", draw_harness_tree),
    ("updated_harness_tree", draw_updated_tree),
    ("runtime_router", draw_router),
    ("routing_search_docs", draw_search_docs),
    ("solver_robot", draw_robot),
    ("result_check", draw_result),
    ("branch_main", lambda d: draw_branch_chip(d, BLUE, "main")),
    ("branch_a", lambda d: draw_branch_chip(d, GREEN, "branch A")),
    ("branch_b", lambda d: draw_branch_chip(d, RED, "branch B")),
    ("workspace_task_board", draw_artifact_doc(BLUE, "task_board")),
    ("workspace_research_log", draw_artifact_doc(GREEN, "research_log")),
    ("workspace_architecture", draw_artifact_doc(RED, "architecture")),
    ("workspace_strategy_tree", draw_artifact_doc(PURPLE, "strategy_tree")),
    ("artifact_prompt", draw_artifact_chip(PURPLE, "prompt")),
    ("artifact_skills", draw_artifact_chip(GREEN, "skills")),
    ("artifact_memory", draw_artifact_chip(ORANGE, "memory")),
    ("artifact_tools", draw_artifact_chip(BLUE, "tools")),
]


def render_icon(name: str, draw_fn: Callable[[ImageDraw.ImageDraw], None]) -> Path:
    img = Image.new("RGBA", (CANVAS, CANVAS), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    draw_fn(draw)
    img = img.resize((EXPORT, EXPORT), Image.Resampling.LANCZOS)
    out = PNG / f"{name}.png"
    img.save(out)
    return out


def make_sheet(files: list[tuple[str, Path]]) -> None:
    cols = 8
    cell = 360
    label_h = 72
    rows = math.ceil(len(files) / cols)
    sheet = Image.new("RGBA", (cols * cell, rows * (cell + label_h)), WHITE)
    draw = ImageDraw.Draw(sheet)
    small_font = font_px(20, True)
    for idx, (name, path) in enumerate(files):
        col = idx % cols
        row = idx // cols
        icon = Image.open(path).convert("RGBA").resize((260, 260), Image.Resampling.LANCZOS)
        x = col * cell + 50
        y = row * (cell + label_h) + 34
        sheet.alpha_composite(icon, (x, y))
        parts = name.split("_")
        lines: list[str] = []
        current = ""
        for part in parts:
            candidate = part if not current else f"{current}_{part}"
            if len(candidate) <= 16:
                current = candidate
            else:
                lines.append(current)
                current = part
        if current:
            lines.append(current)
        top = row * (cell + label_h) + cell - 42
        for li, line in enumerate(lines[:3]):
            bbox = draw.textbbox((0, 0), line, font=small_font)
            tx = col * cell + (cell - (bbox[2] - bbox[0])) / 2
            draw.text((tx, top + li * 22), line, font=small_font, fill=BLACK)
    sheet.convert("RGB").save(SHEET)


def main() -> None:
    PNG.mkdir(parents=True, exist_ok=True)
    files = [(name, render_icon(name, fn)) for name, fn in ICONS]
    make_sheet(files)
    MANIFEST.write_text(
        json.dumps(
            {
                "source": "Figure 2 icon vocabulary recreated from Image #1",
                "format": "transparent PNG",
                "size_px": EXPORT,
                "count": len(files),
                "icons": [{"name": name, "path": str(path.relative_to(OUT))} for name, path in files],
                "contact_sheet": str(SHEET.relative_to(OUT)),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(files)} icons to {PNG}")
    print(f"Wrote contact sheet to {SHEET}")


if __name__ == "__main__":
    main()
