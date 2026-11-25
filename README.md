# TaikoNauts ZIP Sync — 配布用プロジェクト

このリポジトリはアプリ本体とWindowsインストーラーを配布するためのものです。譜面ZIPは、既存の `Torld-Taiko-potato/taiko-charts` リポジトリから取得します。アプリの初期値はその公開リポジトリと `charts` フォルダに設定済みです。

## 配布するもの

- `taiko_zip_sync.py`: アプリ本体
- `.github/workflows/build-windows.yml`: GitHub ActionsでWindows版をビルドする設定
- `installer.iss`: Inno Setupのインストーラー定義
- `requirements.txt`: Pythonビルド依存パッケージ

利用者はPythonやライブラリを入れず、GitHub Releasesから `TaikoNautsZipSync-Setup.exe` をダウンロードしてインストールします。

## アプリ用リポジトリを作る

譜面リポジトリとは分けて、GitHubに新しい**Public**リポジトリを作成します。例: `taikonauts-zip-sync`。

このフォルダ内のファイルを、フォルダ階層を保ったまま新しいリポジトリへアップロードしてコミットしてください。`.github/workflows/build-windows.yml` は必ず `.github/workflows/` の中に置きます。GitHubのファイルアップロード画面は隠しフォルダ `.github` を表示しないことがあるため、アップロード時に見えない場合は、まずGitHubで `.github/workflows/build-windows.yml` を手作業で作成し、残りのファイルをアップロードします。

## Releaseを作ってインストーラーを生成する

1. アプリ用リポジトリの **Releases → Draft a new release** を開きます。
2. **Choose a tag** に `v1.0.0` と入力し、新しいタグとして作成します。Targetは `main` にします。
3. Release titleに `TaikoNauts ZIP Sync v1.0.0` と入力します。
4. **Publish release** を押します。
5. リポジトリの **Actions** タブで **Build Windows installer** が動いていることを確認します。初回はInno Setupのインストールに数分かかる場合があります。
6. 完了後、Releaseページに戻ると `TaikoNautsZipSync-Setup.exe` が添付されています。利用者にはそのReleaseページを案内します。

GitHub Actionsはタグ・ReleaseごとにWindows上でアプリをビルドします。手元のWindows PCにPythonを入れなくてもインストーラーを生成できます。動作確認だけしたい場合は **Actions → Build Windows installer → Run workflow** を実行し、完了後にActionsのArtifactから試験用インストーラーをダウンロードできます。

## リリース後の更新

アプリのコードや設定を変更したらリポジトリへコミットし、`v1.0.1` など新しいタグでReleaseを作成します。Release公開をきっかけに新しいWindowsインストーラーがビルドされ、そのReleaseへアップロードされます。譜面データの追加・更新は、これまで通り `taiko-charts` リポジトリへZIPや定義ファイルをアップロードするだけです。

## 注意

このアプリは公開譜面リポジトリからデータを取得するため、初回設定にGitHubトークンは不要です。譜面・音源の再配布可否は、配布する人が権利や利用条件を確認してください。Windows SmartScreenが初回に警告する場合があります。コード署名証明書を使っていないためで、警告が出たときは発行元・ダウンロード元を確認した上で利用してください。
