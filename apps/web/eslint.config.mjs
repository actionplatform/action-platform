import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: import.meta.dirname });

const config = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  { ignores: [".next/**", "node_modules/**", "lib/api.d.ts", "next-env.d.ts"] },
  {
    files: ["app/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": ["error", {
        patterns: [
          { group: ["@/features/*/*", "!@/features/*/actions"], message: "A page imports a feature through its index (@/features/<name>) or its actions." },
        ],
      }],
    },
  },
  {
    files: ["features/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": ["error", {
        patterns: [
          { group: ["@/app/*", "@/app/**"], message: "A feature never imports a page." },
          { group: ["@/features/*/*", "!@/features/*/actions"], message: "Another feature is reached through its index (@/features/<name>) or its actions." },
        ],
      }],
    },
  },
];

export default config;
