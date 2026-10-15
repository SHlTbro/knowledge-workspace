'use strict';

(function publishSafeExternalUrl(root, factory) {
  const safeExternalUrl = factory();
  if (typeof module === 'object' && module.exports) module.exports = safeExternalUrl;
  if (root) root.KbSafeExternalUrl = safeExternalUrl;
})(typeof globalThis === 'undefined' ? this : globalThis, function createSafeExternalUrl() {
  return function safeExternalUrl(value) {
    try {
      const url = new URL(value);
      if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) return null;
      return url.href;
    } catch (_) {
      return null;
    }
  };
});
