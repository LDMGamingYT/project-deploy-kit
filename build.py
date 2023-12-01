# Buildscript for extension
# Packages extension into VSIX using vsce

import os
import json
import semver
import argparse
import requests
from colorama import Fore, Back, Style
import base64

# This is the hard-coded branch, change whenever applicable
branch = "-DEV"

# TODO: #10 Make this more object-oriented

# TODO: #3 Move this main stuff to actual proper main() function thing
parser = argparse.ArgumentParser()
parser.add_argument('action', nargs='?', default='build-only', choices=['build-only', 'publish'], help='action to perform')
parser.add_argument("-n", "--no-bump", action="store_true", help="build the extension without bumping patch version")
args = parser.parse_args()

with open('package.json') as f:
    data = json.load(f)

version = data['version']

if not args.no_bump:
    data['version'] = semver.bump_patch(version) + branch

    with open('package.json', 'w') as f:
        json.dump(data, f, indent=4)

# TODO: #4 Make building universal
os.system("vsce package")
filename = f"frc-devtools-{version}.vsix"

class Publisher:
    def __init__(self, owner, repo, isPreRelease, version, release_body):
        self.owner = owner
        self.repo = repo
        self.prerelease = isPreRelease
        self.tag = 'v' + version

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
        print (f"\nPreparing to create release on {self.owner}/{self.repo}\n")

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

        if response.status_code == 201:
            print(f'{Back.GREEN}{Fore.BLACK} DONE {Style.RESET_ALL} Release {self.tag} created successfully. (https://github.com/{self.owner}/{self.repo}/releases/tag/{self.tag})')
        else:
            print(
f"""{Back.RED}{Fore.BLACK} ERROR HTTP {response.status_code} {Style.RESET_ALL} Failed to create release. Response: {response.text} (https://github.com/{self.owner}/{self.repo}/releases/tag/{self.tag})

Try:
- Checking if a release already exists with that tag
- Make sure you're connected to the internet
"""
            )
        exit(-1)

    def get_release_id_url(self):
        return requests.get(
            f'https://api.github.com/repos/{self.owner}/{self.repo}/releases/tags/{self.tag}',
            headers = {
                'Authorization': f'Token {self.token}',
            },  
        ).json()['url']

    def delete_release(self):
        response = requests.delete(
            self.get_release_id_url(),
            headers = {
                'Authorization': f'Token {self.token}',
            },
            data=json.dumps(self.payload)
        )

        if response.status_code == 201: # TODO: #5 Fix this to check for all 200 codes, not just 201
            print(f"{Back.GREEN}{Fore.BLACK} DONE {Style.RESET_ALL} Successfully deleted release '{self.tag}'")
        else:
            print(f"{Back.RED}{Fore.BLACK} ERROR HTTP {response.status_code} {Style.RESET_ALL} Failed to delete release '{self.tag}'. Delete it manually at https://github.com/{self.owner}/{self.repo}/releases/tag/{self.tag}")

    def add_release_asset(self):
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/releases/{self.tag}/assets"

        print (f"\nAttempting to add {filename} to {self.tag}")

        with open(filename, 'rb') as file:
            binary_data = file.read()
        binary_data = base64.b64encode(binary_data)
        print(f"\n{Back.GREEN}{Fore.BLACK} OK {Style.RESET_ALL} File encoded successfully\n")

        headers = {
            'Authorization': f'Token {self.token}',
            'Content-Type': 'application/octet-stream',
        }

        params = {
            'name': filename
        }

        response = requests.post(url, headers=headers, params=params, data=binary_data)
        response_json = json.loads(response.text)

        if response.status_code == 201:
            print(f"{Back.GREEN}{Fore.BLACK} DONE {Style.RESET_ALL} Successfully added '{filename}' to release {self.tag}.")
        else:
            print(f"{Back.RED}{Fore.BLACK} ERROR HTTP {response.status_code} {Style.RESET_ALL} Failed to add '{filename}' to {self.tag}: {response_json}")
            print(f"\nAutomatically deleting release {self.tag}, as adding release asset failed\n")

            self.delete_release()

if args.action == "publish":
    if input("This will create a release from main and publish it immediately, proceed? (Y/n) ") == 'n': exit(0)

    publisher = Publisher("LDMGamingYT", "FRC-Development-Tools", True, version, input(f"{Style.BRIGHT}Release body? (Markdown is supported){Style.RESET_ALL}\n"))
    publisher.list_release()
    publisher.add_release_asset()