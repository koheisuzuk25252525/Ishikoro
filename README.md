# いしころ戦記 〜46おく年の まもりびと〜

9さいの「いしころ はかせ」が考えた、本物の石の性質でたたかうゲーム。
YouTube「みんなのアイデア ゲーム化計画」で、みんなのアイデアを入れながら育てています。

作った人：げんあん 9さいの いしころ はかせ ／ せいさく みんなのアイデア ゲーム化計画 ／ ゲームのプログラム Claude（AI）

## Xcodeで動かす

MacとXcode 15以降、iOS / iPadOS 16以降を使います。外部パッケージのインストールは不要です。

1. このフォルダ全体をMacへコピーし、`Ishikoro.xcodeproj` を開きます。
2. 上部のSchemeで `Ishikoro`、実行先でiPhoneまたはiPadのシミュレータを選びます。必要ならXcodeのSettingsからiOSシミュレータをインストールします。
3. ▶︎（Command＋R）で起動します。
4. 実機の場合は、アプリのターゲットの「Signing & Capabilities」で自分のTeamを選び、Bundle Identifierを自分用の一意な名前に変更します。端末側のDeveloper Modeも有効にします。

ゲームの編集対象はルートの `ishikoro.html` です。ビルド時に同じファイルがアプリへコピーされるため、HTMLを編集してから再実行してください。SwiftUIの入口は `IshikoroApp/IshikoroApp.swift`、Web画面は `IshikoroApp/GameView.swift` です。

## Macへの自動同期（初回だけ設定）

`Setup-Ishikoro.command` をMacに保存して実行します。macOSが実行を止める場合は、内容と入手元を確認したうえで「プライバシーとセキュリティ」から許可してください。実行権限が付いていない場合は、ターミナルで `bash ` と入力してから、このファイルをウインドウへドラッグし、Enterで実行できます。

設定するとGitHubの `koheisuzuk25252525/Ishikoro` の `main` を `~/Developer/Ishikoro` に取得し、そのXcodeプロジェクトを開きます。以前にZIPから展開したプロジェクトではなく、この新しいプロジェクトを使用してください。既存の別フォルダは変更しません。

ログイン中はLaunchAgentが約60秒ごとに更新を確認します。GitHubへ送信された変更が自動でファイルへ反映され、Xcodeで⌘Rするとアプリへ反映されます。クラウドでの編集だけでは同期されないため、作業後はGitHubのmainへの反映が必要です。Macから自動コミット・自動プッシュは行いません。

ローカルに編集・未追跡ファイルがある場合、別ブランチの場合、履歴が分岐した場合は更新しません。強制リセットやstashは行いません。XcodeでTeam等を変更した場合も更新が止まることがあります。ログは `~/Library/Application Support/IshikoroSync/sync.log` にあります。既存のTeam設定があるプロジェクトを上書き移行しません。

非公開リポジトリではMac側にもGitHubの読み取り認証が必要です。GitHub CLIでログイン済みの場合はその認証を利用します。未設定ならGitHub CLIの `gh auth login --web --git-protocol https` でブラウザ認証してから設定を再実行してください。認証情報をチャットに貼らないでください。ネット接続・認証に失敗してもローカルファイルはそのまま残ります。

同期を止める場合はMacのターミナルで実行します。

```sh
launchctl bootout "gui/$(id -u)/jp.ishikoro.github-sync"
rm -f "$HOME/Library/LaunchAgents/jp.ishikoro.github-sync.plist"
```

アプリやソースは削除されません。再設定するにはインストーラを再実行します。インストーラ自身が新しい内容を自動実行することはありません。MacのLaunchAgentの実動作はMac上で確認してください。

## 動作確認

Macでは次のコマンドでシミュレータ向けにビルドできます。

```sh
xcodebuild -project Ishikoro.xcodeproj -scheme Ishikoro \
  -configuration Debug -sdk iphonesimulator \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath DerivedData CODE_SIGNING_ALLOWED=NO build
```

iPhone・iPadの両方で、タイトル表示、タッチ操作、最初のステージのクリア、縦横回転、操作後の音声、アプリ終了・再起動後のセーブ復元を確認してください。Linuxのクラウド環境ではXcodeのビルド・実機確認はできません。

## 保存と制約

- HTMLの既存のlocalStorageを、WKWebViewの永続データストアで使います。Safari版のセーブは自動では共有されません。引き継ぎコードを残してください。アプリ削除時にはデータが消える可能性があります。
- ゲーム本体・図形・模様はHTML内に同梱し、端末の日本語フォントを使います。外部フォントや画像のダウンロードは不要です。
- 録画・動画のダウンロード・コピー機能はOSとWKWebViewの対応状況によります。ネイティブの共有・動画保存機能は追加していません。実機で確認してください。
- 地層と水晶のアプリアイコンを設定済みです。App Store提出用の情報・スクリーンショット等は公開時に用意してください。アイコンの元絵は `IshikoroApp/AppIconSource.svg` です。
- `build_editions.py` は添付された原本です。`/home/claude/web` 固定のパスを使うため、Macではそのまま実行できません。Xcodeのビルドでは使用しません。

## ブラウザ版

`ishikoro.html` をブラウザで開いても遊べます。ゲームは1ファイル構成のままです。

## 見た目と検証

世界観は「地層と標本の冒険図鑑」。デザインの考え方と描画箇所は [VISUAL_DESIGN.md](VISUAL_DESIGN.md) にまとめています。石の能力値とセーブ形式を保ち、最初の3戦の敵・城HP・報酬・入口を見直しています。診断・変更前後の数値・人によるテスト項目は [docs/PLAYTEST.md](docs/PLAYTEST.md)、自動テストの範囲は [docs/REGRESSION.md](docs/REGRESSION.md) を参照してください。

出撃と変身の押し分け、相性表示の修正、序盤の敵予告については [docs/TACTICAL_CHOICES.md](docs/TACTICAL_CHOICES.md) を参照してください。

任意の開発用ツールとしてPythonのPlaywrightを使い、画面遷移・表示範囲・既存セーブ・初期セーブからの3戦・作戦の比較・各演出・中断復帰を確認できます。これはゲームの実行に必要な依存関係ではありません。

```sh
python3 -m pip install playwright
python3 -m playwright install chromium
python3 tools/check_game_ui.py --play --animations --screenshots /tmp/ishikoro-review
```

テスト用のローカルサーバーと使い捨てのブラウザを自動で立ち上げます。実際のプレイヤーのセーブにはアクセスしません。iOSのWKWebViewでの確認は、Xcodeから別途行ってください。

## 冒険形式の試作

[prototypes/adventure.html](prototypes/adventure.html) は、石を選んで道をひらく3場面の独立した試作です。ブラウザで開くか、Xcodeの **IshikoroAdventure** を選んで実行できます。従来版は **Ishikoro** のままです。試作はセーブを読み書きしません。目的と検証・人による比較項目は [docs/ADVENTURE_PROTOTYPE.md](docs/ADVENTURE_PROTOTYPE.md) に記載しています。
