import struct

from header import read_header


class InatLookup:

    def __init__(self, filename):

        self.filename = filename

        self.f = open(filename, "rb")

        info = read_header(self.f)

        self.magic = info["magic"]
        self.version = info["version"]
        self.records = info["record_count"]
        self.record_size = info["record_size"]
        self.header_size = info["header_size"]
        self.build_time = info["build_time"]

    def close(self):
        self.f.close()

    def find(self, photo_id):

        low = 0
        high = self.records - 1

        while low <= high:

            mid = (low + high) // 2

            self.f.seek(
                self.header_size +
                mid * self.record_size
            )

            data = self.f.read(self.record_size)

            if len(data) != self.record_size:
                return None

            pid = struct.unpack(">Q", data[:8])[0]

            if pid == photo_id:

                uuid = data[8:]

                uuid = (
                    uuid[:4].hex() + "-" +
                    uuid[4:6].hex() + "-" +
                    uuid[6:8].hex() + "-" +
                    uuid[8:10].hex() + "-" +
                    uuid[10:].hex()
                )

                return uuid

            if pid < photo_id:
                low = mid + 1
            else:
                high = mid - 1

        return None