import { defineCloudflareConfig } from "@opennextjs/cloudflare";
import staticAssetsIncrementalCache from "@opennextjs/cloudflare/overrides/incremental-cache/static-assets-incremental-cache";

// Only public shells are prerendered. Private API fetches use no-store.
// There is no ISR or server data cache, so no R2/KV/D1/queue is needed.
export default defineCloudflareConfig({ incrementalCache: staticAssetsIncrementalCache });
