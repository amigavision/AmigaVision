# Pages to README sync

`docs.md` in the `amigavision/amigavision.github.io` repo is treated as the canonical documentation source.

That repo's workflow rebuilds `README.md` in `amigavision/AmigaVision` by removing the Jekyll front matter from `docs.md` and then pushing the result here.

If the sync stops working, check the workflow and `AMIGAVISION_REPO_SYNC_TOKEN` secret in the `amigavision.github.io` repository.
