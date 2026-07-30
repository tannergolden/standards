// --- Shared Commitlint Configuration ---
//
// Purpose: defines the rules for `commitlint`, which enforces the Conventional
// Commits specification. Holding to it keeps history clean, readable, and
// structured, which is what makes automated changelog generation and version
// inference possible at all.
//
// The rules encoded here are the executable form of the commit standard in
// `docs/distribution/Conventional-Commits.md`. The two change together:
// editing one without the other produces a rule nobody enforces, or a gate
// nothing documents.
//
// ---

export default {
  // `extends` inherits the base rules from the widely-used `config-conventional` preset.
  extends: ['@commitlint/config-conventional'],
  // House plugins. Both mirror `scripts/commit-check.py`, which is the gate
  // that actually blocks a merge; this file is what a contributor runs
  // locally, and the two are only useful if they agree. Every character is
  // built from its code point so this config never contains a banned
  // sequence itself.
  plugins: [
    {
      rules: {
        // U+2013 EN DASH through U+2015 HORIZONTAL BAR. The em dash is the
        // banned character; its neighbours go with it because none of the
        // three belongs in a commit message and a range is harder to get
        // wrong than a single code point. Same range as BANNED_DASHES in
        // commit-check.py, which used to reject an en dash that this config
        // accepted.
        'no-banned-dashes': ({ header, body, footer }) => {
          const banned = [0x2013, 0x2014, 0x2015].map((c) =>
            String.fromCharCode(c)
          );
          const tainted = [header, body, footer].some(
            (part) =>
              typeof part === 'string' &&
              banned.some((dash) => part.includes(dash))
          );
          return [
            !tainted,
            'commit message contains an em dash, en dash or horizontal bar (U+2013 to U+2015); use a comma, a colon, parentheses, or a spaced hyphen instead',
          ];
        },

        // The subject starts with a lowercase letter, optionally after one
        // emoji and a space. Written as a plugin rather than as
        // `subject-case`, because that rule's `sentence-case` detection has
        // no notion of a leading emoji, and the house style puts an emoji on
        // most subjects. This is the same test as commit-check.py: strip an
        // optional emoji prefix, then require a lowercase ASCII letter.
        'subject-lowercase': ({ subject }) => {
          if (typeof subject !== 'string' || subject.length === 0) {
            return [true, ''];
          }
          const stripped = subject.replace(
            /^(?:[\u{1F000}-\u{1FAFF}\u2190-\u21FF\u2300-\u27BF\u2900-\u2BFF]\uFE0F?)\s/u,
            ''
          );
          const first = stripped.charAt(0);
          return [
            first >= 'a' && first <= 'z',
            'the subject must start with a lowercase letter, optionally after an emoji and a space',
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

    // Case is enforced by the `subject-lowercase` plugin above, which
    // understands the leading emoji this house style uses. commitlint's own
    // `subject-case` does not, so it is disabled rather than left to warn
    // about something the plugin already decides.
    'subject-case': [0],
    // THE SCOPE IS REQUIRED, which the Conventional Commits specification
    // treats as optional. `docs: add the seed` repeated across a hundred
    // commits answers "where?" nowhere. commit-check.py has always required
    // it; without this rule a contributor's local run accepted what the
    // required check then rejected.
    'scope-empty': [2, 'never'],
    // Ensures the subject line is never empty.
    'subject-empty': [2, 'never'],
    // Ensures the subject line does not end with a period.
    'subject-full-stop': [1, 'never', '.'],
    // Enforces that the `type` (e.g., "feat", "fix") is always in lower-case.
    'type-case': [1, 'always', 'lower-case'],
    // Ensures the `type` is never empty.
    'type-empty': [2, 'never'],
    // House rules, both defined in the plugin above.
    'no-banned-dashes': [2, 'always'],
    'subject-lowercase': [2, 'always'],
  },
};
