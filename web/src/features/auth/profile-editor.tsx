'use client';

import Image from 'next/image';
import {createPortal} from 'react-dom';
import {useEffect, useRef, useState} from 'react';
import Cropper, {type Area} from 'react-easy-crop';
import {avatarRequest, practiceApi, type Profile} from '@/features/practice/history/api';
import {cropAvatar, loadAvatar} from './avatar-crop';
import s from './profile-editor.module.css';

interface Props {
  uid: string;
  profile: Profile;
  avatar: string | null;
  initials: string;
  onClose: () => void;
  onProfileSaved: (profile: Profile) => void;
  onAvatarSaved: (blob: Blob | null) => void;
  onComplete: () => void;
}
type Photo = {blob: Blob; url: string} | 'remove' | null;

export function ProfileEditor({uid, profile, avatar, initials, onClose, onProfileSaved, onAvatarSaved, onComplete}: Props) {
  const dialog = useRef<HTMLDialogElement>(null), input = useRef<HTMLInputElement>(null), changePhoto = useRef<HTMLButtonElement>(null);
  const [name, setName] = useState(profile.display_name ?? '');
  const [band, setBand] = useState(profile.target_ielts_band?.toString() ?? '');
  const [photo, setPhoto] = useState<Photo>(null);
  const [source, setSource] = useState<Awaited<ReturnType<typeof loadAvatar>> | null>(null);
  const [crop, setCrop] = useState({x: 0, y: 0}), [zoom, setZoom] = useState(1);
  const area = useRef<Area | null>(null);
  const [busy, setBusy] = useState(false), [loading, setLoading] = useState(false), [error, setError] = useState('');
  const lock = useRef(false), selection = useRef({generation: 0}), saved = useRef(profile);
  const cropTitle = useRef<HTMLHeadingElement>(null);
  const preview = photo === 'remove' ? null : photo?.url ?? avatar;

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    const pending = selection.current;
    document.body.style.overflow = 'hidden';
    dialog.current?.showModal();
    return () => {
      pending.generation++;
      document.body.style.overflow = overflow;
      previous?.focus();
    };
  }, []);
  useEffect(() => () => {if (source) URL.revokeObjectURL(source.url);}, [source]);
  useEffect(() => () => {if (photo && photo !== 'remove') URL.revokeObjectURL(photo.url);}, [photo]);
  useEffect(() => {if (source) cropTitle.current?.focus();}, [source]);

  function leaveCrop() {
    setSource(null); area.current = null; setError('');
    requestAnimationFrame(() => changePhoto.current?.focus());
  }
  function close() {
    if (lock.current) return;
    if (source) leaveCrop(); else onClose();
  }
  async function choose(file?: File) {
    if (!file) return;
    const current = ++selection.current.generation;
    setLoading(true); setError('');
    try {
      const next = await loadAvatar(file);
      if (selection.current.generation !== current) {URL.revokeObjectURL(next.url); return;}
      area.current = null; setCrop({x: 0, y: 0}); setZoom(1); setSource(next);
    } catch (e) {
      if (selection.current.generation === current) setError(e instanceof Error ? e.message : 'Could not open this photo.');
    } finally {if (selection.current.generation === current) setLoading(false);}
  }
  async function apply() {
    if (!source || !area.current || lock.current) return;
    lock.current = true; setBusy(true); setError('');
    try {
      const blob = await cropAvatar(source.image, area.current);
      setPhoto({blob, url: URL.createObjectURL(blob)}); leaveCrop();
    } catch (e) {setError(e instanceof Error ? e.message : 'Could not prepare your photo. Try again.');}
    finally {lock.current = false; setBusy(false);}
  }
  async function save() {
    if (lock.current || loading) return;
    if (!name.trim()) {setError('Enter your name.'); return;}
    lock.current = true; setBusy(true); setError('');
    let detailsSaved = false;
    try {
      const target = band ? Number(band) : null;
      if (name.trim() !== saved.current.display_name || target !== saved.current.target_ielts_band) {
        const updated = await practiceApi(uid)('/me', undefined, {method: 'PATCH', body: {display_name: name.trim(), target_ielts_band: target}}) as Profile;
        saved.current = updated; onProfileSaved(updated); detailsSaved = true;
      }
      if (photo) {
        await avatarRequest(uid, photo === 'remove' ? 'DELETE' : 'PUT', photo === 'remove' ? undefined : photo.blob);
        onAvatarSaved(photo === 'remove' ? null : photo.blob);
      }
      onComplete();
    } catch {
      setError(detailsSaved ? 'Your details were saved, but your photo could not be saved. Please try again.' : 'Could not save your changes. Your edits are still here — please try again.');
    } finally {lock.current = false; setBusy(false);}
  }

  return createPortal(<dialog ref={dialog} className={s.dialog} aria-labelledby="profile-editor-title" aria-describedby="profile-editor-description" onCancel={e => {e.preventDefault(); close();}}
    onKeyDown={e => {
      if (e.key !== 'Tab') return;
      const focusable = Array.from(e.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled):not([hidden]), select:not(:disabled), [tabindex="0"]')).filter(node => node.getClientRects().length > 0);
      if (!focusable.length) {e.preventDefault(); return;}
      const index = focusable.indexOf(document.activeElement as HTMLElement);
      const next = e.shiftKey ? (index <= 0 ? focusable.length - 1 : index - 1) : (index + 1) % focusable.length;
      e.preventDefault(); focusable[next]?.focus();
    }}>
    <form className={s.editor} onSubmit={e => {e.preventDefault(); if (!source) void save();}} aria-busy={busy}>
      <header className={s.header}>
        <div><h2 id="profile-editor-title" ref={cropTitle} tabIndex={-1}>{source ? 'Crop your photo' : 'Edit profile'}</h2>
          <p id="profile-editor-description">{source ? 'Drag your photo to find the perfect frame.' : 'A few details to make Alua feel like you.'}</p></div>
        <button type="button" className={s.close} onClick={close} disabled={busy} aria-label={source ? 'Back to edit profile' : 'Close edit profile'}>×</button>
      </header>
      <div className={s.body}>
        {source ? <>
          <div className={s.cropStage}>
            <Cropper image={source.url} crop={crop} zoom={zoom} aspect={1} cropShape="round" showGrid={false}
              onCropChange={setCrop} onZoomChange={setZoom} onCropComplete={(_, pixels) => {area.current = pixels;}}
              minZoom={1} maxZoom={3} zoomSpeed={.5} keyboardStep={5}
              cropperProps={{'aria-label': 'Position photo. Drag or use arrow keys to move.', 'aria-describedby': 'crop-help'}}
              mediaProps={{alt: 'Photo to crop'}}
              style={{cropAreaStyle: {border: '2px solid #fff', boxShadow: '0 0 0 9999px rgba(12, 28, 21, .58)'}}}/>
          </div>
          <div className={s.zoom}><label htmlFor="avatar-zoom">Zoom</label><input id="avatar-zoom" type="range" min="1" max="3" step="0.01" value={zoom} onChange={e => setZoom(Number(e.target.value))} disabled={busy}/><button type="button" className={s.textButton} disabled={busy} onClick={() => {setCrop({x: 0, y: 0}); setZoom(1);}}>Reset</button></div>
          <p className={s.hint} id="crop-help">Drag to move · Pinch or scroll to zoom. Arrow keys also move your photo.</p>
        </> : <>
          <section className={s.photoSection} aria-labelledby="profile-photo-title">
            <h3 id="profile-photo-title">Profile photo</h3>
            <div className={s.photoRow}><div className={s.avatar}>{preview ? <Image src={preview} alt="Profile photo preview" width={80} height={80} unoptimized/> : <span aria-label="Initials avatar">{initials}</span>}</div>
              <div className={s.photoActions}><div className={s.photoButtons}>
                <button type="button" ref={changePhoto} className={s.secondary} disabled={busy || loading} onClick={() => input.current?.click()}>{loading ? 'Opening photo…' : 'Change photo'}</button>
                {preview && <button type="button" className={s.textButton} disabled={busy || loading} onClick={() => {setPhoto('remove'); setError('');}}>Remove photo</button>}
              </div><p className={s.hint}>JPG, PNG or WebP · Up to 2 MB</p></div>
            </div>
            <input ref={input} hidden type="file" accept="image/jpeg,image/png,image/webp" aria-label="Choose photo" onChange={e => {void choose(e.target.files?.[0]); e.target.value = '';}}/>
          </section>
          <section className={s.details} aria-labelledby="profile-details-title"><h3 id="profile-details-title">Personal details</h3>
            <label htmlFor="profile-name">Name<input id="profile-name" autoComplete="name" value={name} required maxLength={80} disabled={busy} onChange={e => setName(e.target.value)}/></label>
            <div className={s.field}><label htmlFor="profile-band">Target IELTS Band</label><select id="profile-band" value={band} disabled={busy} onChange={e => setBand(e.target.value)}>
              <option value="">Not set</option>{Array.from({length: 11}, (_, i) => 4 + i * .5).map(value => <option key={value} value={value}>{value.toFixed(1)}</option>)}
              {band && (Number(band) * 2) % 1 !== 0 && <option value={band}>{band}</option>}
            </select></div>
          </section>
        </>}
        {error && <p className={s.error} role="alert">{error}</p>}
      </div>
      <footer className={s.footer}>
        <button type="button" className={s.secondary} disabled={busy} onClick={close}>Cancel</button>
        {source ? <button type="button" className={s.primary} disabled={busy} onClick={() => void apply()}>{busy ? 'Preparing…' : 'Apply photo'}</button>
          : <button type="submit" className={s.primary} disabled={busy || loading}>{busy ? 'Saving…' : 'Save changes'}</button>}
      </footer>
    </form>
  </dialog>, document.body);
}
