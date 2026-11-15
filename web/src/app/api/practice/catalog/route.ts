import catalog from '@/features/guest/catalog.json';
// Build-time whitelist of published catalog labels; no questions, keys or user data.
export function GET(){return Response.json({items:catalog},{headers:{'Cache-Control':'public, max-age=300'}})}
