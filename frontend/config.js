/* Set this to the deployed Flask API origin, for example https://taka-dao-api.vercel.app. */
window.TAKA_DAO_API_BASE = window.TAKA_DAO_API_BASE || '';
(() => {
  const base = String(window.TAKA_DAO_API_BASE || '').replace(/\\/+$/, '');
  if (!base) return;
  const originalFetch = window.fetch.bind(window);
  window.fetch = (input, init) => {
    if (typeof input === 'string' && input.startsWith('/api/')) input = base + input;
    return originalFetch(input, init);
  };
})();
