// These two constants can be re-written using target.js while building the app.
// If you change how these are formatted please update the target.js script accordingly.
const BASE_URL = 'https://www.xbox.com/';
const PREVIEW_BASE_URL = 'https://play.xbox.com/';
const PREVIEW_OVERRIDE = false;

// Not using the constants defiend above since those can change to target different endpoints.
const ALLOWED_REDIRECT_ORIGINS = new Set([
  new URL('https://www.xbox.com/').origin,
  new URL('https://play.xbox.com/').origin,
]);

const joinParams = (params) => {
    if (params.length === 0) {
        return "";
    }

    const cleaned = params.map(p => p.replace(/^[?&]+/, ''));
    return `?${cleaned.join('&')}`;
}

const getBaysideRedirectPath = (redirectUrlValue) => {
  if (redirectUrlValue.startsWith('/play/games/')) {
    return `/products/${redirectUrlValue.slice('/play/games/'.length)}`;
  }

  if (redirectUrlValue.startsWith('/play/')) {
    return redirectUrlValue.replace('/play/', '/');
  }

  return redirectUrlValue;
};

const normalizeRedirectToInternalPath = (redirectValue) => {
  if (!redirectValue) {
    return '/';
  }

  const trimmedRedirectValue = redirectValue.trim();
  if (!trimmedRedirectValue) {
    return '/';
  }

  if (trimmedRedirectValue.startsWith('/')) {
    return trimmedRedirectValue.startsWith('//') ? '/' : trimmedRedirectValue;
  }

  try {
    const parsedRedirectUrl = new URL(trimmedRedirectValue);
    const isHttpProtocol = parsedRedirectUrl.protocol === 'http:' || parsedRedirectUrl.protocol === 'https:';
    if (!isHttpProtocol || !ALLOWED_REDIRECT_ORIGINS.has(parsedRedirectUrl.origin)) {
      return '/';
    }

    const normalizedPath = `${parsedRedirectUrl.pathname}${parsedRedirectUrl.search}${parsedRedirectUrl.hash}`;
    if (!normalizedPath.startsWith('/') || normalizedPath.startsWith('//')) {
      return '/';
    }

    return normalizedPath;
  } catch (err) {
    return '/';
  }
};

const translateBaysideLaunchParams = (launchParamsString) => {
  if (!launchParamsString) {
    return '';
  }

  const params = new URLSearchParams(launchParamsString);
  if (params.has('redirectUri')) {
    return launchParamsString;
  }

  const redirectUrl = params.get('redirectUrl');
  if (!redirectUrl) {
    // Preserve query-only deeplinks by converting them to a Bayside home redirect.
    const queryOnlyRedirect = `?${params.toString()}`;
    const translatedParams = new URLSearchParams();
    translatedParams.set('redirectUri', queryOnlyRedirect);
    return translatedParams.toString();
  }

  let decodedRedirectUrl = redirectUrl;
  try {
    decodedRedirectUrl = decodeURIComponent(redirectUrl);
  } catch (err) {
    console.warn(`Failed to decode redirectUrl: ${redirectUrl}`);
  }

  const normalizedRedirectUrl = normalizeRedirectToInternalPath(decodedRedirectUrl);
  if (normalizedRedirectUrl === '/' && decodedRedirectUrl.trim() !== '/') {
    console.warn(`Invalid redirectUrl: ${decodedRedirectUrl}`);
  }

  const redirectUri = getBaysideRedirectPath(normalizedRedirectUrl);
  params.delete('redirectUrl');
  params.set('redirectUri', redirectUri);

  return params.toString();
};

const getLaunchUrlEdgewater = async (redirect, locale) => {
    const params = [];
    if (redirect) {
        params.push(redirect);
    }

    const url = `${BASE_URL}${locale}play${joinParams(params)}`;
    console.log(`Launching with ${url}`);

    return url;
};

const getLaunchUrlBayside = async (redirect) => {
    const params = [];
  const translatedLaunchParams = translateBaysideLaunchParams(redirect);
  if (translatedLaunchParams) {
    params.push(translatedLaunchParams);
    }

    const url = `${PREVIEW_BASE_URL}_external/init${joinParams(params)}`;
    console.log(`Launching with ${url}`);

    return url;
};

const getLaunchUrl = async (redirect, locale, shouldLaunchPreviewUX) => {
    if (PREVIEW_OVERRIDE || shouldLaunchPreviewUX) {
        return getLaunchUrlBayside(redirect);
    } else {
        return getLaunchUrlEdgewater(redirect, locale);
    }
};

async function navigateToApp(locale, shouldLaunchPreviewUX = false) {
  // Maintain queryParams from the previous URL
  // This lets us carry forward a redirectUrl for deeplinking from the initial view spawn
  // No need to encode the query params here, since they are encoded when they're first appended
  const launchParamsString = window.location.search.startsWith('?')
    ? window.location.search.slice(1)
    : window.location.search;

  const localeString = locale ?? '';
  const targetUrl = await getLaunchUrl(launchParamsString, localeString, shouldLaunchPreviewUX);

  console.log(`Navigating to ${targetUrl}`);
  window.location.replace(targetUrl);
}

// Combination of XboxCom supported locales and cloud gaming supported markets, see:
// - https://microsoft.visualstudio.com/Xbox/_git/Xbox.JS?path=/packages/xbox-web-partner-edgewater/src/auth/sagas/validateMarketSupport.ts
// - https://microsoft.visualstudio.com/Xbox/_git/Xbox.Xbet.Xboxcom?path=/packages/platform/xbox-foundation/src/configs/localeConfig.ts
const supportedLocales = {
  ["cs-cz"]: "cs-CZ",
  ["da-dk"]: "da-DK",
  ["de-at"]: "de-AT",
  ["de-ch"]: "de-CH",
  ["de-de"]: "de-DE",
  ["en-au"]: "en-AU",
  ["en-ca"]: "en-CA",
  ["en-gb"]: "en-GB",
  ["en-ie"]: "en-IE",
  ["en-nz"]: "en-NZ",
  ["en-us"]: "en-US",
  ["es-ar"]: "es-AR",
  ["es-es"]: "es-ES",
  ["es-mx"]: "es-MX",
  ["fi-fi"]: "fi-FI",
  ["fr-be"]: "fr-BE",
  ["fr-ca"]: "fr-CA",
  ["fr-ch"]: "fr-CH",
  ["fr-fr"]: "fr-FR",
  ["hu-hu"]: "hu-HU",
  ["it-it"]: "it-IT",
  ["ja-jp"]: "ja-JP",
  ["ko-kr"]: "ko-KR",
  ["nb-no"]: "nb-NO",
  ["nl-be"]: "nl-BE",
  ["nl-nl"]: "nl-NL",
  ["pl-pl"]: "pl-PL",
  ["pt-br"]: "pt-BR",
  ["pt-pt"]: "pt-PT",
  ["sk-sk"]: "sk-SK",
  ["sv-se"]: "sv-SE",
};

const fallbackLocales = {
  ["es-us"]: "es-MX",
}

const getSupportedLocale = (localeKey) => {
  const supportedLocale = supportedLocales[localeKey];
  if (supportedLocale) {
    return `${supportedLocale}/`;
  } else {
    // Android offers a number of locales which are adjacent to our supported locales, but not exact matches.
    // For these, we can provide a fallback locale to use instead.
    const fallbackLocale = fallbackLocales[localeKey];
    if (fallbackLocale) {
      return `${fallbackLocale}/`;
    }
  }
  return '';
};

const getWindowLocale = () => {
  if (window.Locale?.language && window.Locale?.region) {
    const localeKey = `${window.Locale.language.toLowerCase()}-${window.Locale.region.toLowerCase()}`;
    return getSupportedLocale(localeKey);
  }
  return undefined;
}

const getSavedLocale = () => new Promise((resolve, reject) => {
  if (window.storedLocalePlugin) {
    window.storedLocalePlugin.getLocale(
      res => resolve(getSupportedLocale(res)),
      err => reject(err)
    );
  } else {
    reject(new Error('storedLocalePlugin not available'));
  }
});

const getShouldLaunchPreviewUX = () => new Promise((resolve, reject) => {
  if (window.sharedPreferencesPlugin) {
    window.sharedPreferencesPlugin?.getNativeVariable(
      'previewUX',
      res => resolve(res.value === 'true'),
      err => reject(err)
    );
  } else {
    reject(new Error('sharedPreferencesPlugin not available'));
  }
}
);

var app = {
  initialize: function () {
    document.addEventListener(
      "deviceready",
      this.onDeviceReady.bind(this),
      false
    );
  },
  // deviceready Event Handler
  //
  // Bind any cordova events here. Common events are:
  // 'pause', 'resume', etc.
  onDeviceReady: function () {
    var Sentry = cordova.require("sentry-cordova.Sentry");
    Sentry.init({ dsn: 'https://027090efcf7b9d8daaefcf9a54064301@o427368.ingest.us.sentry.io/4507064110350336', release: '3.2.1' });
    this.receivedEvent("deviceready");
  },
  // Update DOM on a Received Event
  receivedEvent: function (id) {
    Promise.allSettled([
      getSavedLocale(),
      getShouldLaunchPreviewUX(),
    ]).then(([localeResult, previewUXResult]) => {
      const locale = localeResult.status === 'fulfilled' ? localeResult.value : getWindowLocale();
      const shouldLaunchPreviewUX = previewUXResult.status === 'fulfilled' ? previewUXResult.value : false;

      navigateToApp(locale, shouldLaunchPreviewUX);
    });
  },
};
app.initialize();
