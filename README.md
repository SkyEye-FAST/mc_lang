# mc_lang

A collection of Minecraft language files, including translations for certain languages.

## Files

- `full/`: Contains all downloaded language files.
- `valid/`: Contains filtered language files with only "valid" translation keys.
- `version.txt`: The latest Minecraft snapshot version used.
- `summary.json`: Some information about the languaeg files in the repository.

## Updater

A script to automatically update and filter Minecraft language files.

### Usage

You need to install [uv](https://docs.astral.sh/uv/) to run the updater, or simply use other Python environments.

1. Clone the repository:

   ```bash
   git clone https://github.com/SkyEye_FAST/mc_lang.git
   cd mc_lang
   ```

2. Install the project:

    ```bash
    uv sync --locked --all-extras --dev
    ```

3. Run the updater:

    ```bash
    uv run mc_lang.py
    ```

## License

The script is released under the [Apache 2.0 license](LICENSE).

``` text
  Copyright 2024 - 2025 SkyEye_FAST

  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
```

## Feedback

Please feel free to raise issues for any problems encountered or feature suggestions.

Pull requests are welcome.
