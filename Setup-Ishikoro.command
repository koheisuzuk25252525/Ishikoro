#!/bin/bash
# Run once on the Mac. Source files are fetched from GitHub, never from a ZIP.
set -eu
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
remote='https://github.com/koheisuzuk25252525/Ishikoro.git'
repo="$HOME/Developer/Ishikoro"
support="$HOME/Library/Application Support/IshikoroSync"
plist="$HOME/Library/LaunchAgents/jp.ishikoro.github-sync.plist"
label='jp.ishikoro.github-sync'
finish() {
    code=$?
    if [ "$code" -ne 0 ]; then
        printf '\n設定できませんでした。上のエラーをCodexに伝えてください。\n'
    fi
    printf '\nEnterキーで閉じます。'
    read -r unused || true
}
trap finish EXIT
if [ "$(uname -s)" != Darwin ]; then echo 'Macで実行してください。'; exit 1; fi
if ! xcode-select -p >/dev/null 2>&1; then
    echo '先にXcodeを起動して、初回の準備を完了してください。'; exit 1
fi
mkdir -p "$HOME/Developer" "$support" "$HOME/Library/LaunchAgents"
# Reuse existing GitHub authentication without reading or writing token values.
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    gh auth setup-git --hostname github.com
fi
if [ -e "$repo" ]; then
    if [ ! -d "$repo/.git" ] || [ "$(git -C "$repo" remote get-url origin)" != "$remote" ]; then
        echo "$repo は既に存在します。上書きしません。Codexに相談してください。"; exit 1
    fi
else
    temp="$(mktemp -d "$HOME/Developer/.Ishikoro-install.XXXXXX")"
    if ! git clone --branch main --single-branch "$remote" "$temp/checkout"; then
        rmdir "$temp" 2>/dev/null || true
        echo 'GitHubから取得できませんでした。非公開の場合はMacのGitHub認証が必要です。'; exit 1
    fi
    mv "$temp/checkout" "$repo"
    rmdir "$temp"
fi
if [ ! -f "$repo/tools/sync-mac.sh" ]; then echo '同期スクリプトがありません。'; exit 1; fi
# The small agent runner stays fixed; remote updates do not install new agents.
cp "$repo/tools/sync-mac.sh" "$support/sync-mac.sh"
/bin/bash "$support/sync-mac.sh" "$repo" "$support/update.lock"
# Build a plist with plutil so spaces and XML characters in the home path are safe.
temp_plist="$(mktemp "$support/agent.XXXXXX")"
/usr/bin/plutil -create xml1 "$temp_plist"
/usr/bin/plutil -insert Label -string "$label" "$temp_plist"
/usr/bin/plutil -insert ProgramArguments -xml '<array/>' "$temp_plist"
/usr/bin/plutil -insert ProgramArguments.0 -string /bin/bash "$temp_plist"
/usr/bin/plutil -insert ProgramArguments.1 -string "$support/sync-mac.sh" "$temp_plist"
/usr/bin/plutil -insert ProgramArguments.2 -string "$repo" "$temp_plist"
/usr/bin/plutil -insert ProgramArguments.3 -string "$support/update.lock" "$temp_plist"
/usr/bin/plutil -insert StartInterval -integer 60 "$temp_plist"
/usr/bin/plutil -insert RunAtLoad -bool YES "$temp_plist"
/usr/bin/plutil -insert StandardOutPath -string "$support/sync.log" "$temp_plist"
/usr/bin/plutil -insert StandardErrorPath -string "$support/sync.log" "$temp_plist"
/usr/bin/plutil -lint "$temp_plist"
launchctl bootout "gui/$(id -u)/$label" >/dev/null 2>&1 || true
mv "$temp_plist" "$plist"
launchctl bootstrap "gui/$(id -u)" "$plist"
launchctl kickstart "gui/$(id -u)/$label"
open "$repo/Ishikoro.xcodeproj"
printf '\n設定できました。今後はGitHubのmainを約1分ごとに確認します。\n'
printf '編集がある場合は自動更新を止め、上書きしません。\n'
printf 'Xcodeはこの新しいプロジェクトを使ってください。変更後は⌘Rで実行します。\n'
printf 'ログ: %s/sync.log\n' "$support"
