import io
import struct
import unittest

from exfat_extent import locate_hdf_reader, UnsupportedLayout


def file_entry(name, first, size, directory=False, contiguous=True):
    units = name.encode('utf-16le')
    names = (len(units) + 29) // 30
    data = bytearray(32 * (2 + names))
    data[0:2] = bytes([0x85, 1 + names])
    struct.pack_into('<H', data, 4, 0x10 if directory else 0x20)
    data[32:36] = bytes([0xc0, 3 if contiguous else 1, 0, len(units)//2])
    struct.pack_into('<Q', data, 40, size)
    struct.pack_into('<I', data, 52, first)
    struct.pack_into('<Q', data, 56, size)
    for i in range(names):
        data[64+i*32] = 0xc1
        part = units[i*30:(i+1)*30]
        data[66+i*32:66+i*32+len(part)] = part
    checksum = 0
    for i, value in enumerate(data):
        if i not in (2, 3):
            checksum = ((checksum >> 1) | ((checksum & 1) * 0x8000)) + value
            checksum &= 0xffff
    struct.pack_into('<H', data, 2, checksum)
    return data


def image_fixture(payload, fragmented=False, fat_chain=False):
    start, clusters, sector = 128 * 512, 20000, 512
    fat_sectors = ((clusters + 2) * 4 + 511) // 512
    heap = (24 + fat_sectors) * sector
    volume_size = heap + clusters * sector
    image = bytearray(start + volume_size)
    image[510:512] = b'\x55\xaa'
    image[450] = 7
    struct.pack_into('<II', image, 454, start//512, volume_size//512)
    boot = memoryview(image)[start:start+12*sector]
    boot[3:11] = b'EXFAT   '; boot[510:512] = b'\x55\xaa'
    struct.pack_into('<Q', boot, 64, start//512)
    struct.pack_into('<Q', boot, 72, volume_size//512)
    struct.pack_into('<IIIII', boot, 80, 24, fat_sectors, heap//sector, clusters, 2)
    struct.pack_into('<H', boot, 104, 0x100)
    boot[108:111] = bytes([9, 0, 1])
    checksum = 0
    for i, byte in enumerate(boot[:11*sector]):
        if i not in (106, 107, 112):
            checksum = (((checksum >> 1) | ((checksum & 1) * 0x80000000)) + byte) & 0xffffffff
    boot[11*sector:] = struct.pack('<I', checksum) * (sector//4)
    fat = start + 24 * sector
    struct.pack_into('<I', image, fat+2*4, 0xffffffff)
    root = start + heap
    for cluster, name, first in [(2, 'roms', 3), (3, 'commodore_ami', 4)]:
        entry = file_entry(name, first, sector, directory=True)
        offset = root + (cluster-2)*sector
        image[offset:offset+len(entry)] = entry
    count = (len(payload)+sector-1)//sector
    chain = list(range(8, 8+count))
    if fragmented:
        chain = [8] + list(range(10, 10+count-1))
    if fragmented or fat_chain:
        for i, cluster in enumerate(chain):
            struct.pack_into('<I', image, fat+cluster*4, chain[i+1] if i+1 < len(chain) else 0xffffffff)
    entry = file_entry('AmigaVision.hdf', 8, len(payload), contiguous=not (fragmented or fat_chain))
    offset = root+2*sector
    image[offset:offset+len(entry)] = entry
    for i, cluster in enumerate(chain):
        offset = root+(cluster-2)*sector
        data = payload[i*sector:(i+1)*sector]
        image[offset:offset+len(data)] = data
    return image, root+6*sector


class ExfatTests(unittest.TestCase):
    def test_contiguous_and_contiguous_fat_chain(self):
        payload = b'RDSK' + bytes(range(256)) * 8
        for chained in (False, True):
            image, offset = image_fixture(payload, fat_chain=chained)
            actual, size = locate_hdf_reader(io.BytesIO(image), len(image))
            self.assertEqual((actual, size), (offset, len(payload)))
            self.assertEqual(image[actual:actual+size], payload)

    def test_fragmented_or_corrupt_directory_and_boot_rejected(self):
        image, offset = image_fixture(b'x' * 1024, fragmented=True)
        with self.assertRaisesRegex(UnsupportedLayout, 'fragmented'):
            locate_hdf_reader(io.BytesIO(image), len(image))
        image, offset = image_fixture(b'x' * 1024)
        image[offset-4*512+4] ^= 1
        with self.assertRaisesRegex(UnsupportedLayout, 'entry checksum'):
            locate_hdf_reader(io.BytesIO(image), len(image))
        image, offset = image_fixture(b'x' * 1024)
        image[128*512+120] ^= 1
        with self.assertRaisesRegex(UnsupportedLayout, 'boot checksum'):
            locate_hdf_reader(io.BytesIO(image), len(image))

    def test_cyclic_root_and_truncated_image_rejected(self):
        image, _ = image_fixture(b'x' * 1024)
        struct.pack_into('<I', image, 128*512+24*512+2*4, 2)
        with self.assertRaisesRegex(UnsupportedLayout, 'Cyclic'):
            locate_hdf_reader(io.BytesIO(image), len(image))
        with self.assertRaises(UnsupportedLayout):
            locate_hdf_reader(io.BytesIO(image[:-1024]), len(image)-1024)


if __name__ == '__main__': unittest.main()
