# TJA譜面同期 — ビルドとRelease管理

この文書はアプリ開発者・Release管理者向けです。利用者向けの説明は `README.md` を参照してください。

## リポジトリの役割

この互換移行中、アプリ用リポジトリは `taikonauts-zip-sync` です。互換ブリッジ版の公開後に `tja-chart-sync` へ改名する予定です。譜面ZIPは別の公開リポジトリ `Torld-Taiko-potato/taiko-charts` から取得します。アプリの表示名は **TJA譜面同期** です。

必要な主なファイルは次のとおりです。

- `taiko_zip_sync.py`: アプリ本体
- `app_version.py`: ソース実行時の既定バージョン。GitHub ActionsはReleaseタグからビルド時の値を設定
- `.github/workflows/build-windows.yml`: GitHub ActionsでWindows版をビルドする設定
- `installer.iss`: Inno Setupのインストーラー定義
- `requirements.txt`: Pythonビルド依存パッケージ
- `README.md`: 利用者向け説明
- `assets/taikonauts_sync.ico`: EXE、インストーラー、タスクトレイで共用するWindowsアイコン
- `assets/taikonauts_sync.png`: READMEに表示するアイコン画像の高解像度版

Windows通知は `winotify` を使います。通知内容は譜面リポジトリの `charts/announcement.json` に置かれ、利用者アプリが同期確認時に新しいIDを検出したときだけ表示します。お知らせの作成・公開は別配布の管理者用ツールで行います。アプリ更新は起動時にこのリポジトリのLatest Releaseを確認し、利用者の承認後にインストーラーをダウンロード・起動します。GitHub ReleaseのSHA-256値をダウンロード後に照合します。Inno Setupでは `CloseApplications=yes`、`RestartApplications=no` を指定し、更新時に実行中アプリが更新ファイルをロックしないようにします。

## アプリ用リポジトリを作る

譜面リポジトリとは分けて、GitHubにPublicリポジトリを作ります。現在のリポジトリは `taikonauts-zip-sync` で、互換ブリッジ版を公開してから `tja-chart-sync` に改名します。アプリの更新確認コードは旧・新どちらのURLも扱います。

プロジェクトのファイルをフォルダ階層を保ったままアップロードしてコミットします。`app_version.py` も含めてください。ワークフローは必ず `.github/workflows/build-windows.yml` に置きます。`.github` がWebアップロード画面に表示されない場合は、GitHubの **Add file → Create new file** からファイル名に `.github/workflows/build-windows.yml` と入力し、ファイル内容を貼り付けてください。

## Releaseからインストーラーを生成

1. アプリ用リポジトリの **Releases → Draft a new release** を開きます。
2. **Choose a tag** に `v1.0.2` のような新しいタグを入力し、新規タグとして作成します。Targetは `main` にします。
3. Release titleに **TJA譜面同期 v1.0.2** のような名前を入力します。
4. **Publish release** を押します。
5. **Actions** タブで **Build Windows installer** が実行されていることを確認します。完了後、Releaseページに `TJA-Chart-Sync-Setup.exe` と旧版互換用の `TaikoNautsZipSync-Setup.exe` が添付されます。

旧版アプリとの互換性のため、Releaseには旧ファイル名のエイリアスも残します。Innoの `AppId`、`DefaultDirName`、インストール済みアプリ実行ファイル名は既存利用者の更新のため維持します。インストーラー内の製品名とショートカット名は **TJA譜面同期** です。

GitHub ActionsはGitHubのWindowsランナー上でビルドします。開発者のPCにPythonをインストールしなくてもRelease用インストーラーを生成できます。初回はInno Setupの準備に時間がかかる場合があります。

## ビルドだけを試す

**Actions → Build Windows installer → Run workflow** を実行します。成功後、実行結果の **Artifacts** から `TJA-Chart-Sync-Setup` をダウンロードできます。Artifactには新旧両方のEXE名が入ります。これは動作確認用です。利用者へ配る場合はReleaseを作成してください。

## アプリの更新

アプリのコードや設定を変更したらmainへコミットし、`v1.0.2` などの新しいタグでReleaseを作成します。ワークフローはタグからアプリのバージョンを設定してビルドし、インストーラーをReleaseへアップロードします。利用者アプリは起動時にLatest Releaseを確認し、更新があれば利用者の承認後にインストーラーを起動します。

自動更新機能が入る前の旧版（v1.0.1以前）には自身を更新する機能がないため、この機能を含む最初のReleaseだけは利用者がReleaseページから手動でインストールする必要があります。その次の更新からアプリ内で確認・更新できます。譜面データの追加・更新は、これまで通り譜面リポジトリへZIPや定義ファイルを追加・更新します。

## 注意事項

コード署名証明書を使っていないため、Windows SmartScreenが警告することがあります。署名付き配布へ移行する場合は、証明書と署名工程をビルドに追加してください。公開する譜面・音源については、再配布できる権利・利用条件を確認してください。
