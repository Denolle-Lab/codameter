# Scaling the codameter sweep on Fargate / AWS Batch

`codameter-bench` scores a grid of processing configs against every golden case
and records recovery RMS. The work is deterministic and embarrassingly parallel,
so it fans out cleanly across an array of Fargate tasks: each task runs one
`--shard k/N` and writes one `shard-<k>-of-<N>.jsonl` to S3.

## Size the job first

```bash
codameter-bench plan --grid multiverse --shard 0/64
# grid=multiverse  cases=10  configs/case=648
# total cells=6480  shards=64  cells/shard: min=101 max=102
```

`plan` needs no compute; use it to pick the array size and vCPUs per task. Grids:
`compact` (smoke), `multiverse` (default), `wide` (overnight).

## Run locally (one machine, all vCPUs)

```bash
codameter-bench sweep --grid multiverse --out ./out --jobs 8 --shard 0/1
codameter-bench aggregate --src ./out --out ./agg
```

`--jobs` spreads one shard's cells across worker processes. Splitting into shards
*and* using `--jobs` composes: shards across tasks, jobs across a task's vCPUs.

## Run on AWS Batch (Fargate)

1. **Build and push** the image:

   ```bash
   docker build -f docker/Dockerfile -t codameter-bench .
   aws ecr get-login-password --region <REGION> | docker login --username AWS \
     --password-stdin <ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com
   docker tag codameter-bench <ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/codameter-bench:latest
   docker push <ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/codameter-bench:latest
   ```

2. **Register** the job definition (edit placeholders + `CODAMETER_SHARDS` first):

   ```bash
   aws batch register-job-definition --cli-input-json file://docker/aws-batch-job-def.json
   ```

3. **Submit** an array of N tasks (N must equal `CODAMETER_SHARDS`):

   ```bash
   aws batch submit-job --job-name codameter-sweep --job-queue <QUEUE> \
     --job-definition codameter-sweep --array-properties size=64
   ```

   Batch sets `AWS_BATCH_JOB_ARRAY_INDEX` on each task; the CLI reads it together
   with `CODAMETER_SHARDS` to select the shard, so every task runs the same image
   and command. The `jobRoleArn` needs `s3:PutObject` on the output prefix.

4. **Aggregate** when the array finishes (locally or as a final one-off task):

   ```bash
   codameter-bench aggregate --src s3://<BUCKET>/codameter-sweep/run-001/ \
                             --out  s3://<BUCKET>/codameter-sweep/run-001/agg/
   ```

## Notes

- **Idempotent retries.** Each shard writes exactly its own file, named by shard,
  so a Batch retry overwrites only that shard. No coordination, no partial merges.
- **Even load.** Sharding is round-robin (`items[k::N]`), so the slow configs
  (moving / inversion references, which rerun the estimator per epoch) spread
  evenly instead of piling into one task.
- **s3://** output needs the `aws` extra (`pip install "codameter[aws]"`, already
  in the image). Local paths need nothing.
- **Cost knob.** vCPUs per task x array size sets throughput; `plan` tells you the
  cell count so you can trade array size against per-task `--jobs`.
