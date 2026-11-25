# ビルドとRelease管理

この文書はアプリ開発者・Release管理者向けです。利用者向けの説明は `README.md` を参照してください。

## リポジトリの役割

このアプリ用リポジトリは、Windowsインストーラーを作って配布する場所です。譜面ZIPは別の公開リポジトリ `Torld-Taiko-potato/taiko-charts` から取得します。初期設定はこのアカウント・リポジトリ・`charts` フォルダになっています。

必要な主なファイルは次のとおりです。

- `taiko_zip_sync.py`: アプリ本体
- `.github/workflows/build-windows.yml`: GitHub ActionsでWindows版をビルドする設定
- `installer.iss`: Inno Setupのインストーラー定義
- `requirements.txt`: Pythonビルド依存パッケージ
- `README.md`: 利用者向け説明
- `assets/taikonauts_sync.ico`: EXE、インストーラー、タスクトレイで共用するWindowsアイコン
- `assets/taikonauts_sync.png`: READMEに表示するアイコン画像の高解像度版

## アプリ用リポジトリを作る

譜面リポジトリとは分けて、GitHubにPublicリポジトリを作ります。例: `taikonauts-zip-sync`。

プロジェクトのファイルをフォルダ階層を保ったままアップロードしてコミットします。ワークフローは必ず `.github/workflows/build-windows.yml` に置きます。`.github` がWebアップロード画面に表示されない場合は、GitHubの **Add file → Create new file** からファイル名に `.github/workflows/build-windows.yml` と入力し、ファイル内容を貼り付けてください。

## Releaseからインストーラーを生成

1. アプリ用リポジトリの **Releases → Draft a new release** を開きます。
2. **Choose a tag** に `v1.0.0` のような新しいタグを入力し、新規タグとして作成します。Targetは `main` にします。
3. Release titleを入力します（例: `TaikoNauts ZIP Sync v1.0.0`）。
4. **Publish release** を押します。
5. **Actions** タブで **Build Windows installer** が実行されていることを確認します。完了後、Releaseページに `TaikoNautsZipSync-Setup.exe` が添付されます。

GitHub ActionsはGitHubのWindowsランナー上でビルドします。開発者のPCにPythonをインストールしなくてもRelease用インストーラーを生成できます。初回はInno Setupの準備に時間がかかる場合があります。

## ビルドだけを試す

**Actions → Build Windows installer → Run workflow** を実行します。成功後、実行結果の **Artifacts** から `TaikoNautsZipSync-Setup` をダウンロードできます。これは動作確認用です。利用者へ配る場合はReleaseを作成してください。

## アプリの更新

アプリのコードや設定を変更したらmainへコミットし、`v1.0.1` などの新しいタグでReleaseを作成します。Release公開をきっかけに、新しいWindowsインストーラーがビルドされ、そのReleaseへアップロードされます。譜面データの追加・更新は、これまで通り譜面リポジトリへZIPや定義ファイルを追加・更新します。

## 注意事項

コード署名証明書を使っていないため、Windows SmartScreenが警告することがあります。署名付き配布へ移行する場合は、証明書と署名工程をビルドに追加してください。公開する譜面・音源については、再配布できる権利・利用条件を確認してください。
