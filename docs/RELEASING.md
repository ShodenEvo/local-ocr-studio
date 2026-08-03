# Release Process

1. Update `CHANGELOG.md` and application version.
2. Run tests on Windows and Linux.
3. Tag the release, for example `v1.0.0`.
4. Push the tag to GitHub.
5. Create a GitHub Release with release notes and source archives.
6. Attach a Windows manager executable only if built from the tagged source.
7. Publish SHA-256 checksums for downloadable binaries.

Do not commit generated executables to the main branch. Attach them to GitHub Releases instead.
