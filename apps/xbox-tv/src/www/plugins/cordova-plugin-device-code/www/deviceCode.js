cordova.define("cordova-plugin-device-code.deviceCode", function(require, exports, module) {
const argscheck = require('cordova/argscheck');
const exec = require('cordova/exec');

/**
 * Native API for getting MSA tokens via device code flow.
 * @constructor
 */
function DeviceCode () { }

/**
 * Gets a new device code by calling MSA /devicecode endpoint.
 * @param cv Optional CV to attach to the service calls.
 * @param msaCorrelationId Optional correlation ID to attach to the MSA service calls.
 * @param success Called on success with the contents of the `ServerDeviceCodeResponse`.
 * @param fail Called on error with the error description.
 */
DeviceCode.prototype.getDeviceCode = function (cv, msaCorrelationId, success, fail) {
    argscheck.checkArgs('SSfF', 'DeviceCode.getDeviceCode', arguments);
    exec(success, fail, 'DeviceCode', 'getDeviceCode', [cv, msaCorrelationId]);
};

/**
 * Uses the provided device code to call the MSA /token endpoint and check if authorization is complete
 * @param deviceCode Code obtained from calling `getDeviceCode`.
 * @param cv Optional CV to attach to the service calls.
 * @param msaCorrelationId Optional correlation ID to attach to the MSA service calls.
 * @param success Called on success with the contents of the `ServerAuthorizationTokenResponse`.
 * @param fail Called on error with the error description.
 */
DeviceCode.prototype.checkForToken = function (deviceCode, cv, msaCorrelationId, success, fail) {
    argscheck.checkArgs('sSSfF', 'DeviceCode.checkForToken', arguments);
    exec(success, fail, 'DeviceCode', 'checkForToken', [deviceCode, cv, msaCorrelationId]);
};

module.exports = new DeviceCode();

});
