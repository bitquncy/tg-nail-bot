# Release Notes v1.0.1

Nailshop Bot `v1.0.1` is a patch release on top of `v1.0.0`.

## Included

- Premium Telegram emoji markup is used consistently in HTML messages when enabled.
- Inline and reply buttons are text-only, avoiding unsupported custom emoji markup inside button labels.
- Service selection shows full service names without truncation.
- Service keyboards read the current runtime service map.

## Verified Before Release

- Full test suite: `343 passed, 3 skipped`.
- Coverage: `65%`.
- Docker Compose build passed.
- Runtime healthcheck passed after bot container recreation.
- Service button smoke check showed full names in the running container.
- Release ZIP validation: `76` entries, `0` banned artifacts.

## Upgrade Notes

- No database migration is required for this patch release.
- Rebuild and recreate the bot container so the updated keyboards/messages are active.
- Existing `.env` values can be kept.

## Git Release Commands

Prepare and run manually after final owner approval:

```powershell
git add .
git commit -m "Release v1.0.1"
git tag v1.0.1
git push
git push origin v1.0.1
```
