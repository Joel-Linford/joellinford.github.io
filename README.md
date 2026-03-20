# Joel Linford WIP MkDocs Site

A simple work-in-progress personal website that can be pushed live quickly.

## Run locally

```bash
pip install -r requirements.txt
python scripts/generate_writing_index.py
mkdocs serve
```

## Build

```bash
python scripts/generate_writing_index.py
mkdocs build
```

## Notes

- Replace `docs/assets/images/logo-mark.svg` with your real header mark when ready.
- Replace `docs/assets/images/favicon.svg` with your real favicon when ready.
- Update links in `docs/contact.md` if needed.
