---
id: "OPS-SUPERVISOR-DEBUG-01"
title: "Debugging the Home Assistant Supervisor"
authors: "Home Assistant Contributors"
source: "https://github.com/home-assistant/supervisor"
slug: "supervisor-debugging"
type: "guide"
tags: ["supervisor", "debugging", "home-assistant", "development"]
date: "2023-01-01"
last_updated: "2024-06-09"
url: "https://github.com/home-assistant/supervisor/blob/main/docs/debugging.md"
related: ""
adr: ""
---

# Debugging the Home Assistant Supervisor

The following debug tips and tricks are for developers running the Home Assistant image and working on the base image. If you use the generic Linux installer script, you should be able to access your host and logs as per your host.

## Debug Supervisor

Before you can use the Python debugger, enable the debug option in Supervisor:

```shell
ha su options --debug=true
ha su reload
```

If you are running Supervisor on a remote host, you will not be able to access the Supervisor container directly. The "Remote ptvsd debugger" add-on (available from the [Development Add-On Repository](https://github.com/home-assistant/addons-development)) exposes the debugging port on your host IP address, allowing you to debug the Supervisor remotely.

Below is an example Visual Studio Code configuration to attach a Python debugger to the Home Assistant Supervisor. This configuration is intended as the default for Run > Start Debugging or pressing F5. Change `IP` to match your Supervisor's IP within the Docker environment (use `ip addr` within the Supervisor container) or the host IP if you debug remotely.

`.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Supervisor remote debug",
            "type": "python",
            "request": "attach",
            "port": 33333,
            "host": "IP",
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/usr/src/hassio"
                }
            ]
        }
    ]
}
```
