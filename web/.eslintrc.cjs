module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  parser: "@typescript-eslint/parser",
  parserOptions: { ecmaVersion: "latest", sourceType: "module" },
  plugins: ["@typescript-eslint", "react-hooks"],
  extends: ["eslint:recommended", "plugin:@typescript-eslint/recommended", "plugin:react-hooks/recommended"],
  rules: {
    // UX-S05: colours come from ui/tokens.css only
    "no-restricted-syntax": [
      "error",
      { selector: "Literal[value=/#[0-9a-fA-F]{3,8}\b/]", message: "Use a design token (var(--color-…)) instead of a hex colour." },
    ],
  },
  ignorePatterns: ["dist", "node_modules"],
};
