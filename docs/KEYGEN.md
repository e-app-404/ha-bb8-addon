# Debugging the Home Assistant Operating System | Home Assistant Developer Docs

developers.home-assistant.io /docs/operating-system/debugging/

This section is not for end users. End users should use the SSH add-on to SSH into Home Assistant. This is for developers of Home Assistant. Do not ask for support if you are using these options.

## Enabling SSH access to the host​

SSH access through the SSH add-on (on port 22 by default) only grants limited privileges, and you will be asked for a username and password when typing the 'login' command. Follow the steps below to enable a separate SSH access on port 22222 that works independently of the add-on and gives you direct access to the Home Assistant OS (the "host") with full privileges.

Use a USB drive with a partition named CONFIG (case sensitive) formatted as FAT, ext4, or NTFS. Create an authorized_keys text file (without a file extension) containing your public key(s), one per line, and place it in the root of the USB drive's CONFIG partition. The file must use POSIX-standard newline control characters (LF), not Windows ones (CR LF), and needs to be ASCII character encoded (i.e. mustn't contain any special characters in the comments).

See Generating SSH Keys section below if you need help generating keys.

Connect the USB drive to your Home Assistant OS device and either explicitly import the drive's contents using the ha os import command (e.g. via SSH to the SSH add-on on port 22) or reboot the device leaving the drive attached, which automatically triggers the import.

### tip

Make sure when you are copying the public key(s) to the root of the USB drive that you correctly name the file authorized_keys without a .pub file extension.

You should now be able to connect to your device as root over SSH on port 22222. On Mac/Linux, use:

```
ssh root@homeassistant.local -p 22222
```

If you have an older installation or have changed your hostname, you may need to adjust the command above accordingly. You can alternatively use the device's IP address instead of the hostname.

You will be logged in as root with the /root folder set as the working directory. Home Assistant OS is a hypervisor for Docker. See the Supervisor Architecture documentation for information regarding the Supervisor. The Supervisor offers an API to manage the host and running the Docker containers. Home Assistant itself and all installed addons run in separate Docker containers.

## Disabling SSH access to the host​

Use a USB drive with a partition named CONFIG (case sensitive) formatted as FAT, ext4, or NTFS. Remove any existing authorized_keys file from the root of that partition.

When the Home Assistant OS device is rebooted with this drive inserted, any existing SSH public keys will be removed and SSH access on port 22222 will be disabled.

## Checking the logs​

### Logs from the supervisor service on the Host OS
```
journalctl -f -u hassos-supervisor.service
```

### Supervisor logs
```
docker logs hassio_supervisor
```

### Home Assistant logs
```
docker logs homeassistant
Accessing the container bash​
docker exec -it homeassistant /bin/bash
```

### Generating SSH Keys​
Windows instructions on how to generate and use private/public keys with Putty are found here. Instead of the droplet instructions, add the public key as per above instructions.

Alternative instructions for Mac, Windows and Linux can be found here. Follow the steps under Generating a new SSH key (the other sections are not applicable to Home Assistant and can be ignored).

Make sure to copy the public key of the SSH key pair you just created. By default, the public key file is named id_ed25519.pub (in case of the Ed25519 elliptic curve algorithm) or id_rsa.pub (in case of the older RSA algorithm), i.e. it should have a .pub filename suffix. It is saved to the same folder as the private key (which is named id_ed25519 or id_rsa by default).

## Checking for existing SSH keys

Before you generate an SSH key, you can check to see if you have any existing SSH keys.

### About SSH keys

You can use SSH to perform Git operations in repositories. For more information, see About SSH.
If you have an existing SSH key, you can use the key to authenticate Git operations over SSH.

### Checking for existing SSH keys

Before you generate a new SSH key, you should check your local machine for existing keys.

Note: GitHub improved security by dropping older, insecure key types on March 15, 2022.

As of that date, DSA keys (ssh-dss) are no longer supported. You cannot add new DSA keys to your personal account on GitHub.

RSA keys (ssh-rsa) with a valid_after before November 2, 2021 may continue to use any signature algorithm. RSA keys generated after that date must use a SHA-2 signature algorithm. Some older clients may need to be upgraded in order to use SHA-2 signatures.

Open Terminal.

Enter `ls -al ~/.ssh` to see if existing SSH keys are present.

```
$ ls -al ~/.ssh
# Lists the files in your .ssh directory, if they exist
```

Check the directory listing to see if you already have a public SSH key. By default, the filenames of supported public keys for GitHub are one of the following.

- id_rsa.pub
- id_ecdsa.pub
- id_ed25519.pub

### Tip

If you receive an error that ~/.ssh doesn't exist, you do not have an existing SSH key pair in the default location. You can create a new SSH key pair in the next step.

Either generate a new SSH key or upload an existing key.

If you don't have a supported public and private key pair, or don't wish to use any that are available, generate a new SSH key.

If you see an existing public and private key pair listed (for example, id_rsa.pub and id_rsa) that you would like to use to connect to GitHub, you can add the key to the ssh-agent.

> For more information about generation of a new SSH key or addition of an existing key to the ssh-agent, see Generating a new SSH key and adding it to the ssh-agent.


## Generating a new SSH key and adding it to the ssh-agent - GitHub Docs

docs.github.com /en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent

After you've checked for existing SSH keys, you can generate a new SSH key to use for authentication, then add it to the ssh-agent.

### About SSH key passphrases
You can access and write data in repositories on GitHub using SSH (Secure Shell Protocol). When you connect via SSH, you authenticate using a private key file on your local machine. For more information, see About SSH.

When you generate an SSH key, you can add a passphrase to further secure the key. Whenever you use the key, you must enter the passphrase. If your key has a passphrase and you don't want to enter the passphrase every time you use the key, you can add your key to the SSH agent. The SSH agent manages your SSH keys and remembers your passphrase.

If you don't already have an SSH key, you must generate a new SSH key to use for authentication. If you're unsure whether you already have an SSH key, you can check for existing keys. For more information, see Checking for existing SSH keys.

If you want to use a hardware security key to authenticate to GitHub, you must generate a new SSH key for your hardware security key. You must connect your hardware security key to your computer when you authenticate with the key pair. For more information, see the OpenSSH 8.2 release notes.

### Generating a new SSH key
You can generate a new SSH key on your local machine. After you generate the key, you can add the public key to your account on GitHub.com to enable authentication for Git operations over SSH.

Note: GitHub improved security by dropping older, insecure key types on March 15, 2022.

As of that date, DSA keys (ssh-dss) are no longer supported. You cannot add new DSA keys to your personal account on GitHub.

RSA keys (ssh-rsa) with a valid_after before November 2, 2021 may continue to use any signature algorithm. RSA keys generated after that date must use a SHA-2 signature algorithm. Some older clients may need to be upgraded in order to use SHA-2 signatures.

Open Terminal.

Paste the text below, replacing the email used in the example with your GitHub email address.

```
ssh-keygen -t ed25519 -C "your_email@example.com"
```

Note: If you are using a legacy system that doesn't support the Ed25519 algorithm, use:

```
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

This creates a new SSH key, using the provided email as a label.

### Generating public/private ALGORITHM key pair.
When you're prompted to "Enter a file in which to save the key", you can press Enter to accept the default file location. Please note that if you created SSH keys previously, ssh-keygen may ask you to rewrite another key, in which case we recommend creating a custom-named SSH key. To do so, type the default file location and replace id_ALGORITHM with your custom key name.

> Enter a file in which to save the key (/Users/YOU/.ssh/id_ALGORITHM): [Press enter]
At the prompt, type a secure passphrase. For more information, see Working with SSH key passphrases.

> Enter passphrase (empty for no passphrase): [Type a passphrase]
> Enter same passphrase again: [Type passphrase again]

### Adding your SSH key to the ssh-agent

Before adding a new SSH key to the ssh-agent to manage your keys, you should have checked for existing SSH keys and generated a new SSH key. When adding your SSH key to the agent, use the default macOS ssh-add command, and not an application installed by macports, homebrew, or some other external source.

Start the ssh-agent in the background.

```
$ eval "$(ssh-agent -s)"
> Agent pid 59566
```

Depending on your environment, you may need to use a different command. For example, you may need to use root access by running sudo -s -H before starting the ssh-agent, or you may need to use exec ssh-agent bash or exec ssh-agent zsh to run the ssh-agent.

If you're using macOS Sierra 10.12.2 or later, you will need to modify your ~/.ssh/config file to automatically load keys into the ssh-agent and store passphrases in your keychain.

First, check to see if your ~/.ssh/config file exists in the default location.

```
$ open ~/.ssh/config
```

> The file /Users/YOU/.ssh/config does not exist.

If the file doesn't exist, create the file.

```
touch ~/.ssh/config
```

Open your ~/.ssh/config file, then modify the file to contain the following lines. If your SSH key file has a different name or path than the example code, modify the filename or path to match your current setup.

```
Host github.com
  AddKeysToAgent yes
  UseKeychain yes
  IdentityFile ~/.ssh/id_ed25519
```

Note:

If you chose not to add a passphrase to your key, you should omit the UseKeychain line.
If you see a Bad configuration option: usekeychain error, add an additional line to the configuration's' Host *.github.com section.

```Text
Host github.com
  IgnoreUnknown UseKeychain
```

Add your SSH private key to the ssh-agent and store your passphrase in the keychain. If you created your key with a different name, or if you are adding an existing key that has a different name, replace id_ed25519 in the command with the name of your private key file.

```
ssh-add --apple-use-keychain ~/.ssh/id_ed25519
```

Note:

The --apple-use-keychain option stores the passphrase in your keychain for you when you add an SSH key to the ssh-agent. If you chose not to add a passphrase to your key, run the command without the --apple-use-keychain option.

The --apple-use-keychain option is in Apple's standard version of ssh-add. In macOS versions prior to Monterey (12.0), the --apple-use-keychain and --apple-load-keychain flags used the syntax -K and -A, respectively.

If you don't have Apple's standard version of ssh-add installed, you may receive an error. For more information, see Error: ssh-add: illegal option -- apple-use-keychain.

If you continue to be prompted for your passphrase, you may need to add the command to your ~/.zshrc file (or your ~/.bashrc file for bash).

Add the SSH public key to your account on GitHub. For more information, see Adding a new SSH key to your GitHub account.

Generating a new SSH key for a hardware security key
If you are using macOS or Linux, you may need to update your SSH client or install a new SSH client prior to generating a new SSH key. For more information, see Error: Unknown key type.

Insert your hardware security key into your computer.

Open Terminal.

Paste the text below, replacing the email address in the example with the email address associated with your GitHub account.

```
ssh-keygen -t ed25519-sk -C "your_email@example.com"
```

Note

If the command fails and you receive the error invalid format or feature not supported, you may be using a hardware security key that does not support the Ed25519 algorithm. Enter the following command instead.

```
ssh-keygen -t ecdsa-sk -C "your_email@example.com"
```

When you are prompted, touch the button on your hardware security key.

When you are prompted to "Enter a file in which to save the key," press Enter to accept the default file location.

> Enter a file in which to save the key (/Users/YOU/.ssh/id_ed25519_sk): [Press enter]

When you are prompted to type a passphrase, press Enter.

> Enter passphrase (empty for no passphrase): [Type a passphrase]
> Enter same passphrase again: [Type passphrase again]
Add the SSH public key to your account on GitHub. For more information, see Adding a new SSH key to your GitHub account.

### Discussion Forum Posts

#### HOWTO: How to access the Home Assistant OS host itself over ssh 

https://community.home-assistant.io/t/howto-how-to-access-the-home-assistant-os-host-itself-over-ssh/263352

It took a while to figure this out, so I might as well document this. Looking at the amount of search hits on this subject, I wasn’t not the only one that needed access to the host itself.

When debugging an issue related to the OS or docker, you might need access to the host itself. The Terminal & SSH Add-on drops you in a container, while this might be enough for users, you sometimes want to access the real operating system, to examine some docker issue for example.

There is a well written documentation on how to do this here: Debugging the Home Assistant Operating System | Home Assistant Developer Docs but this only works nicely when you are running HA on a Raspberry Pi. When running HA in a VM like on Proxmox, it’s more difficult to map an USB stick to be able to copy the file. Note that these steps below do the exact same thing as the copy does.

You’ll first need to login to the host itself, trough the host console. You can do this from within the interface of Proxmox. Just open the console, and login with root, you don’t need a password. Then, use login to drop to a shell. This is enough to access the host shell, but since the console doesn’t work nicely, we want to continue to enable SSH.
Now, I assume you are already running the Terminal & SSH Add-on, and have it configured with your public key. Go to your .ssh directory by running cd /root/.ssh/, and next, copy the authorized_keys file to the host. You can do this with docker cp addon_core_ssh:/root/.ssh/authorized_keys . (Note the single dot at the end of the command). To be sure, give it the right permissions, but this should already be the case. chmod 600 authorized_keys
Finally, you’ll need to start dropbear. You can do this with systemctl start dropbear.
You can now connect to your host with ssh root@hass -p 22222. Replace the hostname if needed.
I’m sorry if this has already been mentioned somewhere else, but I couldn’t find it. I might add it to the docs at Debugging the Home Assistant Operating System | Home Assistant Developer Docs sometime, but since it’s quite an advanced topic, it might not be that usefull.
