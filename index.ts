import { execFile } from "node:child_process";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import { Type } from "@sinclair/typebox";
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

const execFileAsync = promisify(execFile);

type PluginConfig = {
  kbHome?: string;
  pythonExecutable?: string;
};

function getConfig(context: { pluginConfig?: unknown }): PluginConfig {
  return (context.pluginConfig ?? {}) as PluginConfig;
}

function getPythonExecutable(config: PluginConfig): string {
  return config.pythonExecutable?.trim() || "python";
}

function getEnv(config: PluginConfig): NodeJS.ProcessEnv {
  const env = { ...process.env, PYTHONIOENCODING: "utf-8" };
  if (config.kbHome?.trim()) {
    env.KB_HOME = config.kbHome.trim();
  }
  return env;
}

async function runPythonScript(
  scriptName: string,
  args: string[],
  config: PluginConfig,
): Promise<string> {
  const scriptPath = fileURLToPath(
    new URL(`./scripts/${scriptName}`, import.meta.url),
  );
  const { stdout, stderr } = await execFileAsync(
    getPythonExecutable(config),
    [scriptPath, ...args],
    {
      env: getEnv(config),
      encoding: "utf-8",
      windowsHide: true,
    },
  );

  const trimmedStdout = stdout.trim();
  const trimmedStderr = stderr.trim();
  return [trimmedStdout, trimmedStderr].filter(Boolean).join("\n");
}

export default definePluginEntry({
  id: "ai-knowledge-base",
  name: "AI Knowledge Base",
  description:
    "OpenClaw plugin that bundles the AI knowledge base CLI, daily check script, and Codex-compatible skills.",
  register(api) {
    api.registerTool({
      name: "kb_run",
      description:
        "Runs the bundled AI Knowledge Base CLI with the provided subcommand arguments.",
      parameters: Type.Object({
        args: Type.Array(
          Type.String({
            description:
              "CLI arguments, for example ['status'] or ['get', 'K-20260406-001'].",
          }),
        ),
      }),
      async execute(_callId, params, context) {
        const output = await runPythonScript(
          "kb.py",
          params.args,
          getConfig(context),
        );

        return {
          content: [
            {
              type: "text",
              text: output || "{}",
            },
          ],
        };
      },
    });

    api.registerTool({
      name: "kb_daily_check",
      description:
        "Runs the bundled daily knowledge-base check and returns either text or JSON output.",
      parameters: Type.Object({
        json: Type.Optional(
          Type.Boolean({
            description: "When true, append --json to the daily check script.",
          }),
        ),
      }),
      async execute(_callId, params, context) {
        const args = params.json ? ["--json"] : [];
        const output = await runPythonScript(
          "daily_check.py",
          args,
          getConfig(context),
        );

        return {
          content: [
            {
              type: "text",
              text: output || "{}",
            },
          ],
        };
      },
    });
  },
});
