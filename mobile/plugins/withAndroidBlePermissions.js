const { withAndroidManifest } = require("@expo/config-plugins");

const BLE_PERMISSIONS = [
  {
    "android:name": "android.permission.BLUETOOTH_SCAN",
    "android:usesPermissionFlags": "neverForLocation",
  },
  {
    "android:name": "android.permission.BLUETOOTH_CONNECT",
  },
  {
    "android:name": "android.permission.BLUETOOTH",
    "android:maxSdkVersion": "30",
  },
  {
    "android:name": "android.permission.BLUETOOTH_ADMIN",
    "android:maxSdkVersion": "30",
  },
  {
    "android:name": "android.permission.ACCESS_FINE_LOCATION",
    "android:maxSdkVersion": "30",
  },
];

const BLE_FEATURE = {
  "android:name": "android.hardware.bluetooth_le",
  "android:required": "true",
};

function ensureArray(target, key) {
  if (!Array.isArray(target[key])) {
    target[key] = [];
  }
  return target[key];
}

function upsertTag(list, attributes) {
  const existing = list.find((item) => item.$?.["android:name"] === attributes["android:name"]);
  if (existing) {
    existing.$ = { ...existing.$, ...attributes };
  } else {
    list.push({ $: { ...attributes } });
  }
}

module.exports = function withAndroidBlePermissions(config) {
  return withAndroidManifest(config, (config) => {
    const manifest = config.modResults;

    const permissions = ensureArray(manifest, "uses-permission");
    BLE_PERMISSIONS.forEach((permission) => upsertTag(permissions, permission));

    const features = ensureArray(manifest, "uses-feature");
    upsertTag(features, BLE_FEATURE);

    return config;
  });
};
