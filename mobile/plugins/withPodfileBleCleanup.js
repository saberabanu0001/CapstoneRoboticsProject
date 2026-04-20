const { withDangerousMod } = require("@expo/config-plugins");
const fs = require("fs");
const path = require("path");

const SNIPPET_SENTINEL = "# Remove stray macOS resource-fork Podspecs that break CocoaPods.";

const RUBY_CLEANUP_HELPER = [
  SNIPPET_SENTINEL,
  "def delete_stray_podspecs!",
  "  Dir.glob(File.join(__dir__, '..', 'node_modules', '**', '._*.podspec')).each do |file|",
  "    File.delete(file) if File.file?(file)",
  "  end",
  "end",
  "",
  "delete_stray_podspecs!",
  "",
  "pre_install do",
  "  delete_stray_podspecs!",
  "end",
  "",
].join("\n");

const LEGACY_BLOCK_PATTERNS = [
  /#\s*Exclude problematic podspec file[\s\S]*?^\s*end\s*$/m,
  /installer\.pods_project\.targets\.each[\s\S]*?^\s*end\s*$/m,
  /#\s*Remove stray macOS resource-fork Podspecs that break CocoaPods\.[\s\S]*?(^\s*pre_install[\s\S]*?^\s*end\s*$)?/m,
];

function injectCleanupSnippet(contents) {
  const cleaned = LEGACY_BLOCK_PATTERNS.reduce((acc, pattern) => acc.replace(pattern, ""), contents);

  if (contents.includes(SNIPPET_SENTINEL)) {
    return cleaned;
  }

  const snippet = `${RUBY_CLEANUP_HELPER}\n`;

  const platformRegex = /(platform\s*:ios[^\n]*\n)/;
  if (platformRegex.test(cleaned)) {
    return cleaned.replace(platformRegex, `$1\n${snippet}`);
  }

  return `${snippet}\n${cleaned}`;
}

module.exports = function withPodfileBleCleanup(config) {
  return withDangerousMod(config, ["ios", (config) => {
    const podfilePath = path.join(config.modRequest.platformProjectRoot, "Podfile");

    if (!fs.existsSync(podfilePath)) {
      return config;
    }

    const contents = fs.readFileSync(podfilePath, "utf8");
    fs.writeFileSync(podfilePath, injectCleanupSnippet(contents));

    return config;
  }]);
};
