cordova.define('cordova/plugin_list', function(require, exports, module) {
  module.exports = [
    {
      "id": "cordova-plugin-device-code.deviceCode",
      "file": "plugins/cordova-plugin-device-code/www/deviceCode.js",
      "pluginId": "cordova-plugin-device-code",
      "clobbers": [
        "deviceCode"
      ]
    },
    {
      "id": "cordova-plugin-bluetooth-manager.bluetoothManagerPlugin",
      "file": "plugins/cordova-plugin-bluetooth-manager/www/bluetoothManagerPlugin.js",
      "pluginId": "cordova-plugin-bluetooth-manager",
      "clobbers": [
        "bluetoothManagerPlugin"
      ]
    },
    {
      "id": "sentry-cordova.Sentry",
      "file": "plugins/sentry-cordova/dist/js/sentry-cordova.bundle.js",
      "pluginId": "sentry-cordova",
      "clobbers": [
        "Sentry"
      ]
    },
    {
      "id": "com-darryncampbell-cordova-plugin-intent.IntentShim",
      "file": "plugins/com-darryncampbell-cordova-plugin-intent/www/IntentShim.js",
      "pluginId": "com-darryncampbell-cordova-plugin-intent",
      "clobbers": [
        "intentShim"
      ]
    },
    {
      "id": "cordova-plugin-wifi-status.wifiStatusPlugin",
      "file": "plugins/cordova-plugin-wifi-status/www/wifiStatusPlugin.js",
      "pluginId": "cordova-plugin-wifi-status",
      "clobbers": [
        "wifiStatusPlugin"
      ]
    },
    {
      "id": "cordova-plugin-shared-preferences.sharedPreferencesPlugin",
      "file": "plugins/cordova-plugin-shared-preferences/www/sharedPreferencesPlugin.js",
      "pluginId": "cordova-plugin-shared-preferences",
      "clobbers": [
        "sharedPreferencesPlugin"
      ]
    },
    {
      "id": "cordova-plugin-stored-locale.storedLocalePlugin",
      "file": "plugins/cordova-plugin-stored-locale/www/storedLocalePlugin.js",
      "pluginId": "cordova-plugin-stored-locale",
      "clobbers": [
        "storedLocalePlugin"
      ]
    },
    {
      "id": "cordova-plugin-locale.Locale",
      "file": "plugins/cordova-plugin-locale/www/locale.js",
      "pluginId": "cordova-plugin-locale",
      "clobbers": [
        "Locale"
      ]
    },
    {
      "id": "cordova-plugin-oss-notices.ossNoticesPlugin",
      "file": "plugins/cordova-plugin-oss-notices/www/ossNoticesPlugin.js",
      "pluginId": "cordova-plugin-oss-notices",
      "clobbers": [
        "ossNoticesPlugin"
      ]
    }
  ];
  module.exports.metadata = {
    "cordova-plugin-remote-injection": "0.5.2",
    "cordova-plugin-device-code": "1.0.0",
    "cordova-plugin-bluetooth-manager": "1.0.0",
    "sentry-cordova": "1.3.0",
    "com-darryncampbell-cordova-plugin-intent": "2.2.0",
    "cordova-plugin-wifi-status": "1.0.0",
    "cordova-plugin-shared-preferences": "1.0.0",
    "cordova-plugin-stored-locale": "1.0.0",
    "cordova-plugin-locale": "2.0.2",
    "cordova-plugin-oss-notices": "1.0.0"
  };
});