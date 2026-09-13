#!/usr/bin/env python3
"""Prepare the supplied, real-time recordings. Never modifies source videos."""
import argparse
import concurrent.futures as futures
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser()
parser.add_argument('--source-root', type=Path, required=True)
parser.add_argument('--work-dir', type=Path, required=True)
parser.add_argument('--site', type=Path, default=Path(__file__).resolve().parents[1])
args = parser.parse_args()
ffmpeg = shutil.which('ffmpeg')
ffprobe = shutil.which('ffprobe')
if not ffmpeg or not ffprobe:
    raise SystemExit('FFmpeg and ffprobe are required.')
videos = args.site / 'assets/videos'
posters = args.site / 'assets/posters'
for path in (videos, posters, args.work_dir):
    path.mkdir(parents=True, exist_ok=True)

def probe(path):
    return json.loads(subprocess.check_output([ffprobe, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))

def run(params):
    subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', *map(str, params)], check=True)

def encode(source, target, crf='22', maxrate='6M'):
    limit = float(maxrate[:-1]) * 1_000_000
    if not target.exists() or float(probe(target)['format']['bit_rate']) > limit * 1.08:
        run(['-threads', '2', '-i', source, '-map', '0:v:0', '-an', '-vf',
             'scale=1920:1080:flags=lanczos,setsar=1,fps=30,format=yuv420p',
             '-c:v', 'libx264', '-preset', 'fast', '-crf', crf, '-maxrate', maxrate,
             '-bufsize', str(int(limit * 2)), '-threads', '4',
             '-movflags', '+faststart', '-map_metadata', '-1', '-map_chapters', '-1', target])
    print('READY ' + target.name, flush=True)

def poster(source, slug):
    duration = float(probe(source)['format']['duration'])
    run(['-ss', min(3, duration / 3), '-i', source, '-frames:v', '1',
         '-vf', 'scale=1280:-2', '-q:v', '3', posters / (slug + '.jpg')])

gaits = ['trot', 'pace', 'canter', 'pronk']
main_sources = [args.source_root / '全向步态展示' / ('outdoor_' + gait + '.mov') for gait in gaits]
supplementary = [
    ('indoor-four-gaits', '前进步态展示（截图用）_1', 'indoor_front.mov', 'Indoor · four gaits'),
    ('asphalt-four-gaits', '前进步态展示（截图用）_1', '柏油路4步态.mov', 'Asphalt · four gaits'),
    ('stone-trot-pace-canter', '前进步态展示（截图用）_1', 'stone_trot_pace+back_canter.mov', 'Stone paving · Trot, Pace & backward Canter'),
    ('stone-canter', '前进步态展示（截图用）_1', 'stone_canter.mov', 'Stone paving · Canter'),
    ('pronk-1', '前进步态展示（截图用）_1', 'front_pronk.mov', 'Forward Pronk · sequence 1'),
    ('backward-pace-forward-canter', '前进步态展示（截图用）_2', 'back_pace2_front_canter.mov', 'Backward Pace → forward Canter'),
    ('forward-pace', '前进步态展示（截图用）_2', 'front_pace.mov', 'Forward Pace'),
    ('pronk-2', '前进步态展示（截图用）_2', 'front_pronk.mov', 'Forward Pronk · sequence 2'),
]
all_sources = main_sources + [args.source_root / folder / name for _, folder, name, _ in supplementary]
for source in all_sources:
    if not source.is_file():
        raise SystemExit('Missing source: ' + str(source))

def extra(item):
    slug, folder, name, _ = item
    target = videos / (slug + '.mp4')
    encode(args.source_root / folder / name, target)
    poster(target, slug)

with futures.ThreadPoolExecutor(max_workers=2) as pool:
    tasks = [pool.submit(encode, source, args.work_dir / (gait + '.mp4'), '19', '16M')
             for gait, source in zip(gaits, main_sources)]
    for task in tasks:
        task.result()
    extra_tasks = [pool.submit(extra, item) for item in supplementary]

    # A simple text-only transparent overlay; no changes to the recorded scenes.
    overlay = Image.new('RGBA', (3840, 2160), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font_path = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
    if not Path(font_path).exists():
        font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    font = ImageFont.truetype(font_path, 62)
    for i, gait in enumerate(gaits):
        x, y = 48 + 1920 * (i % 2), 42 + 1080 * (i // 2)
        width = int(draw.textlength(gait.title(), font=font)) + 64
        draw.rounded_rectangle((x, y, x + width, y + 104), radius=16, fill=(15, 24, 24, 205))
        draw.text((x + 32, y + 18), gait.title(), font=font, fill='white')
    draw.rectangle((1917, 0, 1923, 2160), fill=(255, 255, 255, 245))
    draw.rectangle((0, 1077, 3840, 1083), fill=(255, 255, 255, 245))
    labels = args.work_dir / 'gait-labels.png'
    overlay.save(labels)
    duration = max(float(probe(args.work_dir / (gait + '.mp4'))['format']['duration']) for gait in gaits)
    inputs = []
    for gait in gaits:
        inputs += ['-threads', '1', '-i', args.work_dir / (gait + '.mp4')]
    inputs += ['-i', labels]
    filters = []
    for i in range(4):
        filters.append(f'[{i}:v]setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={duration}[p{i}]')
    filters += ['[p0][p1][p2][p3]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0[grid]',
                '[grid][4:v]overlay=0:0,format=yuv420p[out]']
    master = videos / 'main-demo-4k.mp4'
    if not master.exists() or float(probe(master)['format']['bit_rate']) > 19_000_000:
        run([*inputs, '-filter_complex_threads', '2', '-filter_complex', ';'.join(filters),
             '-map', '[out]', '-an', '-t', duration, '-r', '30', '-c:v', 'libx264',
             '-preset', 'fast', '-crf', '22', '-maxrate', '18M', '-bufsize', '36M',
             '-threads', '6', '-movflags', '+faststart',
             '-map_metadata', '-1', master])
    print('READY main-demo-4k.mp4', flush=True)
    encode(master, videos / 'main-demo.mp4', '22', '8M')
    poster(master, 'main-demo')
    for task in extra_tasks:
        task.result()

metadata = {
    'playback_speed': '1x', 'audio': 'omitted in web exports',
    'main_demo': {'layout': [['Trot', 'Pace'], ['Canter', 'Pronk']],
                  'shorter_clips': 'hold final frame', 'duration_seconds': duration},
    'sources': [], 'exports': []
}
for source in all_sources:
    data = probe(source)
    metadata['sources'].append({'file': str(source.relative_to(args.source_root)),
        'duration': float(data['format']['duration']),
        'sha256': hashlib.file_digest(source.open('rb'), 'sha256').hexdigest()})
for path in sorted(videos.glob('*.mp4')):
    data = probe(path)
    stream = next(s for s in data['streams'] if s['codec_type'] == 'video')
    assert stream['codec_name'] == 'h264'
    assert int(data['format']['size']) < 95 * 1024 * 1024, path.name + ' is too large for GitHub'
    metadata['exports'].append({'file': path.name, 'width': stream['width'], 'height': stream['height'],
        'duration': float(data['format']['duration']), 'size_bytes': path.stat().st_size,
        'sha256': hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()})
(args.site / 'media-manifest.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
print('COMPLETE: all 12 source recordings processed; main demo + 8 supplementary demos.', flush=True)
