# Home Assistant Add-on: Docker Build, Run, and Validation Guide

This guide documents the recommended commands, execution sequence, and troubleshooting tips for building, running, and validating your Home Assistant add-on container. It also includes best practices for workspace cleanup, build context verification, and reproducibility.

## Workspace Preparation and Best Practices

Before deploying or building your add-on, follow these steps to ensure a clean and reproducible environment:

- **Clean up macOS system files:**
  ```sh
  find . -name '.DS_Store' -delete && find . -name '._*' -delete && find . -name '.AppleDouble' -delete && find . -name '.Apple*' -delete
  ```
  This removes unwanted artifacts that can pollute your build context or deployment target.

- **Verify build context:**
  Ensure all required files (e.g., `run.sh`, `bb8_core/main.py`, config files) are present in the `addon/` directory before running `docker build`.

- **Check file permissions:**
  Scripts and executables (like `run.sh` and service scripts) should have the correct permissions:
  ```sh
  chmod +x addon/run.sh addon/services.d/*/run
  ```

- **Version control:**
  Commit all source changes to git before deployment. If deploying from a remote, pull the latest changes.

- **Container cleanup:**
  Remove unused or exited containers and images to free up disk space:
  ```sh
  docker container prune
  docker image prune
  ```

- **Python virtual environment (local testing):**
  If using a local venv, activate it and install dependencies before building or testing:
  ```sh
  source .venv/bin/activate
  pip install -r requirements-dev.txt
  ```

- **Rebuilding Python bytecode:**
  Since `__pycache__` and `.pyc` files are excluded during rsync, Python will regenerate them on first run in the container.


```sh
docker build --build-arg BUILD_FROM=ghcr.io/home-assistant/aarch64-base:latest -t beep_boop_bb8 addon/
```
- **Purpose:** Builds the Docker image from the `addon/` directory using the specified base image.
- **Tip:** Change the tag (`beep_boop_bb8`) as needed for your workflow.

---

## 2. Remove Previous Container (if exists)

```sh
docker rm -f addon_local_beep_boop_bb8
```
- **Purpose:** Removes any previous container with the same name to avoid conflicts.

---

## 3. Run the Container

```sh
docker run --name addon_local_beep_boop_bb8 -d beep_boop_bb8
```
- **Purpose:** Starts the container in detached mode.

---

## 4. Get the Container ID

```sh
CID=$(docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}')
echo $CID  # Should print the container ID
```
- **Purpose:** Sets the `$CID` variable for use in subsequent commands.
- **Tip:** Always run this after starting a new container.

---

## 5. Validation Commands

### Check Container is Running
```sh
docker ps --filter name=addon_local_beep_boop_bb8
```

### Check Wrapper Script Presence
```sh
docker exec "$CID" test -f /usr/src/app/run.sh && echo "RUN_SH_PRESENT" || echo "RUN_SH_MISSING"
```

### Check venv Activation
```sh
docker exec "$CID" bash -lc 'echo $VIRTUAL_ENV'
docker exec "$CID" bash -lc 'which python'
```

### Check Interpreter Used by run.sh
```sh
docker exec "$CID" bash -lc 'PRINT_INTERP=1 /usr/src/app/run.sh'
```

### Check s6 and cont-init.d Script Logs
```sh
docker logs "$CID"
```

### Check Python Module Import (bb8_core.main)
```sh
docker exec "$CID" ls /usr/src/app/bb8_core
docker exec "$CID" test -f /usr/src/app/bb8_core/main.py && echo "main.py present" || echo "main.py missing"
docker exec "$CID" test -f /usr/src/app/bb8_core/__init__.py && echo "__init__.py present" || echo "__init__.py missing"
docker exec "$CID" /opt/venv/bin/python -c "import bb8_core.main"
docker exec "$CID" /opt/venv/bin/python -m bb8_core.main
```
These commands confirm that `main.py` and `__init__.py` exist and that the Python module is importable and runnable.

---

## 6. Troubleshooting Tips

- **Container Exits Immediately:**
  - Check logs: `docker logs "$CID"`
  - Ensure all scripts in `/etc/cont-init.d` have correct shebangs and are executable.
  - Validate that `/usr/src/app/run.sh` exists and is executable.
  - Confirm that the venv is created and activated correctly.

- **Python Import Errors (No module named 'bb8_core.main'):**
  - Ensure `addon/bb8_core/main.py` exists in your source tree.
  - Ensure `addon/bb8_core/__init__.py` exists.
  - Rebuild and redeploy the Docker image after adding `main.py`:
  
    ```sh
    docker build --build-arg BUILD_FROM=ghcr.io/home-assistant/aarch64-base:latest -t beep_boop_bb8 addon/
    docker rm -f addon_local_beep_boop_bb8
    docker run --name addon_local_beep_boop_bb8 -d beep_boop_bb8
    CID=$(docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}')
    ```
  - Validate with the commands above to confirm the module is present and importable.

- **$CID is Empty:**
  - Always set `$CID` after starting a new container.
  - Run: `CID=$(docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}')`

- **Script or Permission Errors:**
  - Check permissions: `docker exec "$CID" ls -l /etc/cont-init.d`
  - Check script syntax and shebangs in all init scripts.

- **s6-rc or execline Errors:**
  - Ensure all scripts in `/etc/cont-init.d` are valid shell scripts (not execline unless intended).
  - Use `#!/usr/bin/with-contenv sh` for shell scripts.

---

## 7. Additional Validation

- To inspect files and directories:
  ```sh
  docker exec "$CID" ls -l /usr/src/app
  docker exec "$CID" ls -l /etc/cont-init.d
  ```
- To debug environment variables:
  ```sh
  docker exec "$CID" env
  ```

---

## 8. If Problems Persist

Provide the following for further diagnosis:
- Output of `docker logs "$CID"`
- Contents of scripts in `/etc/cont-init.d` and `/etc/services.d`
- Output of `ls -l /etc/cont-init.d` and `ls -l /usr/src/app`

## 9. Python Entrypoint Example

To run the main entrypoint directly:
```sh
docker exec "$CID" /opt/venv/bin/python -m bb8_core.main
```
This will execute the `main()` function in `bb8_core/main.py` if present.

---


## 10. Why Use rsync for Deployment?

`rsync` is used to efficiently synchronize your local `addon/` directory with the target deployment location (such as `/Volumes/addons/local/beep_boop_bb8/`). This ensures:
- All source files, configuration, and required assets are updated on the deployment target.
- Files deleted locally are also removed from the target (with `--delete`).
- Unwanted artifacts (like `.DS_Store`, `__pycache__`, and `.pyc` files) are excluded, preventing permission errors and unnecessary clutter.
- Directory structure and file permissions are preserved for reproducible add-on updates.

**Recommended command:**
```sh
rsync -av --delete \
  --exclude='.DS_Store' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  addon/ /Volumes/addons/local/beep_boop_bb8/
```

**Tip:** Adjust excludes as needed for your environment. Always run rsync before building or deploying to ensure the target matches your source tree.

---
**Last updated:** 2025-08-27
