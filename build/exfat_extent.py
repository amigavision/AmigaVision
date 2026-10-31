"""Read-only lookup of a contiguous file inside an MBR/exFAT disk image.

Unsupported/fragmented layouts are rejected so packaging can use ordinary xz.
Reference: https://learn.microsoft.com/windows/win32/fileio/exfat-specification
"""
import struct
from pathlib import Path


class UnsupportedLayout(ValueError):
    pass


def entry_checksum(data):
    value = 0
    for i, byte in enumerate(data):
        if i not in (2, 3):
            value = (((value & 1) << 15) | (value >> 1)) + byte
            value &= 0xffff
    return value


class Exfat:
    def __init__(self, file, start, length, image_size):
        self.file, self.start, self.length = file, start, length
        if start < 512 or start + length > image_size:
            raise UnsupportedLayout('Partition exceeds image bounds')
        boot = self.read(0, 512)
        if boot[3:11] != b'EXFAT   ' or boot[510:512] != b'\x55\xaa':
            raise UnsupportedLayout('Partition is not exFAT')
        sector_shift, cluster_shift, fats = boot[108:111]
        if not 9 <= sector_shift <= 12 or cluster_shift + sector_shift > 25 or fats not in (1, 2):
            raise UnsupportedLayout('Unsupported exFAT geometry')
        self.sector = 1 << sector_shift
        self.cluster_size = self.sector << cluster_shift
        volume_sectors = struct.unpack_from('<Q', boot, 72)[0]
        fat_offset, fat_length, heap, self.clusters, self.root = struct.unpack_from('<IIIII', boot, 80)
        self.heap = heap * self.sector
        active = struct.unpack_from('<H', boot, 106)[0] & 1
        fat_size = fat_length * self.sector
        if (active >= fats or volume_sectors * self.sector > length or self.clusters == 0 or
                fat_offset < 24 or fat_size > 64 * 1024**2 or
                fat_size < (self.clusters + 2) * 4 or
                (fat_offset + fat_length * fats) * self.sector > self.heap or
                self.heap + self.clusters * self.cluster_size > volume_sectors * self.sector):
            raise UnsupportedLayout('Invalid exFAT bounds')
        region = self.read(0, 12 * self.sector)
        checksum = 0
        for i, byte in enumerate(region[:11*self.sector]):
            if i not in (106, 107, 112):
                checksum = ((((checksum & 1) << 31) | (checksum >> 1)) + byte) & 0xffffffff
        if region[11*self.sector:] != struct.pack('<I', checksum) * (self.sector // 4):
            raise UnsupportedLayout('Invalid exFAT boot checksum')
        self.fat = self.read((fat_offset + active * fat_length) * self.sector, fat_size)

    def read(self, offset, size):
        if offset < 0 or size < 0 or offset + size > self.length:
            raise UnsupportedLayout('Read exceeds partition')
        self.file.seek(self.start + offset)
        data = self.file.read(size)
        if len(data) != size:
            raise UnsupportedLayout('Truncated exFAT image')
        return data

    def cluster_offset(self, cluster):
        if not 2 <= cluster < self.clusters + 2:
            raise UnsupportedLayout('Invalid exFAT cluster')
        return self.heap + (cluster - 2) * self.cluster_size

    def chain(self, first, length=None, contiguous=False):
        if length is not None:
            count = (length + self.cluster_size - 1) // self.cluster_size
            if not 0 < count <= self.clusters:
                raise UnsupportedLayout('Invalid exFAT stream length')
            if contiguous:
                self.cluster_offset(first); self.cluster_offset(first + count - 1)
                return range(first, first + count)
        else:
            count = min(self.clusters, 8 * 1024**2 // self.cluster_size)
        chain, seen, cluster = [], set(), first
        while True:
            self.cluster_offset(cluster)
            if cluster in seen or len(chain) >= count:
                raise UnsupportedLayout('Cyclic or oversized exFAT chain')
            seen.add(cluster); chain.append(cluster)
            following = struct.unpack_from('<I', self.fat, cluster * 4)[0]
            if following >= 0xfffffff8:
                if length is not None and len(chain) != count:
                    raise UnsupportedLayout('Short exFAT chain')
                return chain
            cluster = following

    def directory(self, first, length=None, contiguous=False):
        if length is not None and length > 8 * 1024**2:
            raise UnsupportedLayout('Directory exceeds size limit')
        data = b''.join(self.read(self.cluster_offset(c), self.cluster_size)
                        for c in self.chain(first, length, contiguous))
        entries, pos = [], 0
        while pos + 32 <= len(data):
            entry = data[pos:pos+32]
            if entry[0] == 0:
                break
            if entry[0] != 0x85:
                pos += 32; continue
            count = entry[1]
            group = data[pos:pos+32*(count+1)]
            if count < 2 or len(group) != 32*(count+1) or entry_checksum(group) != struct.unpack_from('<H', entry, 2)[0]:
                raise UnsupportedLayout('Invalid exFAT directory entry checksum')
            stream = group[32:64]
            if stream[0] != 0xc0 or not stream[1] & 1 or stream[1] & ~3:
                raise UnsupportedLayout('Unsupported exFAT stream flags')
            name_length = stream[3]
            name_entries = (name_length + 14) // 15
            if not name_length or count != 1 + name_entries:
                raise UnsupportedLayout('Unsupported exFAT directory entry set')
            name_bytes = b''
            for i in range(name_entries):
                part = group[64+i*32:96+i*32]
                if part[0] != 0xc1:
                    raise UnsupportedLayout('Invalid exFAT filename entry')
                name_bytes += part[2:32]
            try:
                name = name_bytes[:name_length*2].decode('utf-16le')
            except UnicodeError as error:
                raise UnsupportedLayout('Invalid exFAT filename') from error
            valid = struct.unpack_from('<Q', stream, 8)[0]
            first_cluster = struct.unpack_from('<I', stream, 20)[0]
            size = struct.unpack_from('<Q', stream, 24)[0]
            entries.append((name, bool(struct.unpack_from('<H', entry, 4)[0] & 0x10),
                            first_cluster, size, bool(stream[1] & 2), valid))
            pos += 32 * (count + 1)
        return entries

    def locate(self, parts):
        first, size, contiguous = self.root, None, False
        for index, part in enumerate(parts):
            found = [entry for entry in self.directory(first, size, contiguous) if entry[0].casefold() == part.casefold()]
            if len(found) != 1:
                raise UnsupportedLayout(f'exFAT path missing/ambiguous: {part}')
            _, directory, first, size, contiguous, valid = found[0]
            if valid != size:
                raise UnsupportedLayout('Partially initialized exFAT stream')
            if index < len(parts) - 1:
                if not directory: raise UnsupportedLayout('Expected exFAT directory')
            else:
                if directory: raise UnsupportedLayout('Expected exFAT file')
                clusters = self.chain(first, size, contiguous)
                if any(cluster != first + i for i, cluster in enumerate(clusters)):
                    raise UnsupportedLayout('Embedded HDF is fragmented')
                return self.start + self.cluster_offset(first), size
        raise UnsupportedLayout('Empty exFAT path')


def locate_hdf(image, path='roms/commodore_ami/AmigaVision.hdf'):
    image = Path(image)
    with image.open('rb') as file:
        return locate_hdf_reader(file, image.stat().st_size, path)


def locate_hdf_reader(file, image_size, path='roms/commodore_ami/AmigaVision.hdf'):
    file.seek(0)
    mbr = file.read(512)
    if len(mbr) != 512 or mbr[510:] != b'\x55\xaa':
        raise UnsupportedLayout('Expected MBR disk image')
    errors = []
    for i in range(4):
        entry = mbr[446+i*16:462+i*16]
        if entry[4] != 7: continue
        start, sectors = struct.unpack_from('<II', entry, 8)
        try:
            return Exfat(file, start*512, sectors*512, image_size).locate(path.split('/'))
        except UnsupportedLayout as error:
            errors.append(str(error))
    raise UnsupportedLayout('; '.join(errors) or 'No supported exFAT partition')
