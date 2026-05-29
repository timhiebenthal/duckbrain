/**
 * Probe plugin — verifies system.transform hook pipeline end-to-end.
 * Install: cp this file to ~/.config/opencode/plugins/
 * Test: start session, ask "Does your system prompt contain PROBE_123? yes or no."
 * Verify: look for [probe] messages in OpenCode's stderr output.
 */
export const ProbePlugin = async (ctx) => {
  process.stderr.write("[probe] Plugin loaded\n");

  return {
    "experimental.chat.system.transform": async (input, output) => {
      process.stderr.write(`[probe] Hook fired. sessionID=${input.sessionID || "none"}, system items before=${output.system.length}\n`);
      output.system.push("PROBE_MARKER_BINARY_YES_NO_12345");
      process.stderr.write(`[probe] Marker pushed. system items after=${output.system.length}\n`);
    },
  };
};
