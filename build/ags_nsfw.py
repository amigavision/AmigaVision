"""Generate the on-Amiga removal option from the built menu and database."""

from pathlib import Path

from ags_make import make_canonical_name
from ags_fs import convert_filename_uae2a
from ags_query import get_amiga_whd_dir, get_runscript_paths


def shell_quote(value):
    return '"' + value.replace('*', '**').replace('"', '*"') + '"'


def literal_pattern(value):
    # AmigaDOS pattern escaping is separate from Shell argument quoting.
    return ''.join("'" + c if c in "'?#()[]~|%" else c for c in value)


def make_nsfw_option(db, ags_path, collection):
    rows = [dict(row) for row in db.execute('SELECT * FROM titles')]
    tagged = {row['id']: row for row in rows
              if 'nsfw' in {tag.strip().lower() for tag in row['subcategory'].split(',')}}
    content_dirs = set()
    protected_dirs = set()
    run_paths = set()
    for row in rows:
        if not row.get('slave_path'):
            continue
        row['slave_dir'] = row['slave_path'].split('/')[0]
        directory = get_amiga_whd_dir(row)
        if directory:
            (content_dirs if row['id'] in tagged else protected_dirs).add(directory)
        if row['id'] in tagged:
            for folder in get_runscript_paths(row):
                if folder:
                    run_paths.add(folder + '/' + make_canonical_name(row))
    if {p.casefold() for p in content_dirs} & {p.casefold() for p in protected_dirs}:
        raise ValueError('NSFW removal would delete an installation shared with an untagged title')

    menu_paths = {path for path, entry_id in collection.image_entries.items() if entry_id in tagged}
    # Include entries with custom artwork, which are absent from image_entries.
    targets = {'execute "AGS:' + path + '"' for path in run_paths}
    for path in Path(ags_path).rglob('*.run'):
        relative = path.relative_to(ags_path)
        if relative.parts[0] in ('Run', 'RunQuiet') or relative.as_posix()[:-4] in collection.image_entries:
            continue
        if path.read_text(encoding='latin-1').strip() in targets:
            menu_paths.add(relative.as_posix()[:-4])

    lines = ['; Generated from titles.csv NSFW tags. Deletes installed files permanently.',
             'FailAt 21', 'Echo "Removing NSFW titles, be patient while we delete the files"']
    for root in ('SYS:AGS2/', 'SYS:AGS-HiRes/'):
        for path in sorted(menu_paths):
            base = literal_pattern(convert_filename_uae2a(root + path))
            pattern = base + '(.run|.txt|.iff|-QR.iff|-[1-9].iff)'
            lines.append('Delete >NIL: ' + shell_quote(pattern) + ' FORCE QUIET')
        for path in sorted(run_paths):
            lines.append('Delete >NIL: ' + shell_quote(literal_pattern(convert_filename_uae2a(root + path))) + ' FORCE QUIET')
        for folder in sorted({str(Path(path).parent) for path in menu_paths}):
            lines.append('Delete >NIL: ' + shell_quote(literal_pattern(convert_filename_uae2a(root + folder + '/.dir'))) + ' FORCE QUIET')
    for path in sorted(content_dirs):
        lines.append('Delete >NIL: ' + shell_quote(literal_pattern('WHD0:' + path)) + ' ALL FORCE QUIET')
    # Run cleanup after this script returns: AmigaDOS may lock an executing file.
    cleanup = ['; Remove the completed option after its executing script closes.', 'Wait 2']
    for root in ('SYS:AGS2/', 'SYS:AGS-HiRes/'):
        base = literal_pattern(root + '[ Options ].ags/Remove NSFW Titles')
        cleanup.append('Delete >NIL: ' + shell_quote(base + '(.run|.txt|.iff|-QR.iff|-[1-9].iff)') + ' FORCE QUIET')
        cleanup.append('Delete >NIL: ' + shell_quote(literal_pattern(root + '[ Options ].ags/.dir')) + ' FORCE QUIET')
    cleanup.insert(1, 'FailAt 21')
    Path(ags_path, 'RemoveNSFWCleanup').write_text('\n'.join(cleanup) + '\n', encoding='latin-1')
    lines += ['Echo "NSFW titles removed."', 'Wait 3',
              'Run >NIL: Execute "AGS:RemoveNSFWCleanup"']
    option = Path(ags_path) / '[ Options ].ags' / 'Remove NSFW Titles'
    option.parent.mkdir(parents=True, exist_ok=True)
    option.with_suffix('.run').write_text('\n'.join(lines) + '\n', encoding='latin-1')
    option.with_suffix('.txt').write_text(
        'Permanently delete NSFW titles.\n'
        'Removes installed content; saved games are retained.\n'
        'Note that this is permanent, re-download to restore.\n', encoding='latin-1')
    return menu_paths, content_dirs
