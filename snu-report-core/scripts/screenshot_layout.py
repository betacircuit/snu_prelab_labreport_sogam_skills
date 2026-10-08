"""Preserve readable, equal text scale in screenshots with different crop/zoom sizes."""
from pathlib import Path
import re
from PIL import Image


def homework_sections(markdown):
    """Keep photo requirements active for plain, numbered and legacy HW headings."""
    ordinal = 0
    for match in re.finditer(r"(?ms)^# +([^\n]+)\n(.*?)(?=^# |\Z)", markdown + "\n"):
        title, section = match.groups()
        if re.search(r"\{[^}]*?(?:\.unnumbered|(?<!\S)-(?!\S))[^}]*\}", title):
            continue
        ordinal += 1
        explicit = re.match(r"(?:Problem\s+)?(\d+)[.)]?\s+", title, re.I)
        yield explicit.group(1) if explicit else str(ordinal), section


def normalize_screenshots(markdown, source_dir, lab_dir, style):
    """line-px is the measured source baseline pitch, not screenshot DPI metadata.

    All marked images use one physical line pitch. Reject overflow rather than
    silently shrinking individual screenshots and destroying that invariant.
    """
    from build import IMG_RE
    target = float(style.get('screenshots', {}).get('line_pitch_pt', 10.5))
    if target <= 0:
        raise ValueError('screenshots.line_pitch_pt must be positive')
    frames = style.get('frames', {})
    page = style.get('page', {})
    margins = page.get('margin_mm', {})
    page_width = 210 - margins.get('left', 25) - margins.get('right', 25)
    maximum_width = min(frames.get('max_width_mm', 140), page_width) * 72 / 25.4
    output = []
    in_code = False
    for line in markdown.splitlines():
        if line.lstrip().startswith('```'):
            in_code = not in_code
        match = None if in_code else IMG_RE.match(line)
        attr = match['attr'] if match else None
        pitch = re.search(r'(?<![\w-])line-px=([0-9.]+)(?=\s|})', attr or '')
        if pitch:
            source_pitch = float(pitch.group(1))
            if source_pitch <= 0:
                raise ValueError('line-px must be positive')
            src = match['src']
            if not src.startswith('snu-missing:'):
                path = next((Path(base) / src for base in (source_dir, lab_dir)
                             if (Path(base) / src).is_file()), None)
                if path is None:
                    raise FileNotFoundError(src)
                with Image.open(path) as picture:
                    width, height = picture.size
                width_pt, height_pt = width / source_pitch * target, height / source_pitch * target
                limit = frames.get('portrait_max_height_mm', 80) if height / width >= 1.25 else frames.get('max_height_mm', 95)
                if width_pt > maximum_width + .05 or height_pt > limit * 72 / 25.4 + .05:
                    raise ValueError(f'{src}: equal text scale exceeds figure bounds; crop margins or split the screenshot')
                attr = re.sub(r'(?<![\w-])(?:line-px|width|height)=[^\s}]+', '', attr)
                attr = attr[:-1].rstrip() + f' width={width_pt:.3f}pt' + '}'
                line = f"{match.group(1)}![{match['cap']}]({src}){attr}"
        output.append(line)
    return '\n'.join(output)
