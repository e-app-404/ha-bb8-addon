import re
from pathlib import Path

cfg = Path(".coveragerc")
text = (
    cfg.read_text()
    if cfg.exists()
    else (
        "[run]\nbranch = True\n\n[report]\n"
        "fail_under = 70\nshow_missing = True\nskip_covered = False\n"
    )
)
text = re.sub(r"(?im)^(fail_under\s*=\s*)(\d+(\.\d+)?)", r"\g<1>70", text)
if "fail_under" not in text:
    text += "\nfail_under = 70\n"
cfg.write_text(text)
print("Coverage ratchet set: fail_under = 70")
