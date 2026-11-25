import json
import logging
from logging.handlers import RotatingFileHandler
import os
import queue
import shutil
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    pystray = None
    Image = ImageDraw = None

APP_NAME = "TaikoNauts ZIP Sync"
API_ROOT = "https://api.github.com"
LOG_PATH = Path.home() / "TaikoNautsZipSync.log"
logger = logging.getLogger("taiko_zip_sync")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)


def resource_path(relative_path):
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return bundle_root / relative_path


def github_request(url, token):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "TaikoNauts-ZIP-Sync/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.read(), response.headers.get("Content-Type", "")


def safe_extract(zip_path, destination):
    destination = Path(destination).resolve()
    with zipfile.ZipFile(zip_path) as archive:
        seen = {}
        for info in archive.infolist():
            name = info.filename.replace("\\", "/")
            relative = PurePosixPath(name)
            if relative.is_absolute() or any(part in ("..", "") for part in relative.parts):
                raise ValueError(f"ZIP内に安全でないパスがあります: {name}")
            normalized = "/".join(part for part in relative.parts if part not in ("", "."))
            key = normalized.casefold()
            if key in seen:
                raise ValueError(f"ZIP内でファイル名が重複しています（Windowsでは同一扱い）: {seen[key]} と {name}")
            seen[key] = name
            target = (destination / Path(*relative.parts)).resolve()
            if target != destination and destination not in target.parents:
                raise ValueError(f"ZIP内に展開先外のパスがあります: {name}")
            # ZIP symlinks are not extracted; chart packs should contain ordinary files only.
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise ValueError(f"ZIP内のシンボリックリンクは展開できません: {name}")
        archive.extractall(destination)


class SyncApp:
    def __init__(self, root, start_minimized=False):
        self.root = root
        root.title(APP_NAME)
        icon_file = resource_path("assets/taikonauts_sync.ico")
        if icon_file.exists():
            try:
                root.iconbitmap(str(icon_file))
            except tk.TclError:
                logger.warning("ウィンドウアイコンを設定できませんでした: %s", icon_file)
        root.geometry("760x580")
        root.minsize(660, 500)
        self.events = queue.Queue()
        self.stop_event = threading.Event()
        self.worker = None
        self.config_path = Path.home() / ".taiko_zip_sync.json"
        self.state_path = Path.home() / ".taiko_zip_sync_state.json"
        self.config = self.load_config()
        self.owner = tk.StringVar(value=self.config.get("owner") or "Torld-Taiko-potato")
        self.repo = tk.StringVar(value=self.config.get("repo") or "taiko-charts")
        self.branch = tk.StringVar(value=self.config.get("branch", "main"))
        self.folder = tk.StringVar(value=self.config.get("folder", ""))
        self.interval = tk.StringVar(value=str(self.config.get("interval", 10)))
        self.token = tk.StringVar(value="")
        self.autostart = tk.BooleanVar(value=bool(self.config.get("autostart", False)))
        self.start_minimized = start_minimized
        self.tray_icon = None
        self.status = tk.StringVar(value="設定して「今すぐ同期」を押してください。")
        self.make_ui()
        self.root.after(150, self.process_events)
        root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.setup_tray()
        if self.start_minimized and self.tray_icon is not None:
            root.withdraw()
        if self.autostart.get():
            self.root.after(900, self.start_periodic)

    def load_config(self):
        try:
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save_config(self):
        data = {
            "owner": self.owner.get().strip(),
            "repo": self.repo.get().strip(),
            "branch": self.branch.get().strip() or "main",
            "zip_folder": self.zip_folder_var.get().strip(),
            "folder": self.folder.get().strip(),
            "interval": self.interval.get().strip(),
            "autostart": bool(self.autostart.get()),
        }
        self.config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def make_ui(self):
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="GitHub ZIP同期", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(main, text="リポジトリ内のZIPを定期確認し、新規・更新分を保存先へ展開します。既存の譜面は自動削除しません。", wraplength=700).pack(anchor="w", pady=(4, 14))

        form = ttk.Frame(main)
        form.pack(fill="x")
        self.add_entry(form, "GitHubユーザー / 組織", self.owner, 0)
        self.add_entry(form, "リポジトリ名", self.repo, 1)
        self.add_entry(form, "ブランチ", self.branch, 2)
        self.add_entry(form, "ZIPを探すフォルダ（空欄ならリポジトリ全体）", tk.StringVar(value=self.config.get("zip_folder") or "charts"), 3, key="zip_folder")
        self.zip_folder_var = self.fields["zip_folder"]
        self.add_entry(form, "GitHubトークン（非公開リポジトリ用。実行中のみ保持）", self.token, 4, show="*")
        self.add_entry(form, "TaikoNautsの譜面保存先", self.folder, 5, browse=True)
        self.add_entry(form, "確認間隔（分）", self.interval, 6)
        ttk.Label(main, text="ZIPの置き方: リポジトリ（または指定フォルダ）に曲ごとの .zip を追加してください。ZIP内に .tja と対応する .ogg を入れ、必要なら曲フォルダごとZIP化します。", wraplength=700).pack(anchor="w", pady=(12, 4))
        ttk.Label(main, text="初回同期も実行します。更新ZIPは同名フォルダへ展開し、差し替えファイルのみ上書きされます。ZIPを削除してもプレイヤー側の譜面は消えません。", wraplength=700).pack(anchor="w", pady=4)
        buttons = ttk.Frame(main)
        buttons.pack(fill="x", pady=(10, 8))
        self.sync_button = ttk.Button(buttons, text="今すぐ同期", command=self.sync_once)
        self.sync_button.pack(side="left")
        self.start_button = ttk.Button(buttons, text="定期同期を開始", command=self.start_periodic)
        self.start_button.pack(side="left", padx=8)
        self.stop_button = ttk.Button(buttons, text="停止", command=self.stop_periodic, state="disabled")
        self.stop_button.pack(side="left")
        ttk.Button(buttons, text="ログファイルを開く", command=self.open_log_file).pack(side="left", padx=8)
        ttk.Checkbutton(main, text="Windows起動時に自動起動（タスクトレイ常駐・自動同期）", variable=self.autostart, command=self.toggle_autostart).pack(anchor="w", pady=(4, 2))
        ttk.Label(main, textvariable=self.status, wraplength=700).pack(anchor="w", pady=(2, 8))
        self.log = tk.Text(main, height=12, wrap="word", state="disabled", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)
        self.fields = getattr(self, "fields", {})

    def add_entry(self, parent, label, variable, row, show=None, browse=False, key=None):
        if not hasattr(self, "fields"):
            self.fields = {}
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=3)
        entry = ttk.Entry(parent, textvariable=variable, show=show)
        entry.grid(row=row, column=1, sticky="ew", pady=3)
        parent.columnconfigure(1, weight=1)
        if browse:
            ttk.Button(parent, text="参照...", command=self.choose_folder).grid(row=row, column=2, padx=(8, 0))
        if key:
            self.fields[key] = variable

    def choose_folder(self):
        path = filedialog.askdirectory(title="TaikoNautsの譜面保存先を選択")
        if path:
            self.folder.set(path)

    def validate(self):
        owner, repo = self.owner.get().strip(), self.repo.get().strip()
        branch, dest = self.branch.get().strip(), self.folder.get().strip()
        if not owner or not repo or not branch:
            raise ValueError("GitHubユーザー/組織、リポジトリ名、ブランチを入力してください。")
        if not dest:
            raise ValueError("TaikoNautsの譜面保存先を選択してください。")
        try:
            minutes = int(self.interval.get())
            if minutes < 1:
                raise ValueError
        except ValueError:
            raise ValueError("確認間隔は1分以上の整数にしてください。")
        Path(dest).mkdir(parents=True, exist_ok=True)
        self.save_config()
        return owner, repo, branch, self.zip_folder_var.get().strip().strip("/"), Path(dest), minutes, self.token.get().strip()

    def sync_once(self):
        if self.worker and self.worker.is_alive():
            self.status.set("同期処理はすでに実行中です。")
            return
        try:
            args = self.validate()
        except Exception as exc:
            messagebox.showerror("設定を確認してください", str(exc))
            return
        self.status.set("GitHubを確認しています...")
        self.worker = threading.Thread(target=self.sync_worker, args=(args,), daemon=True)
        self.worker.start()

    def sync_worker(self, args):
        owner, repo, branch, zip_folder, dest, _, token = args
        try:
            base = f"{API_ROOT}/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}"
            branch_url = f"{base}/branches/{urllib.parse.quote(branch, safe='')}"
            raw, _ = github_request(branch_url, token)
            branch_data = json.loads(raw)
            tree_sha = branch_data["commit"]["commit"]["tree"]["sha"]
            tree_url = f"{base}/git/trees/{tree_sha}?recursive=1"
            raw, _ = github_request(tree_url, token)
            tree = json.loads(raw)
            if tree.get("truncated"):
                raise RuntimeError("リポジトリが大きく、ZIP一覧を取得できませんでした。ZIPを専用フォルダにまとめてください。")
            files = [item for item in tree.get("tree", []) if item.get("type") == "blob" and item.get("path", "").lower().endswith(".zip")]
            def_files = [item for item in tree.get("tree", []) if item.get("type") == "blob" and Path(item.get("path", "")).name.lower() in ("category.def", "box.def")]
            prefix = zip_folder.rstrip("/") + "/" if zip_folder else ""
            if zip_folder:
                files = [item for item in files if item["path"].startswith(prefix)]
                def_files = [item for item in def_files if item["path"].startswith(prefix)]
            state = self.load_state()
            count = 0
            for item in files:
                if self.stop_event.is_set():
                    break
                rel = item["path"]
                if state.get(rel) == item["sha"]:
                    continue
                try:
                    source_rel = PurePosixPath(rel)
                    relative_parts = source_rel.parts
                    if prefix:
                        relative_path = PurePosixPath("/".join(relative_parts[len(PurePosixPath(zip_folder).parts):]))
                    else:
                        relative_path = source_rel
                    if relative_path.is_absolute() or any(part in ("", ".", "..") for part in relative_path.parts):
                        raise ValueError(f"ZIPのリポジトリ内パスが不正です: {rel}")
                    url = f"{base}/git/blobs/{item['sha']}"
                    data, _ = github_request(url, token)
                    payload = json.loads(data)
                    import base64
                    zip_bytes = base64.b64decode(payload["content"], validate=False)
                    out_dir = dest.joinpath(*relative_path.with_suffix("").parts).resolve()
                    if dest.resolve() not in out_dir.parents:
                        raise ValueError(f"ZIPの展開先が保存先の外を指しています: {rel}")
                    out_dir.parent.mkdir(parents=True, exist_ok=True)
                    temp = dest / f".sync-{Path(rel).name}.tmp"
                    temp.write_bytes(zip_bytes)
                    # Replace the entire managed song folder when the ZIP content changes.
                    staging_dir = out_dir.parent / f".sync-{out_dir.name}-staging"
                    try:
                        if staging_dir.exists():
                            shutil.rmtree(staging_dir)
                        staging_dir.mkdir(parents=True, exist_ok=True)
                        safe_extract(temp, staging_dir)
                        if out_dir.exists():
                            shutil.rmtree(out_dir)
                        staging_dir.replace(out_dir)
                    finally:
                        temp.unlink(missing_ok=True)
                        if staging_dir.exists():
                            shutil.rmtree(staging_dir)
                    state[rel] = item["sha"]
                    self.save_state(state)
                    count += 1
                    logger.info("ZIP同期成功: %s", rel)
                    self.events.put(("log", f"展開しました: {rel} → {out_dir}"))
                except Exception as exc:
                    logger.exception("ZIP同期失敗: %s", rel)
                    self.events.put(("error", f"ZIPを同期できませんでした: {rel}\n{exc}\n既存の同期フォルダはそのままです。詳細: {LOG_PATH}"))
            for item in def_files:
                if self.stop_event.is_set():
                    break
                rel = item["path"]
                if state.get(rel) == item["sha"]:
                    continue
                try:
                    parts = PurePosixPath(rel).parts
                    if prefix:
                        parts = parts[len(PurePosixPath(zip_folder).parts):]
                    if not parts or any(part in ("", ".", "..") for part in parts):
                        raise ValueError(f"定義ファイルのリポジトリ内パスが不正です: {rel}")
                    target = dest.joinpath(*parts).resolve()
                    if dest.resolve() not in target.parents:
                        raise ValueError(f"定義ファイルの保存先が保存先の外を指しています: {rel}")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    data, _ = github_request(f"{base}/git/blobs/{item['sha']}", token)
                    payload = json.loads(data)
                    import base64
                    target.write_bytes(base64.b64decode(payload["content"], validate=False))
                    state[rel] = item["sha"]
                    self.save_state(state)
                    logger.info("定義ファイル同期成功: %s → %s", rel, target)
                    self.events.put(("log", f"同期しました: {rel} → {target}"))
                except Exception as exc:
                    logger.exception("定義ファイル同期失敗: %s", rel)
                    self.events.put(("error", f"定義ファイルを同期できませんでした: {rel}\n{exc}\n詳細: {LOG_PATH}"))
            self.events.put(("status", f"同期確認完了。新規・更新ZIP: {count}件 / ZIP合計: {len(files)}件"))
            logger.info("同期確認完了: %s/%s, 更新ZIP %s/%s", owner, repo, count, len(files))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", "replace")[:500]
            logger.exception("GitHub APIエラー: HTTP %s", exc.code)
            self.events.put(("error", f"GitHubからエラー ({exc.code}): {details}\n詳細: {LOG_PATH}"))
        except Exception as exc:
            logger.exception("同期処理で予期しないエラー")
            self.events.put(("error", f"同期に失敗しました: {exc}\n詳細: {LOG_PATH}"))

    def load_state(self):
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save_state(self, state):
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def start_periodic(self):
        if self.worker and self.worker.is_alive():
            return
        try:
            args = self.validate()
        except Exception as exc:
            messagebox.showerror("設定を確認してください", str(exc))
            return
        self.stop_event.clear()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status.set("定期同期を開始しました。ウィンドウを開いている間、設定間隔で確認します。")
        self.worker = threading.Thread(target=self.periodic_worker, args=(args,), daemon=True)
        self.worker.start()

    def periodic_worker(self, args):
        interval = args[5] * 60
        while not self.stop_event.is_set():
            self.sync_worker(args)
            if self.stop_event.wait(interval):
                break
        self.events.put(("periodic_stopped", "定期同期を停止しました。"))

    def stop_periodic(self):
        self.stop_event.set()
        self.status.set("停止しています...")

    def open_log_file(self):
        LOG_PATH.touch(exist_ok=True)
        try:
            os.startfile(str(LOG_PATH))
        except Exception as exc:
            messagebox.showinfo("ログファイル", f"{LOG_PATH}\n{exc}")

    def process_events(self):
        try:
            while True:
                kind, text = self.events.get_nowait()
                if kind == "log":
                    self.log.configure(state="normal")
                    self.log.insert("end", text + "\n")
                    self.log.see("end")
                    self.log.configure(state="disabled")
                elif kind == "status":
                    self.status.set(text)
                elif kind == "error":
                    self.status.set("エラーが発生しました。ログと設定を確認してください。")
                    self.log.configure(state="normal")
                    self.log.insert("end", text + "\n")
                    self.log.see("end")
                    self.log.configure(state="disabled")
                elif kind == "periodic_stopped":
                    self.status.set(text)
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(150, self.process_events)

    def close(self):
        self.stop_event.set()
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.root.destroy()

    def setup_tray(self):
        if pystray is None:
            self.events.put(("error", "タスクトレイ機能には pystray と Pillow が必要です。手順書のインストール方法を実行してください。"))
            return
        icon_file = resource_path("assets/taikonauts_sync.ico")
        if icon_file.exists():
            image = Image.open(icon_file).convert("RGBA")
        else:
            image = Image.new("RGB", (64, 64), (24, 42, 66))
            draw = ImageDraw.Draw(image)
            draw.ellipse((8, 8, 56, 56), fill=(248, 179, 54))
            draw.text((20, 18), "T", fill=(24, 42, 66))
        menu = pystray.Menu(
            pystray.MenuItem("ウィンドウを表示", lambda icon, item: self.root.after(0, self.show_window), default=True),
            pystray.MenuItem("今すぐ同期", lambda icon, item: self.root.after(0, self.sync_once)),
            pystray.MenuItem("終了", lambda icon, item: self.root.after(0, self.close)),
        )
        self.tray_icon = pystray.Icon("taiko_zip_sync", image, APP_NAME, menu)
        self.tray_icon.run_detached()

    def hide_to_tray(self):
        if self.tray_icon is None:
            self.root.iconify()
            return
        self.root.withdraw()
        self.status.set("タスクトレイで動作中です。アイコンのメニューから表示・同期・終了できます。")

    def show_window(self):
        self.root.deiconify()
        self.root.lift()

    def toggle_autostart(self):
        if os.name != "nt":
            self.autostart.set(False)
            messagebox.showinfo("Windows専用", "自動起動の登録はWindowsでのみ利用できます。")
            return
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if self.autostart.get():
                    if getattr(sys, "frozen", False):
                        command = f'"{Path(sys.executable).resolve()}" --minimized'
                    else:
                        pythonw = Path(sys.executable).with_name("pythonw.exe")
                        if not pythonw.exists():
                            pythonw = Path(sys.executable)
                        command = f'"{pythonw}" "{Path(__file__).resolve()}" --minimized'
                    winreg.SetValueEx(key, "TaikoNautsZipSync", 0, winreg.REG_SZ, command)
                    self.status.set("Windows起動時の自動起動を登録しました。設定後、定期同期を開始してください。")
                else:
                    try:
                        winreg.DeleteValue(key, "TaikoNautsZipSync")
                    except FileNotFoundError:
                        pass
                    self.status.set("Windows起動時の自動起動を解除しました。")
            self.save_config()
            if self.autostart.get() and not (self.worker and self.worker.is_alive()):
                self.start_periodic()
        except Exception as exc:
            self.autostart.set(False)
            messagebox.showerror("自動起動を設定できません", str(exc))


if __name__ == "__main__":
    root = tk.Tk()
    app = SyncApp(root, start_minimized="--minimized" in sys.argv)
    root.mainloop()
