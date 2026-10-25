cordova.define("cordova-plugin-wifi-status.wifiStatusPlugin", function(require, exports, module) {
const exec = require("cordova/exec");

/**
 * Native API for checking wifi status info from web.
 * @constructor
 */
function WifiStatusPlugin() {}

// exec format: success, error, plugin name, action name, args[]
WifiStatusPlugin.prototype.getWifiStatus = function (
  successCallback,
  errorCallback
) {
  exec(successCallback, errorCallback, "WifiStatusPlugin", "getWifiStatus", []);
};

module.exports = new WifiStatusPlugin();

});
