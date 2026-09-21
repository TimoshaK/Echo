"""Pure SRT helpers — no tkinter, no file dialogs, no message boxes."""


def time_to_srt(seconds: float, offset: float = 0.0) -> str:
    total = int(seconds + offset)
    millis = int((seconds + offset - total) * 1000)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def build_srt_content(segments: list) -> str:
    lines = []
    for idx, seg in enumerate(segments, start=1):
        start = time_to_srt(float(seg.get("start", 0)))
        end = time_to_srt(float(seg.get("end", 0)))
        text = str(seg.get("text", "")).strip()
        lines.append(f"{idx}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)
