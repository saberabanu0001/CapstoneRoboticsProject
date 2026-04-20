const { withProjectBuildGradle } = require("@expo/config-plugins");

const MIN_SDK_VERSION = 23;
const JITPACK_REPO = "maven { url 'https://www.jitpack.io' }";

function ensureMinSdkVersion(contents) {
  const fallbackRegex = /minSdkVersion\s*=\s*findProperty\(['"]expo\.minSdkVersion['"]\)\?\.toInteger\(\)\s*\?:\s*(\d+)/;

  if (fallbackRegex.test(contents)) {
    return contents.replace(fallbackRegex, (match, current) => {
      return parseInt(current, 10) >= MIN_SDK_VERSION
        ? match
        : match.replace(current, String(MIN_SDK_VERSION));
    });
  }

  const numericRegex = /(minSdkVersion\s*=\s*)(\d+)/;

  if (numericRegex.test(contents)) {
    return contents.replace(numericRegex, (match, prefix, current) => {
      return parseInt(current, 10) >= MIN_SDK_VERSION
        ? match
        : `${prefix}${MIN_SDK_VERSION}`;
    });
  }

  return contents;
}

function ensureJitpackRepository(contents) {
  if (contents.includes(JITPACK_REPO)) {
    return contents;
  }

  const repositoriesRegex = /(allprojects\s*{\s*repositories\s*{)/;
  if (repositoriesRegex.test(contents)) {
    return contents.replace(
      repositoriesRegex,
      `$1\n        ${JITPACK_REPO}`
    );
  }

  return contents;
}

module.exports = function withAndroidBuildGradleTweaks(config) {
  return withProjectBuildGradle(config, (config) => {
    if (typeof config.modResults.contents !== "string") {
      return config;
    }

    let contents = config.modResults.contents;
    contents = ensureMinSdkVersion(contents);
    contents = ensureJitpackRepository(contents);
    config.modResults.contents = contents;

    return config;
  });
};
