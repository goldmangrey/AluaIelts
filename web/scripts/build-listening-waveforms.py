"""Build read-only audio envelopes; originals and the backend manifest are never modified."""
import argparse
import concurrent.futures
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--audio-root', type=Path, default=Path.home() / 'Desktop/Listening')
args = parser.parse_args()
items = json.loads((ROOT / 'backend/app/content/listening_audio_v1/audio_manifest.json').read_text())['items']
output = ROOT / 'web/public/listening-waveforms/v1'
output.mkdir(parents=True, exist_ok=True)


def envelope(item):
    path = args.audio_root / item['relative_path']
    if not path.is_file() or path.stat().st_size != item['byte_size']:
        raise RuntimeError(f"Missing/mismatched source: {item['audio_id']}")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    duration = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(path)]))
    command = ['ffmpeg', '-v', 'error', '-err_detect', 'ignore_err', '-i', str(path), '-vn', '-ac', '1', '-af', 'aresample=8000,asetnsamples=n=512:p=0,astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-', '-f', 'null', '-']
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    levels = [0.0] * 2048
    counts = [0] * 2048
    time = None
    for line in result.stdout.splitlines():
        match = re.search(r'pts_time:([\d.]+)', line)
        if match:
            time = float(match[1]) + .032
        elif line.startswith('lavfi.astats.Overall.RMS_level=') and time is not None:
            db = float(line.split('=', 1)[1])
            energy = 10 ** (db / 10) if math.isfinite(db) else 0
            index = min(2047, max(0, int(time / duration * 2048)))
            levels[index] += energy
            counts[index] += 1
    if not sum(counts):
        raise RuntimeError(f"No decoded RMS: {item['audio_id']}")
    rms = [math.sqrt(level / max(1, count)) for level, count in zip(levels, counts)]
    ceiling = max(rms)
    peaks = [round(255 * math.sqrt(level / ceiling)) if ceiling else 0 for level in rms]
    return item, {'audio_id': item['audio_id'], 'source_sha256': sha, 'duration': round(duration, 6), 'peaks': peaks}

exams = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for item, data in pool.map(envelope, items):
        exams.setdefault(item['exam_id'], {})[str(item['part_number'])] = data
manifest = {'version': 1, 'algorithm': '2048 time-aligned bins; FFmpeg 8kHz mono, 64ms RMS; energy aggregation; sqrt dynamic-range compression; uint8', 'exams': {}}
for eid, parts in sorted(exams.items()):
    body = (json.dumps({'version': 1, 'exam_id': eid, 'parts': parts}, separators=(',', ':')) + '\n').encode()
    sha = hashlib.sha256(body).hexdigest()
    filename = f'{eid}-{sha[:16]}.json'
    (output / filename).write_bytes(body)
    manifest['exams'][eid] = {'url': '/listening-waveforms/v1/' + filename, 'sha256': sha}
(ROOT / 'web/src/features/listening/waveform-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'exams': len(exams), 'audio_tracks': len(items), 'bytes': sum(p.stat().st_size for p in output.glob('*.json'))}))
