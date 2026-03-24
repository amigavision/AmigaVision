#!/usr/bin/env python3

# AGSImager: Types

class EntryCollection:
    def __init__(self):
        # entry_id: entry
        self.by_id = dict()
        # {"entry_id", "path"}
        self.path_ids = set()
        # runfile_path: int
        self.path_sort_rank = dict()
        # list of entries with overrides
        self.overridden_entries = []
        # AGS tree progress counters
        self.progress_current = 0
        self.progress_total = 0
        # AGS tree timing counters
        self.timing = dict()

    def ids(self):
        return self.by_id.values()
