module.exports = {
    types: [
      { types: ["feat", "feature", "added"], label: "🎉 New Features" },
      { types: ["fix", "bugfix", "fixed"], label: "🐛 Bugfixes" },
      { types: ["improvements", "enhancement"], label: "🔨 Improvements" },
      { types: ["perf"], label: "🏎️ Performance Improvements" },
      { types: ["build", "ci"], label: "🏗️ Build System" },
      { types: ["refactor", "refactoring"], label: "🪚 Refactoring" },
      { types: ["doc", "docs", "document"], label: "📚 Documentation Changes" },
      { types: ["test", "tests"], label: "🔍 Tests" },
      { types: ["style"], label: "💅 Code Style Changes" },
      { types: ["chore"], label: "🧹 Chores" },
      { types: ["other"], label: "Other Changes" },
    ],
  
    excludeTypes: ["other"],
  
    renderTypeSection: function (label, commits) {
      let text = `\n## ${label}\n`;
  
      commits.forEach((commit) => {
        text += `- ${commit.subject}\n`;
      });
  
      return text;
    },
  
    renderChangelog: function (release, changes) {
      const now = new Date();
      return `# ${release} - ${now.toISOString().substr(0, 10)}\n` + changes + "\n\n";
    },
  };