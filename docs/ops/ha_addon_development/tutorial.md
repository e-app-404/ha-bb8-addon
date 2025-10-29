---
id: "OPS-HA_ADDON_TUTORIAL-01"
title: "Tutorial: Making your first add-on"
authors: "Home Assistant Team"
slug: "ha-addon-tutorial"
type: "tutorial"
tags: ["home-assistant", "add-on", "tutorial"]
date: "2023-01-01"
last_updated: "2024-06-09"
---

So you've got Home Assistant going and you've been enjoying the built-in add-ons, but you're missing that one application. Time to make your own add-on!

To get started with developing add-ons, you first need access to where Home Assistant looks for local add-ons. You can use the [Samba](https://my.home-assistant.io/redirect/supervisor_addon/?addon=core_samba) or [SSH](https://my.home-assistant.io/redirect/supervisor_addon/?addon=core_ssh) add-ons.

For Samba, once enabled and started, your Home Assistant instance will show up in your local network tab and share a folder called `addons`. This is the folder to store your custom add-ons.

> **Tip**:
> If you are on macOS and the folder is not showing up automatically, go to Finder and press <kbd>CMD</kbd>+<kbd>K</kbd>, then enter `smb://homeassistant.local`.

For SSH, you will need to install it. Before starting, generate a private/public key pair and store your public key in the add-on config ([see docs for more info](https://github.com/home-assistant/addons/blob/master/ssh/DOCS.md#configuration)). Once started, you can SSH to Home Assistant and store your custom add-ons in the `/addons` directory.

Once you have located your add-on directory, it's time to get started!

## Step 1: The basics

- Create a new directory called `hello_world`.
- Inside that directory, create three files:
    - `Dockerfile`
    - `config.yaml`
    - `run.sh`

### The `Dockerfile` file

This is the image that will be used to build your add-on.

```dockerfile
ARG BUILD_FROM
FROM $BUILD_FROM

# Copy data for add-on
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
```

### The `config.yaml` file

This is your add-on configuration, which tells the Supervisor what to do and how to present your add-on.

For an overview of all valid add-on configuration options, see [add-on configuration](/docs/add-ons/configuration#add-on-configuration).

```yaml
name: "Hello world"
description: "My first real add-on!"
version: "1.0.0"
slug: "hello_world"
init: false
arch:
    - aarch64
    - amd64
    - armhf
    - armv7
    - i386
```

### The `run.sh` file

This is the script that will run when your add-on starts.

```bash
#!/usr/bin/with-contenv bashio

echo "Hello world!"
```

> **Note**:
> Make sure your editor is using UNIX-like line breaks (LF), not DOS/Windows (CRLF).

## Step 2: Installing and testing your add-on

Now comes the fun part: time to open the Home Assistant UI and install and run your add-on.

- Open the Home Assistant frontend.
- Go to "Settings".
- Click on "Add-ons".
- Click "Add-on store" in the bottom right corner.

[![Open your Home Assistant instance and show the Supervisor add-on store.](https://my.home-assistant.io/badges/supervisor_store.svg)](https://my.home-assistant.io/redirect/supervisor_store/)

- In the top right overflow menu, click the "Check for updates" button.
- Refresh your webpage if needed.
- You should now see a new section at the top of the store called "Local add-ons" that lists your add-on!

![Screenshot of the local repository card](../../img/en/hass.io/screenshots/local_repository.png)

- Click on your add-on to go to the add-on details page.
- Install your add-on.
- Start your add-on.
- Click on the "Logs" tab, and refresh the logs of your add-on. You should now see "Hello world!" in your logs.

![Screenshot of the add-on logs](../../img/en/hass.io/tutorial/addon_hello_world_logs.png)

### I don't see my add-on?!

If you clicked "Check for updates" in the store and your add-on didn't show up, or you updated an option and your add-on disappeared, try refreshing your browser's cache first by pressing <kbd>Ctrl</kbd>+<kbd>F5</kbd> (Windows/Linux) or <kbd>Cmd</kbd>+<kbd>Shift</kbd>+<kbd>R</kbd> (macOS). If that didn't help, your `config.yaml` is likely invalid. It's either [invalid YAML](http://www.yamllint.com/) or one of the specified options is incorrect. To see what went wrong, go to ["Settings" → "System" → "Logs" and select "Supervisor" in the top-right drop-down menu](https://my.home-assistant.io/redirect/logs/?provider=supervisor). This should bring you to a page with the logs of the supervisor. Scroll to the bottom to find the validation error.

Once you fix the error, go to the add-on store and click "Check for updates" again.

## Step 3: Hosting a server

Until now we've done some basic stuff, but it's not very useful yet. Let's take it one step further and host a server that we expose on a port. We'll use the built-in HTTP server that comes with Python 3.

To do this, update your files as follows:

- `Dockerfile`: Install Python 3.
- `config.yaml`: Make the port from the container available on the host.
- `run.sh`: Run the Python 3 command to start the HTTP server.

Update your `Dockerfile`:

```dockerfile
ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements for add-on
RUN \
    apk add --no-cache \
        python3

# Python 3 HTTP Server serves the current working dir
# So let's set it to our add-on persistent data directory.
WORKDIR /data

# Copy data for add-on
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
```

Add `ports` to `config.yaml`. This will make TCP on port 8000 inside the container available on the host on port 8000.

```yaml
name: "Hello world"
description: "My first real add-on!"
version: "1.1.0"
slug: "hello_world"
init: false
arch:
    - aarch64
    - amd64
    - armhf
    - armv7
    - i386
startup: services
ports:
    8000/tcp: 8000
```

Update `run.sh` to start the Python 3 server:

```bash
#!/usr/bin/with-contenv bashio

echo "Hello world!"

python3 -m http.server 8000
```

## Step 4: Installing the update

Since you updated the version number in your `config.yaml`, Home Assistant will show an update button when viewing the add-on details. You might need to refresh your browser or click the "Check for updates" button in the add-on store for it to show up. If you did not update the version number, you can also uninstall and reinstall the add-on. After installing again, make sure you start it.

Now navigate to [http://homeassistant.local:8000](http://homeassistant.local:8000) to see your server in action!

![Screenshot of the file index served by the add-on](../../img/en/hass.io/tutorial/python3-http-server.png)

## Bonus: Working with add-on options

In the screenshot, you may have noticed that our server only served up one file: `options.json`. This file contains the user configuration for this add-on. Because we specified two empty objects for the `options` and `schema` keys in our `config.yaml`, the resulting file is currently empty.

Let's see if we can get some data into that file!

Specify the default options and a schema for the user to change the options. Change the `options` and `schema` entries in your `config.yaml` as follows:

```yaml
...
options:
    beer: true
    wine: true
    liquor: false
    name: "world"
    year: 2017
schema:
    beer: bool
    wine: bool
    liquor: bool
    name: str
    year: int
...
```

Reload the add-on store and reinstall your add-on. You will now see the options available in the add-on config screen. When you go back to your Python 3 server and download `options.json`, you'll see the options you set. [Example of how `options.json` can be used inside `run.sh`](https://github.com/home-assistant/addons/blob/master/dhcp_server/data/run.sh#L10-L13).

## Bonus: Template add-on repository

A full template example repository for add-ons is available to help you get started:
[`home-assistant/addons-example`](https://github.com/home-assistant/addons-example)
