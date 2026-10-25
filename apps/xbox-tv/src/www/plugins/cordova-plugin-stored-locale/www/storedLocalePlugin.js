cordova.define("cordova-plugin-stored-locale.storedLocalePlugin", function(require, exports, module) {
    const argscheck = require('cordova/argscheck');
    const exec = require('cordova/exec');
    
    /**
     * Native API for storing and fetching locale info.
     * @constructor
     */
    function StoredLocalePlugin () { }
    
    StoredLocalePlugin.prototype.getLocale = function (success, fail) {
        argscheck.checkArgs('FF', 'StoredLocalePlugin.getLocale', arguments);
        exec(success, fail, 'StoredLocalePlugin', 'getLocale', []);
    };

    StoredLocalePlugin.prototype.setLocale = function (locale, success, fail) {
        argscheck.checkArgs('SFF', 'StoredLocalePlugin.setLocale', arguments);
        exec(success, fail, 'StoredLocalePlugin', 'setLocale', [locale]);
    };
    
    module.exports = new StoredLocalePlugin();    
});
