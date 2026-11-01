"""Mood Cafe kiosk: smile at the camera, get a coffee discount.

Run:   .venv\\Scripts\\python.exe app.py            (webcam)
       .venv\\Scripts\\python.exe app.py --demo DIR (cycle through face photos in DIR instead of a camera)
Keys:  F11 full screen, Esc leave full screen.
"""
from __future__ import annotations

import argparse
import queue
import sys
import threading
import time
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import messagebox

ROOT = Path(__file__).resolve().parent
LOG_FILE = ROOT / "moodcafe.log"

# Started from MoodCafe.exe (pythonw) there is no console: send library output to a log file.
if sys.stdout is None or sys.stderr is None:
    sys.stdout = sys.stderr = open(LOG_FILE, "w", encoding="utf-8", buffering=1)

try:
    import cv2
    from PIL import Image, ImageTk

    from moodcafe.discount import COOLDOWN_SECONDS, SmileJudge
    from moodcafe.expression import EXPRESSIONS, ExpressionClassifier
    from moodcafe.faces import FaceDetector
except Exception:
    traceback.print_exc()
    _root = tk.Tk()
    _root.withdraw()
    messagebox.showerror("Mood Cafe", "Python packages are missing. Run INSTALL_WINDOWS.bat, then try again.")
    sys.exit(1)

CREAM = "#fbf6ef"
PAPER = "#ffffff"
ESPRESSO = "#3b2417"
COFFEE = "#6f4e37"
LATTE = "#c8a27a"
FOAM = "#efe3d3"
MUTED = "#8a7566"
GREEN = "#2e9e6b"
FONT = "Segoe UI"
MOOD_COLORS = {"happy": "#2e9e6b", "surprise": "#e0a526", "neutral": "#8a7566", "sad": "#4a7bd1",
               "angry": "#d1493f", "fear": "#8b5ad1", "disgust": "#6b8e23"}
MOOD_NAMES = {"happy": "Happy", "surprise": "Surprised", "neutral": "Neutral", "sad": "Sad",
              "angry": "Angry", "fear": "Afraid", "disgust": "Disgusted"}
VIEW_W, VIEW_H = 720, 540


class Camera:
    """Webcam, or a folder of photos shown one after another (demo mode)."""

    def __init__(self, demo_dir=None, seconds_per_photo=3.0):
        self.photos = sorted(p for p in Path(demo_dir).glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png")) \
            if demo_dir else []
        self.seconds_per_photo = seconds_per_photo
        self.started = time.monotonic()
        self.cap = None if self.photos else cv2.VideoCapture(0, cv2.CAP_DSHOW)

    @property
    def available(self):
        return bool(self.photos) or (self.cap is not None and self.cap.isOpened())

    def read(self):
        if self.photos:
            index = int((time.monotonic() - self.started) / self.seconds_per_photo) % len(self.photos)
            time.sleep(1 / 30)
            return cv2.imread(str(self.photos[index]))
        ok, frame = self.cap.read()
        return cv2.flip(frame, 1) if ok else None  # mirror, like looking in a mirror

    def release(self):
        if self.cap is not None:
            self.cap.release()


class Vision(threading.Thread):
    """Background thread: camera -> faces -> expressions. Posts results to a queue for the UI."""

    def __init__(self, camera, results):
        super().__init__(daemon=True)
        self.camera, self.results = camera, results
        self.running = True

    def run(self):
        try:
            detector, classifier = FaceDetector(), ExpressionClassifier()
            self.results.put(("ready", detector.kind, classifier.device_name))
            while self.running:
                frame = self.camera.read()
                if frame is None:
                    time.sleep(0.05)
                    continue
                faces = detector.detect(frame)[:4]
                moods = classifier.predict([face.crop(frame) for face in faces])
                if self.results.qsize() < 2:  # drop frames if the UI is behind
                    self.results.put(("frame", frame, faces, moods))
        except Exception as exc:
            traceback.print_exc()
            self.results.put(("error", str(exc)))
        finally:
            self.camera.release()


class MoodCafeApp:
    def __init__(self, root, camera):
        self.root = root
        self.camera = camera
        self.judge = SmileJudge()
        self.results: queue.Queue = queue.Queue()
        self.coupons_today = 0
        self.coupon_shown_until = 0.0
        self.photo = None
        icon = ROOT / "assets" / "moodcafe.ico"
        if icon.exists():
            root.iconbitmap(default=str(icon))

        root.title("Mood Cafe — Smile for a discount")
        root.configure(bg=CREAM)
        root.geometry("1240x800")
        root.minsize(1100, 760)
        root.bind("<F11>", lambda _e: root.attributes("-fullscreen", not root.attributes("-fullscreen")))
        root.bind("<Escape>", lambda _e: root.attributes("-fullscreen", False))
        self._build()
        root.protocol("WM_DELETE_WINDOW", self.close)

        if not camera.available:
            self._show_message("No camera found", "Connect a webcam and restart Mood Cafe.")
            return
        self.vision = Vision(camera, self.results)
        self.vision.start()
        root.after(30, self._tick)

    # ------------------------------------------------------------------ layout
    def _build(self):
        header = tk.Frame(self.root, bg=CREAM, padx=28, pady=16)
        header.pack(fill="x")
        logo = tk.Canvas(header, width=46, height=46, bg=CREAM, highlightthickness=0)
        logo.create_oval(2, 2, 44, 44, fill=COFFEE, outline="")
        logo.create_rectangle(13, 18, 31, 33, fill=FOAM, outline="")
        logo.create_arc(26, 20, 36, 30, start=270, extent=180, style="arc", outline=FOAM, width=3)
        logo.create_arc(16, 20, 28, 29, start=200, extent=140, style="arc", outline=COFFEE, width=2)
        logo.pack(side="left")
        titles = tk.Frame(header, bg=CREAM)
        titles.pack(side="left", padx=12)
        tk.Label(titles, text="Mood Cafe", bg=CREAM, fg=ESPRESSO, font=(FONT, 20, "bold")).pack(anchor="w")
        tk.Label(titles, text="Smile at the camera and get a discount on your coffee",
                 bg=CREAM, fg=MUTED, font=(FONT, 10)).pack(anchor="w")
        self.status = tk.Label(header, text="Starting camera and AI…", bg=FOAM, fg=COFFEE,
                               font=(FONT, 9, "bold"), padx=12, pady=6)
        self.status.pack(side="right")

        body = tk.Frame(self.root, bg=CREAM)
        body.pack(fill="both", expand=True, padx=28, pady=(0, 20))
        view_card = tk.Frame(body, bg=ESPRESSO, padx=6, pady=6)
        view_card.pack(side="left", anchor="n")
        self.view = tk.Label(view_card, bg=ESPRESSO, width=VIEW_W, height=VIEW_H)
        self.view.pack()

        side = tk.Frame(body, bg=CREAM)
        side.pack(side="left", fill="both", expand=True, padx=(22, 0))

        # Footer first: Tk shrinks the last packed widgets when space runs out.
        footer = tk.Frame(side, bg=CREAM)
        footer.pack(fill="x", side="bottom")
        self.stats = tk.Label(footer, text="Coupons today: 0", bg=CREAM, fg=COFFEE, font=(FONT, 10, "bold"))
        self.stats.pack(anchor="w")
        tk.Label(footer, text="Privacy: no photos are saved. Only the coupon code and time are logged.",
                 bg=CREAM, fg=MUTED, font=(FONT, 8)).pack(anchor="w")
        tk.Label(footer, text="F11 full screen · Esc exit full screen", bg=CREAM, fg=MUTED,
                 font=(FONT, 8)).pack(anchor="w")

        meter_card = self._card(side)
        self.prompt = tk.Label(meter_card, text="Show us your best smile!", bg=PAPER, fg=ESPRESSO,
                               font=(FONT, 16, "bold"))
        self.prompt.pack(anchor="w")
        self.hint = tk.Label(meter_card, text="Hold a big smile for a moment to unlock a discount.",
                             bg=PAPER, fg=MUTED, font=(FONT, 9))
        self.hint.pack(anchor="w", pady=(2, 12))
        self.meter = tk.Canvas(meter_card, height=34, bg=PAPER, highlightthickness=0)
        self.meter.pack(fill="x")

        self.coupon_card = tk.Frame(side, bg=GREEN, padx=20, pady=12)
        top = tk.Frame(self.coupon_card, bg=GREEN)
        top.pack(fill="x")
        self.coupon_title = tk.Label(top, text="", bg=GREEN, fg="#ffffff", font=(FONT, 28, "bold"))
        self.coupon_title.pack(side="left")
        tk.Label(top, text="your\ncoffee", bg=GREEN, fg="#e8fff3", font=(FONT, 11, "bold"),
                 justify="left").pack(side="left", padx=(10, 0))
        self.coupon_code = tk.Label(self.coupon_card, text="", bg="#ffffff", fg=ESPRESSO,
                                    font=("Consolas", 22, "bold"), padx=14, pady=2)
        self.coupon_code.pack(anchor="w", pady=(4, 6))
        self.coupon_note = tk.Label(self.coupon_card, text="", bg=GREEN, fg="#e8fff3", font=(FONT, 10))
        self.coupon_note.pack(anchor="w")

        mood_card = self._card(side, "Your mood right now")
        self.bars = {}
        for name in ["happy", "neutral", "surprise", "sad", "angry", "fear", "disgust"]:
            row = tk.Frame(mood_card, bg=PAPER)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=MOOD_NAMES[name], bg=PAPER, fg=ESPRESSO, font=(FONT, 10), width=10,
                     anchor="w").pack(side="left")
            bar = tk.Canvas(row, width=1, height=14, bg=FOAM, highlightthickness=0)
            bar.pack(side="left", fill="x", expand=True, padx=(4, 8))
            value = tk.Label(row, text="0%", bg=PAPER, fg=MUTED, font=(FONT, 9), width=5, anchor="e")
            value.pack(side="left")
            self.bars[name] = (bar, value)

    def _card(self, parent, title=None):
        card = tk.Frame(parent, bg=PAPER, padx=18, pady=16, highlightthickness=1, highlightbackground=FOAM)
        card.pack(fill="x", pady=(0, 14))
        if title:
            tk.Label(card, text=title, bg=PAPER, fg=ESPRESSO, font=(FONT, 12, "bold")).pack(anchor="w", pady=(0, 8))
        return card

    # ------------------------------------------------------------------ updates
    def _tick(self):
        latest = None
        try:
            while True:
                item = self.results.get_nowait()
                if item[0] == "frame":
                    latest = item
                elif item[0] == "ready":
                    self.status.configure(text=f"  Ready · {item[1]} · {item[2]}  ", bg="#e3f4ea", fg=GREEN)
                elif item[0] == "error":
                    self._show_message("Something went wrong", item[1][:300] + f"\n\nLog: {LOG_FILE}")
                    return
        except queue.Empty:
            pass
        if latest is not None:
            self._render(*latest[1:])
        self.root.after(30, self._tick)

    def _render(self, frame, faces, moods):
        now = time.monotonic()
        main = moods[0] if moods else None
        coupon = self.judge.update(main["happy"] if main else None, now)
        if coupon:
            self._show_coupon(coupon, now)

        for face, mood in zip(faces, moods):
            top = max(mood, key=mood.get)
            color = tuple(int(MOOD_COLORS[top][i:i + 2], 16) for i in (5, 3, 1))  # hex -> BGR
            cv2.rectangle(frame, (face.x, face.y), (face.x + face.w, face.y + face.h), color, 3)
            label = f"{MOOD_NAMES[top]} {mood[top]:.0%}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(frame, (face.x, face.y - th - 14), (face.x + tw + 12, face.y), color, -1)
            cv2.putText(frame, label, (face.x + 6, face.y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        height, width = frame.shape[:2]
        scale = min(VIEW_W / width, VIEW_H / height)
        frame = cv2.resize(frame, (int(width * scale), int(height * scale)))
        self.photo = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
        self.view.configure(image=self.photo)

        for name, (bar, value) in self.bars.items():
            share = main[name] if main else 0.0
            bar.delete("all")
            bar.create_rectangle(0, 0, max(2, bar.winfo_width() * share), 14, fill=MOOD_COLORS[name], outline="")
            value.configure(text=f"{share:.0%}")
        self._update_meter(now, bool(faces))
        if self.coupon_shown_until and now > self.coupon_shown_until:
            self.coupon_card.pack_forget()
            self.coupon_shown_until = 0.0

    def _update_meter(self, now, has_face):
        state = self.judge.state
        progress = self.judge.progress(now)
        width = self.meter.winfo_width()
        self.meter.delete("all")
        self.meter.create_rectangle(0, 0, width, 34, fill=FOAM, outline="")
        fill = progress if state in ("smiling", "watching") else 1.0
        self.meter.create_rectangle(0, 0, width * fill, 34, fill=GREEN if state != "watching" else LATTE,
                                    outline="")
        self.meter.create_text(12, 17, anchor="w", font=(FONT, 10, "bold"), fill=ESPRESSO,
                               text=f"Smile meter {self.judge.score:.0%}")
        if state == "cooldown":
            left = max(0, int(self.judge.cooldown_until - now))
            self.prompt.configure(text="Enjoy your coffee!")
            self.hint.configure(text=f"Next customer in {left} s. Please step aside.")
        elif state == "next_customer":
            self.prompt.configure(text="Thanks! Next customer, please")
            self.hint.configure(text="One discount per visit.")
        elif not has_face:
            self.prompt.configure(text="Step in front of the camera")
            self.hint.configure(text="Look at the camera and give us your best smile.")
        elif state == "smiling":
            self.prompt.configure(text=f"Keep smiling… {progress:.0%}")
            self.hint.configure(text="Almost there!")
        else:
            self.prompt.configure(text="Show us your best smile!")
            self.hint.configure(text="Hold a big smile for a moment to unlock a discount.")

    def _show_coupon(self, coupon, now):
        self.coupons_today += 1
        self.stats.configure(text=f"Coupons today: {self.coupons_today}")
        self.coupon_title.configure(text=f"{coupon.percent}% OFF")
        self.coupon_code.configure(text=coupon.code)
        self.coupon_note.configure(text=f"Show this code to the barista · valid until {coupon.expires:%H:%M}")
        self.coupon_card.pack(fill="x", pady=(0, 14), after=self.meter.master)
        self.coupon_shown_until = now + COOLDOWN_SECONDS

    def _show_message(self, title, text):
        self.status.configure(text=f"  {title}  ", bg="#fde4e1", fg="#a53a2f")
        self.prompt.configure(text=title)
        self.hint.configure(text=text)

    def close(self):
        if hasattr(self, "vision"):
            self.vision.running = False
        self.root.after(200, self.root.destroy)


def main():
    parser = argparse.ArgumentParser(description="Mood Cafe smile-for-a-discount kiosk")
    parser.add_argument("--demo", help="folder of face photos to use instead of the webcam")
    args = parser.parse_args()
    root = tk.Tk()
    MoodCafeApp(root, Camera(args.demo))
    root.mainloop()


if __name__ == "__main__":
    main()
