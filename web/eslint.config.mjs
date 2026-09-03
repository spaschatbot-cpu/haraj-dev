/**
 * ESLint، بالإعداد المسطّح مباشرةً.
 *
 * `eslint-config-next` 16 ships flat config, so it is imported and spread —
 * no `FlatCompat` shim. The shim exists to load old `.eslintrc` presets, and
 * pointing it at a config that is already flat produces a circular object it
 * cannot even format an error about.
 */
import next from "eslint-config-next";

const config = [
  ...next,
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      // Generated from the OpenAPI schema by `npm run schema`, and never
      // edited. Linting a generated file teaches nobody anything and produces
      // a diff the generator will undo.
      "lib/api/schema.ts",
    ],
  },
];

export default config;
