# OpenClaw native plugin

This plugin is a native OpenClaw plugin scaffold.

It was created under a dedicated subdirectory so it can be published as an independent GitHub repository without turning the parent directory into a repository.

Files:

- `openclaw.plugin.json`: native OpenClaw manifest
- `package.json`: package metadata and OpenClaw runtime entry declaration
- `index.ts`: runtime entry that registers a sample `starter_echo` tool

Local test:

```powershell
npm install
openclaw plugins install .
openclaw plugins enable openclaw-native-plugin
openclaw gateway restart
```
