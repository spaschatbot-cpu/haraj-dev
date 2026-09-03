import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["**/*.test.ts", "**/*.test.tsx"],
    server: {
      // The guards in `ops/checks` are plain node scripts with a shebang, run
      // by CI as executables. Vitest's transform does not expect one and fails
      // to parse the first line, so they are imported as-is — which is also the
      // point: the test must exercise the file CI runs, not a rewritten copy.
      deps: { external: [/ops[\/]checks[\/]/] },
    },
  },
  resolve: { alias: { "@": fileURLToPath(new URL(".", import.meta.url)) } },
});
