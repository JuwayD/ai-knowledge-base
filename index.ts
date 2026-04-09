import { Type } from "@sinclair/typebox";
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

export default definePluginEntry({
  id: "ai-knowledge-base",
  name: "AI Knowledge Base",
  description: "A minimal native OpenClaw plugin with one sample tool.",
  register(api) {
    api.registerTool({
      name: "starter_echo",
      description: "Echoes text so the plugin can be validated end-to-end.",
      parameters: Type.Object({
        input: Type.String(),
      }),
      async execute(_callId, params, context) {
        const config = (context.pluginConfig ?? {}) as { prefix?: string };
        const prefix = config.prefix?.trim() ? `${config.prefix.trim()} ` : "";

        return {
          content: [
            {
              type: "text",
              text: `${prefix}${params.input}`,
            },
          ],
        };
      },
    });
  },
});
