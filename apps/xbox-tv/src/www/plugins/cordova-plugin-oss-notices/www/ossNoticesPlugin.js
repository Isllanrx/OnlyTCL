// Copyright (C) Microsoft Corporation. All rights reserved.

cordova.define("cordova-plugin-oss-notices.ossNoticesPlugin", function(require, exports, module) {
const argscheck = require('cordova/argscheck');
const exec = require('cordova/exec');

/**
 * Native API for retrieving the bundled third-party OSS notices.
 * @constructor
 */
function OssNoticesPlugin () { }

/**
 * Returns the native-side third-party notices for display in Bayside's
 * combined OSS-notices page.
 * @param success Called on success with the oss notices.
 * @param fail Called on error with the error description.
 */
OssNoticesPlugin.prototype.getOSSNotices = function (success, fail) {
    argscheck.checkArgs('FF', 'OssNoticesPlugin.getOSSNotices', arguments);
    exec(success, fail, 'OssNotices', 'getOSSNotices', []);
};

module.exports = new OssNoticesPlugin();

});
