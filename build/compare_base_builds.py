"""Prepare isolated HDF/native A/B builds; print the plan unless --run is given."""
import argparse
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import time
from av_base_tree import compare, directory_fingerprint, file_hash


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-hdf', type=Path, required=True)
    p.add_argument('--base-dir', type=Path, required=True)
    p.add_argument('--work-dir', type=Path, required=True, help='New, empty comparison directory')
    p.add_argument('--profile', choices=['test', 'full'], default='test', help='Small test configuration by default')
    p.add_argument('--run', action='store_true', help='Run both preparation builds and compare DH0/DH1')
    args = p.parse_args()
    image, source, work = (v.expanduser().resolve() for v in [args.base_hdf, args.base_dir, args.work_dir])
    if not image.is_file() or not source.is_dir():
        p.error('Both input sources must exist')
    if source == work or source in work.parents or work in source.parents:
        p.error('Comparison workspace must be separate from the native source')
    repo = Path(__file__).resolve().parent.parent
    commands = []
    for label, source_args in [('hdf', ['--base-hdf', str(image)]), ('native', ['--base-dir', str(source)])]:
        stage, output = work/label/'stage', work/label/'output'
        commands.append((label, ['make', 'prepare-image-temp',
                         'AGSTEMP='+str(stage), 'AGSDEST='+str(output),
                         'AGSCACHEGEN=base-compare-'+work.name,
                         'BASE_IMAGE_ARGS='+shlex.join(source_args+['--temp-dir',str(stage)])]))
        if args.profile == 'test':
            commands[-1][1].append('IMAGE_PREP_CMD='+shlex.join([
                'pipenv', 'run', 'build/ags_imager.py', '-c', str(work/'fixture/BaseCompare.yaml'),
                '-o', str(output), *source_args, '--temp-dir', str(stage)]))
    for label, cmd in commands:
        print(label+': '+shlex.join(cmd), flush=True)
    if not args.run:
        print('Plan only. Add --run to create both staged builds (no emulator is launched).')
        return 0
    if work.exists() and any(work.iterdir()):
        p.error('Comparison workspace must be empty; choose a new --work-dir')
    if args.profile == 'test':
        fixture = work/'fixture'
        fixture.mkdir(parents=True, exist_ok=True)
        # Use real title art; the legacy Test.yaml has synthetic categories without
        # the pre-rendered high-resolution artwork required by today's builder.
        (fixture/'BaseCompare.yaml').write_text(
            '- CannonFodder\n- Agony\n- IK+\n- EyeOfTheBeholder2\n'
            '- Andromeda-Rule30\n- Bacteria\n')
        for suffix in ['runscript', 'clonescript']:
            shutil.copy2(repo/'configs'/('AmigaVision.'+suffix), fixture/('BaseCompare.'+suffix))
        (fixture/'BaseCompare.layers.yaml').write_text(
            json.dumps([{str(repo/'configs/Layers/Base'): '/'}])+'\n')
    before = {'hdf': file_hash(image), 'native': directory_fingerprint(source)}
    elapsed = {}
    for label, cmd in commands:
        (work/label/'stage').mkdir(parents=True, exist_ok=True)
        (work/label/'output').mkdir(parents=True, exist_ok=True)
        start = time.monotonic()
        with (work/label/'build.log').open('w') as log:
            result = subprocess.run(cmd, cwd=repo, stdout=log, stderr=subprocess.STDOUT)
        elapsed[label] = time.monotonic()-start
        if result.returncode:
            print(f'{label} preparation failed; see {work/label/"build.log"}')
            return result.returncode
    report = {'profile': args.profile, 'preparation_seconds': elapsed,
              'source_unchanged': before == {'hdf': file_hash(image), 'native': directory_fingerprint(source)},
              'partitions': {}}
    for part in ['DH0','DH1']:
        report['partitions'][part] = compare(work/'hdf/stage'/part, work/'native/stage'/part)
    (work/'comparison.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    return int(not report['source_unchanged'] or any(any(d.values()) for d in report['partitions'].values()))

if __name__ == '__main__':
    raise SystemExit(main())
