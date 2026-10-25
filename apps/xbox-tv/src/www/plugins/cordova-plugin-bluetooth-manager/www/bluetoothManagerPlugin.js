cordova.define("cordova-plugin-bluetooth-manager.bluetoothManagerPlugin", function(require, exports, module) {
const argscheck = require('cordova/argscheck');
const exec = require('cordova/exec');

/**
 * Native API for managing bluetooth devices via web.
 * @constructor
 */
function BluetoothManagerPlugin () { }
/**
 * Starts the scan of Bluetooth devices.
 * @param classFilters Optional array of class filters to use in the results.
 * @param success Called on success.
 * @param fail Called on error.
 */
BluetoothManagerPlugin.prototype.scanDevices = function (classFilters, success, fail) {
    argscheck.checkArgs('AFF', 'BluetoothManagerPlugin.scanDevices', arguments);
    exec(success, fail, 'BluetoothManagerPlugin', 'scanDevices', [classFilters]);
};

/**
 * Stops the Bluetooth scan.
 * @param success Called on success.
 * @param fail Called on error.
 */
BluetoothManagerPlugin.prototype.stopScan = function (success, fail) {
    argscheck.checkArgs('FF', 'BluetoothManagerPlugin.stopScan', arguments);
    exec(success, fail, 'BluetoothManagerPlugin', 'stopScan', []);
};

/**
 * Starts the bond process for a bluetooth device using the passed MAC address.
 * @param macAddress MAC address of the device to bond.
 * @param success Called on success.
 * @param fail Called on error.
 */
BluetoothManagerPlugin.prototype.bondDevice = function (macAddress, success, fail) {
    argscheck.checkArgs('SFF', 'BluetoothManagerPlugin.bondDevice', arguments);
    exec(success, fail, 'BluetoothManagerPlugin', 'bondDevice', [macAddress]);
};

/**
 * Starts the unbond process for a bluetooth device using the passed MAC address.
 * @param macAddress MAC address of the device to unbond.
 * @param success Called on success.
 * @param fail Called on error.
 */
BluetoothManagerPlugin.prototype.unbondDevice = function (macAddress, success, fail) {
    argscheck.checkArgs('SFF', 'BluetoothManagerPlugin.unbondDevice', arguments);
    exec(success, fail, 'BluetoothManagerPlugin', 'unbondDevice', [macAddress]);
};

/**
 * Request location permissions to the user at runtime. Bluetooth on Android requires location access.
 * @param success Called on success.
 * @param fail Called on error.
 */
BluetoothManagerPlugin.prototype.requestLocationPermissions = function (success, fail) {
    argscheck.checkArgs('FF', 'BluetoothManagerPlugin.requestLocationPermissions', arguments);
    exec(success, fail, 'BluetoothManagerPlugin', 'requestLocationPermissions', []);
};

/**
 * Checks whether the app already has location permissions or not.
 * @param success Called on success.
 * @param fail Called on error.
 */
BluetoothManagerPlugin.prototype.hasLocationPermissions = function (success, fail) {
    argscheck.checkArgs('FF', 'BluetoothManagerPlugin.hasLocationPermissions', arguments);
    exec(success, fail, 'BluetoothManagerPlugin', 'hasLocationPermissions', []);
};

module.exports = new BluetoothManagerPlugin();

});
