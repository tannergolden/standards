// --- Shared Commitlint Configuration ---
//
// Purpose: defines the rules for `commitlint`, which enforces the Conventional
// Commits specification. Holding to it keeps history clean, readable, and
// structured, which is what makes automated changelog generation and version
// inference possible at all.
//
// The rules encoded here are the executable form of the commit standard in
// `docs/distribution/AI-Driven-Commit-Process.md`. The two change together:
// editing one without the other produces a rule nobody enforces, or a gate
// nothing documents.
//
// ---

export default {
  // `extends` inherits the base rules from the widely-used `config-conventional` preset.
  extends: ['@commitlint/config-conventional'],
  // House plugin: the em dash (U+2014) is banned in every commit message.
  // The character is built from its code point so this config file never
  // contains a banned sequence itself.
  plugins: [
    {
      rules: {
        'no-em-dash': ({ header, body, footer }) => {
          const emDash = String.fromCharCode(0x2014);
          const tainted = [header, body, footer].some(
            (part) => typeof part === 'string' && part.includes(emDash)
          );
          return [
            !tainted,
            'commit message contains an em dash (U+2014); use a comma, a colon, parentheses, or a spaced hyphen instead',
          ];
        },
      },
    },
  ],
  // The `rules` object is where we can override or add to the base configuration.
  // Each rule is defined as `[level, applicable, value]`:
  // - `level` (0=disable, 1=warn, 2=error): Determines if a violation fails the check.
  // - `applicable` ('always' or 'never'): Specifies when the rule applies.
  // - `value`: The actual parameter for the rule.
  rules: {
    // This rule specifies the *only* allowed commit types.
    'type-enum': [
      2, // Level: Error
      'always', // Applicable: Always
      [
        // Value: List of allowed types
        'feat',
        'fix',
        'docs',
        'style',
        'refactor',
        'perf',
        'test',
        'build',
        'ci',
        'chore',
        'revert',
        'security',
      ],
    ],

    // This rule enforces that the subject is *not* in any of the specified cases.
    // We strictly ban UPPER-CASE (all caps), but allow sentence-case or PascalCase.
    'subject-case': [
      1, // Level: Warn
      'never', // Applicable: Never
      // Value: Disallowed cases
      ['upper-case'],
    ],
    // Ensures the subject line is never empty.
    'subject-empty': [2, 'never'],
    // Ensures the subject line does not end with a period.
    'subject-full-stop': [1, 'never', '.'],
    // Enforces that the `type` (e.g., "feat", "fix") is always in lower-case.
    'type-case': [1, 'always', 'lower-case'],
    // Ensures the `type` is never empty.
    'type-empty': [2, 'never'],
    // House rule: no em dashes anywhere in the message (see plugin above).
    'no-em-dash': [2, 'always'],
  },
};
