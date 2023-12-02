# Buildscript for extension
# Packages extension into VSIX using vsce

import os
import json
import semver
import argparse
import requests
from colorama import Fore, Back, Style
import base64

class Builder:
    def __init__(self, build_command, branch) -> None:
        self.cmd = build_command
        self.branch = branch

        with open('package.json') as f:
            self.package = json.load(f)

        self.version = self.package['version']

    def bump_patch(self):
        self.package['version'] = semver.bump_patch(self.version) + self.branch

        with open('package.json', 'w') as f:
            json.dump(self.package, f, indent=4)

    def build(self):
        os.system(self.cmd)

class Logger:
    @staticmethod
    def log(color: Back, type: str, message: str):
        print(f"{color}{Fore.BLACK} {type} {Style.RESET_ALL} {message}")

    @staticmethod
    def err(message: str, response_code: int = None):
        Logger.log(Back.RED, "ERROR" if response_code == None else "ERROR - HTTP " + str(response_code), message)

    @staticmethod
    def done(message: str, response_code: int = None):
        Logger.log(Back.GREEN, "DONE" if response_code == None else "DONE - HTTP " + str(response_code), message)

    @staticmethod
    def ok(message: str, response_code: int = None):
        Logger.log(Back.GREEN, "OK" if response_code == None else "OK - HTTP " + str(response_code), message)

class Publisher:
    def __init__(self, owner, repo, isPreRelease, version, release_body, filename):
        self.owner = owner
        self.repo = repo
        self.prerelease = isPreRelease
        self.tag = 'v' + version
        self.filename = filename

        self.payload = {
            'name': self.tag,
            'tag_name': self.tag,
            'target_commitish': 'main',
            'body': release_body,
            'draft': False,
            'prerelease': self.prerelease
        }

        with open("GH_TOKEN", 'r') as f:
            self.token = f.read()

    def list_release(self):
        print(f"\nPreparing to create release on {self.owner}/{self.repo}\n")

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {self.token}'
        }

        print("Sending payload:", self.payload, '\n')

        response = requests.post(
            f'https://api.github.com/repos/{self.owner}/{self.repo}/releases',
            headers=headers,
            data=json.dumps(self.payload)
        )

        if 200 <= response.status_code <= 299:
            Logger.done(f'Release {self.tag} created successfully. (https://github.com/{self.owner}/{self.repo}/releases/tag/{self.tag})', "HTTP + " + response.status_code)
        else:
            Logger.err(
f"""Failed to create release. Response: {response.text} (https://github.com/{self.owner}/{self.repo}/releases/tag/{self.tag})

Try:
- Checking if a release already exists with that tag
- Make sure you're connected to the internet
""", response.status_code)
        exit(-1)

    def get_release_id_url(self):
        return requests.get(
            f'https://api.github.com/repos/{self.owner}/{self.repo}/releases/tags/{self.tag}',
            headers = {
                'Authorization': f'Token {self.token}',
            },  
        ).json()['url']

    # TODO: #2 Make buildscript properly delete tags    
    def delete_release(self):
        response = requests.delete(
            self.get_release_id_url(),
            headers = {
                'Authorization': f'Token {self.token}',
            },
            data=json.dumps(self.payload)
        )

        if 200 <= response.status_code <= 299:
            Logger.done(f"Successfully deleted release '{self.tag}'", response.status_code)
        else:
            Logger.err(f"Failed to delete release '{self.tag}'. Delete it manually at https://github.com/{self.owner}/{self.repo}/releases/tag/{self.tag}", response.status_code)

    def add_release_asset(self):
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/releases/{self.tag}/assets"

        print (f"\nAttempting to add {self.filename} to {self.tag}")

        with open(self.filename, 'rb') as file:
            binary_data = file.read()
        binary_data = base64.b64encode(binary_data)
        Logger.ok("\nFile encoded successfully\n")

        headers = {
            'Authorization': f'Token {self.token}',
            'Content-Type': 'application/octet-stream',
        }

        params = {
            'name': self.filename
        }

        response = requests.post(url, headers=headers, params=params, data=binary_data)
        response_json = json.loads(response.text)

        if 200 <= response.status_code <= 299:
            Logger.done(f"Successfully added '{self.filename}' to release {self.tag}.", response.status_code)
        else:
            Logger.err(f"Failed to add '{self.filename}' to {self.tag}: {response_json}", response.status_code)
            print(f"\nAutomatically deleting release {self.tag}, as adding release asset failed\n")

            self.delete_release()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', nargs='?', default='build-only', choices=['build-only', 'publish'], help='action to perform')
    parser.add_argument("-n", "--no-bump", action="store_true", help="build the extension without bumping patch version")
    args = parser.parse_args()

    builder = Builder("echo Building successful! \(nothing happened, this is an echo statement\)", "-TEST")
    if not args.no_bump:
        builder.bump_patch()
    builder.build()

    if args.action == "publish":
        if input("\nThis will create a release from main and publish it immediately, proceed? (Y/n) ") == 'n': exit(0)

        publisher = Publisher("LDMGamingYT", "FRC-Development-Tools", True, builder.version, 
                              input(f"\n{Style.BRIGHT}Release body? (Markdown is supported){Style.RESET_ALL}\n"), f"debugbin-{builder.version}.txt")
        publisher.list_release()
        publisher.add_release_asset()

if __name__ == "__main__": main()