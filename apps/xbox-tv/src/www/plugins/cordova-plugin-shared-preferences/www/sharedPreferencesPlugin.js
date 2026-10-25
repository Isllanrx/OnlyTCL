cordova.define("cordova-plugin-shared-preferences.sharedPreferencesPlugin", function(require, exports, module) {
    const argscheck = require('cordova/argscheck');
    const exec = require('cordova/exec');
    
    /**
     * Native API for storing and fetching key/value pairs from the SharedPreferences cache.
     * @constructor
     */
    function SharedPreferencesPlugin () { }
    
    SharedPreferencesPlugin.prototype.getNativeVariable = function (key, success, fail) {
        argscheck.checkArgs('SFF', 'SharedPreferencesPlugin.getNativeVariable', arguments);
        exec(success, fail, 'SharedPreferencesPlugin', 'getNativeVariable', [key]);
    };

    SharedPreferencesPlugin.prototype.setNativeVariable = function (key, value, success, fail) {
        argscheck.checkArgs('SSFF', 'SharedPreferencesPlugin.setNativeVariable', arguments);
        exec(success, fail, 'SharedPreferencesPlugin', 'setNativeVariable', [key, value]);
    };
    
    module.exports = new SharedPreferencesPlugin();    
});
