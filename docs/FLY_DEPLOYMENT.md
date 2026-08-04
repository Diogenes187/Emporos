# Emporos Fly Deployment

`emporos-next.fly.dev` is the staging home for the PostgreSQL Emporos build.
The existing `emporos.fly.dev` SQLite application remains untouched until the
new build has passed playtesting and its data-migration plan has been rehearsed.

## Prepared configuration

- `Dockerfile` runs the FastAPI application on Fly's internal port 8080.
- `fly.toml` uses DFW, HTTPS, health checks, automatic start/stop, and a
  persistent `/data` mount for uploaded source originals.
- The release command bootstraps an empty PostgreSQL database or verifies and
  migrates an existing Emporos database.
- `EMPOROS_UPLOAD_ROOT=/data/uploads` keeps uploaded adventure files off the
  disposable application filesystem.

## Cost gate before first deployment

Do not deploy until these paid or potentially billable resources are approved:

1. Create a Fly Managed Postgres cluster and attach it to `emporos-next`.
2. Create the `emporos_uploads` volume in DFW.
3. Set AI-provider secrets on `emporos-next`.
4. Run `fly deploy --app emporos-next` and verify `/health` plus a disposable
   campaign before importing valuable campaign data.

## Later takeover of emporos.fly.dev

The staging app name is not embedded in application data. After validation,
deploy this repository with `fly deploy --app emporos`, replace the old SQLite
environment and volume configuration with PostgreSQL/upload settings, and only
then retire `emporos-next`. Preserve the old volume until the migration is
verified and backed up.
