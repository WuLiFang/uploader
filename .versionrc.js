// https://github.com/conventional-changelog/conventional-changelog-config-spec/blob/master/versions/2.1.0/README.md#compareurlformat-string

const URL = "https://github.com/WuLiFang/uploader";

module.exports = {
  types: [
    { type: "feat", section: "Features" },
    { type: "fix", section: "Bug Fixes" },
    { type: "chore", hidden: true },
    { type: "docs", hidden: true },
    { type: "style", hidden: true },
    { type: "refactor", hidden: true },
    { type: "perf", section: "Performance" },
    { type: "test", hidden: true },
  ],
  commitUrlFormat: `${URL}/commit/{{hash}}`,
  compareUrlFormat: `${URL}/compare/{{previousTag}}...{{currentTag}}`,
  issueUrlFormat: `${URL}/issues/{{id}}`,
  userUrlFormat: `https://github.com//{{user}}`,
  bumpFiles: [
    {
      filename: "cgtwq_uploader/__version__.py",
      updater: "scripts/python-version-updater.js",
    },
    {
      filename: "VERSION",
      type: "plain-text",
    },
  ],
};
