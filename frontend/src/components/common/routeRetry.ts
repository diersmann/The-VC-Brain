/** A rejected lazy import needs a document reload because React.lazy caches it. */
export const retryRoute = () => window.location.reload();
