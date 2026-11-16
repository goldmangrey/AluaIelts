import type {Area} from 'react-easy-crop';

const MAX_BYTES = 2 * 1024 * 1024;

/** Validate the original, before decoding or uploading. Animated files are not avatars. */
export async function loadAvatar(file: File): Promise<{url: string; image: HTMLImageElement}> {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    throw new Error('Choose a JPG, PNG or WebP photo. Other formats are not supported.');
  }
  if (file.size > MAX_BYTES) throw new Error('This photo is too large. Choose a file up to 2 MB.');
  const bytes = new Uint8Array(await file.arrayBuffer());
  const view = new DataView(bytes.buffer);
  const tag = (offset: number) => String.fromCharCode(...bytes.slice(offset, offset + 4));
  const png = bytes[0] === 137 && tag(1) === 'PNG\r';
  const webp = tag(0) === 'RIFF' && tag(8) === 'WEBP';
  const jpeg = bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255;
  if (!(file.type === 'image/png' && png || file.type === 'image/webp' && webp || file.type === 'image/jpeg' && jpeg)) {
    throw new Error('This file is not a valid photo. Choose a JPG, PNG or WebP.');
  }
  for (let offset = png ? 8 : 12; (png || webp) && offset + 8 <= bytes.length;) {
    const type = tag(offset + (png ? 4 : 0));
    if (type === 'acTL' || type === 'ANIM') throw new Error('Choose a still photo. Animated images are not supported.');
    const size = view.getUint32(offset + (png ? 0 : 4), webp);
    offset += png ? size + 12 : size + 8 + size % 2;
  }
  const url = URL.createObjectURL(file);
  try {
    // Browser decoding applies EXIF orientation to both the cropper and canvas source.
    const image = new Image();
    image.src = url;
    await image.decode();
    const width = image.naturalWidth, height = image.naturalHeight;
    if (Math.min(width, height) < 32) throw new Error('This photo is too small. Choose an image at least 32 × 32 pixels.');
    if (Math.max(width, height) > 4096 || width * height > 16_000_000) {
      throw new Error('Choose a photo up to 4096 pixels per side and 16 megapixels.');
    }
    return {url, image};
  } catch (error) {
    URL.revokeObjectURL(url);
    if (error instanceof Error && error.message.startsWith('This photo') || error instanceof Error && error.message.startsWith('Choose a photo')) throw error;
    throw new Error('This photo could not be opened. Try another JPG, PNG or WebP.');
  }
}

/** The same pixel area shown by the cropper, exported at the backend's native size. */
export async function cropAvatar(image: HTMLImageElement, area: Area): Promise<Blob> {
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 256;
  const context = canvas.getContext('2d');
  if (!context) throw new Error('Could not prepare your photo. Please try again.');
  context.fillStyle = '#fff';
  context.fillRect(0, 0, 256, 256);
  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = 'high';
  context.drawImage(image, area.x, area.y, area.width, area.height, 0, 0, 256, 256);
  for (const quality of [.92, .85, .75]) {
    const blob = await new Promise<Blob | null>(resolve => canvas.toBlob(resolve, 'image/webp', quality));
    if (blob && blob.size <= 128 * 1024) return blob;
  }
  throw new Error('Could not prepare this photo within the size limit. Try another photo.');
}
