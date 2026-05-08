# <stage_id>

This directory is a stage workspace.

If an AI window opens here, it performs only this stage.

## Role

<role_summary>

## Model Profile

`<model_profile>`

## Run When

<run_condition>

## First Read

1. `../_system/START_HERE.md`
2. `../_system/project_canon.md`
3. `../_system/stage_manifest.json`
4. the files listed under this stage in `stage_manifest.json`

## Inputs

```text
<input_files>
```

## Outputs

```text
<output_files>
```

## Lock

Update:

```text
<lock_file>
```

## Boundary

Do not scan or rewrite unrelated project files. Do not perform another stage's work.

## Stop Rule

After writing the allowed outputs and updating the lock file, stop.

Do not start the next stage from this window unless the user explicitly instructs you to do so.
