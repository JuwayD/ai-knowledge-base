# AI Knowledge Base

This repository is the OpenClaw-native packaging of the Codex plugin from:

- `D:\WorkSpace\AIWorkSpace\codex-plugin\plugins\ai-knowledge-base`

It keeps the original Codex bundle structure for compatibility:

- `.codex-plugin/plugin.json`
- `skills/`
- `scripts/`
- `tools/`

It also adds an OpenClaw-native entry so the package can be installed and exposed as a native OpenClaw plugin.

## OpenClaw tools

- `kb_run`: run the bundled `scripts/kb.py` CLI with arbitrary subcommand arguments
- `kb_daily_check`: run the bundled `scripts/daily_check.py`

## Plugin config

- `kbHome`: override the knowledge-base data directory
- `pythonExecutable`: override the Python interpreter used to run the scripts

## Local test

```powershell
npm install
openclaw plugins install .
openclaw plugins enable ai-knowledge-base
openclaw gateway restart
```

Example tool behavior:

```powershell
python .\scripts\kb.py status
python .\scripts\daily_check.py --json
```
